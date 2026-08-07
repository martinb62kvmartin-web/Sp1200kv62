#include "audio_engine.h"

#include <android/log.h>
#include <cmath>
#include <cstring>
#include <unistd.h>

#define LOG_TAG "SP1200Engine"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = 2.0 * kPi;
}

AudioEngine::AudioEngine() = default;

AudioEngine::~AudioEngine() {
    stop();
}

bool AudioEngine::start() {
    if (running) {
        return true;
    }

    oboe::AudioStreamBuilder builder;

    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(1);
    builder.setDataCallback(this);

    oboe::Result result = builder.openStream(outputStream);

    if (result != oboe::Result::OK) {
        LOGI("Failed to open audio stream");
        return false;
    }

    sampleRate = outputStream->getSampleRate();
    if (sampleRate <= 0.0) {
        sampleRate = 48000.0;
    }

    releaseFactor = std::exp(-1.0 / (sampleRate * 0.01));

    int32_t burst = outputStream->getFramesPerBurst();
    if (burst > 0) {
        outputStream->setBufferSizeInFrames(burst * 2);
    }

    result = outputStream->requestStart();

    if (result != oboe::Result::OK) {
        LOGI("Failed to start audio stream");
        outputStream->close();
        outputStream.reset();
        return false;
    }

    running = true;
    LOGI("Audio engine started. Sample rate: %d", outputStream->getSampleRate());
    return true;
}

void AudioEngine::stop() {
    if (!running && !outputStream) {
        return;
    }

    running = false;

    if (outputStream) {
        outputStream->stop();
        outputStream->close();
        outputStream.reset();
        LOGI("Audio engine stopped");
    }
}

void AudioEngine::setGateMode(bool enabled) {
    gateMode.store(enabled, std::memory_order_relaxed);
}

void AudioEngine::setPitchSemitones(double semitones) {
    pitchRate.store(std::pow(2.0, semitones / 12.0), std::memory_order_relaxed);
}

void AudioEngine::padRelease(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    if (gateMode.load(std::memory_order_relaxed)) {
        voices[padIndex].gateClosed.store(true, std::memory_order_relaxed);
    }
}

bool AudioEngine::loadSample(int padIndex, int fd) {
    if (padIndex < 0 || padIndex >= kNumPads || fd < 0) {
        return false;
    }

    std::vector<uint8_t> bytes;
    uint8_t buf[65536];
    ssize_t n;
    while ((n = ::read(fd, buf, sizeof(buf))) > 0) {
        bytes.insert(bytes.end(), buf, buf + n);
    }

    if (bytes.size() < 44) {
        return false;
    }

    if (std::memcmp(bytes.data(), "RIFF", 4) != 0 ||
        std::memcmp(bytes.data() + 8, "WAVE", 4) != 0) {
        LOGI("Not a WAV file");
        return false;
    }

    int format = 0;
    int numChannels = 0;
    int bits = 0;
    double rate = 44100.0;
    const uint8_t* dataPtr = nullptr;
    size_t dataSize = 0;

    size_t pos = 12;
    while (pos + 8 <= bytes.size()) {
        const uint8_t* id = bytes.data() + pos;
        uint32_t size = 0;
        std::memcpy(&size, bytes.data() + pos + 4, 4);
        const uint8_t* body = bytes.data() + pos + 8;

        if (std::memcmp(id, "fmt ", 4) == 0 && size >= 16) {
            uint16_t f = 0, ch = 0, bps = 0;
            uint32_t sr = 0;
            std::memcpy(&f, body, 2);
            std::memcpy(&ch, body + 2, 2);
            std::memcpy(&sr, body + 4, 4);
            std::memcpy(&bps, body + 14, 2);
            format = f;
            numChannels = ch;
            rate = sr;
            bits = bps;
        } else if (std::memcmp(id, "data", 4) == 0) {
            dataPtr = body;
            dataSize = size;
            if (pos + 8 + dataSize > bytes.size()) {
                dataSize = bytes.size() - pos - 8;
            }
        }

        pos += 8 + size + (size & 1);
    }

    if (dataPtr == nullptr || numChannels <= 0) {
        return false;
    }

    if (!(format == 1 && bits == 16)) {
        LOGI("Unsupported WAV format. Need PCM 16-bit");
        return false;
    }

    auto sample = std::make_shared<Sample>();
    sample->sampleRate = rate;

    const size_t frameBytes = static_cast<size_t>(numChannels) * 2;
    const size_t frames = dataSize / frameBytes;
    sample->data.resize(frames);

    for (size_t i = 0; i < frames; ++i) {
        float acc = 0.0f;
        for (int c = 0; c < numChannels; ++c) {
            int16_t s = 0;
            std::memcpy(&s, dataPtr + i * frameBytes + static_cast<size_t>(c) * 2, 2);
            acc += static_cast<float>(s) / 32768.0f;
        }
        sample->data[i] = acc / static_cast<float>(numChannels);
    }

    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        samples[padIndex] = sample;
    }

    LOGI("Loaded sample for pad %d, frames=%zu", padIndex, sample->data.size());
    return true;
}

void AudioEngine::triggerPad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    Voice& voice = voices[padIndex];

    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        voice.nextSample = samples[padIndex];
    }

    voice.gateClosed.store(false, std::memory_order_relaxed);
    voice.type.store(padIndex, std::memory_order_relaxed);
    voice.hasNextSample.store(true, std::memory_order_relaxed);
    voice.resetRequest.store(true, std::memory_order_relaxed);
    voice.active.store(true, std::memory_order_relaxed);
}

double AudioEngine::nextNoise(Voice& v) {
    v.rng = v.rng * 1664525u + 1013904223u;
    return (static_cast<double>(v.rng) / 2147483648.0) - 1.0;
}

double AudioEngine::renderVoice(Voice& v) {
    const double rate = pitchRate.load(std::memory_order_relaxed);

    if (v.sample && !v.sample->data.empty()) {
        const std::vector<float>& d = v.sample->data;
        const double step = (v.sample->sampleRate / sampleRate) * rate;
        const size_t i = static_cast<size_t>(v.pos);

        if (i + 1 >= d.size()) {
            v.amp = 0.0;
            return 0.0;
        }

        const double frac = v.pos - static_cast<double>(i);
        const double out = d[i] + (d[i + 1] - d[i]) * frac;
        v.pos += step;
        return out * v.amp;
    }

    const double t = static_cast<double>(v.age) / sampleRate;
    double out = 0.0;

    switch (v.type.load(std::memory_order_relaxed)) {
        case 0: {
            const double f = (40.0 + 120.0 * std::exp(-t * 25.0)) * rate;
            v.phase += kTwoPi * f / sampleRate;
            if (v.phase >= kTwoPi) v.phase -= kTwoPi;
            out = std::sin(v.phase);
            break;
        }
        case 1: {
            const double n = nextNoise(v);
            v.phase += kTwoPi * 180.0 * rate / sampleRate;
            if (v.phase >= kTwoPi) v.phase -= kTwoPi;
            out = 0.6 * n + 0.5 * std::sin(v.phase);
            break;
        }
        case 2:
        case 3: {
            const double n = nextNoise(v);
            const double hp = n - v.prevNoise;
            v.prevNoise = n;
            out = 0.8 * hp;
            break;
        }
        case 4: {
            const double f = (70.0 + 30.0 * std::exp(-t * 10.0)) * rate;
            v.phase += kTwoPi * f / sampleRate;
            if (v.phase >= kTwoPi) v.phase -= kTwoPi;
            out = std::sin(v.phase);
            break;
        }
        case 5: {
            const double f = (120.0 + 40.0 * std::exp(-t * 10.0)) * rate;
            v.phase += kTwoPi * f / sampleRate;
            if (v.phase >= kTwoPi) v.phase -= kTwoPi;
            out = std::sin(v.phase);
            break;
        }
        case 6: {
            const double n = nextNoise(v);
            out = n * (0.6 + 0.4 * std::sin(t * kTwoPi * 22.0));
            break;
        }
        case 7: {
            v.phase += kTwoPi * 540.0 * rate / sampleRate;
            if (v.phase >= kTwoPi) v.phase -= kTwoPi;
            v.phase2 += kTwoPi * 800.0 * rate / sampleRate;
            if (v.phase2 >= kTwoPi) v.phase2 -= kTwoPi;
            const double s1 = (v.phase < kPi) ? 0.5 : -0.5;
            const double s2 = (v.phase2 < kPi) ? 0.4 : -0.4;
            out = s1 + s2;
            break;
        }
        default:
            out = 0.0;
            break;
    }

    v.age++;

    return out * v.amp;
}

oboe::DataCallbackResult AudioEngine::onAudioReady(
        oboe::AudioStream* stream,
        void* audioData,
        int32_t numFrames
) {
    auto* output = static_cast<float*>(audioData);

    if (sampleRate <= 0.0 && stream != nullptr) {
        sampleRate = stream->getSampleRate();
    }

    if (sampleRate <= 0.0) {
        sampleRate = 48000.0;
    }

    for (int32_t frame = 0; frame < numFrames; ++frame) {
        float mix = 0.0f;

        for (auto& v : voices) {
            if (!v.active.load(std::memory_order_relaxed)) {
                continue;
            }

            if (v.resetRequest.exchange(false, std::memory_order_relaxed)) {
                if (v.hasNextSample.exchange(false, std::memory_order_relaxed)) {
                    std::lock_guard<std::mutex> lock(sampleMutex);
                    v.sample = v.nextSample;
                }

                const int type = v.type.load(std::memory_order_relaxed);
                v.age = 0;
                v.phase = 0.0;
                v.phase2 = 0.0;
                v.prevNoise = 0.0;
                v.amp = 1.0;
                v.pos = 0.0;
                v.rng = 123456789u + static_cast<uint32_t>(type) * 999983u;

                switch (type) {
                    case 0: v.decay = std::exp(-1.0 / (sampleRate * 0.35)); break;
                    case 1: v.decay = std::exp(-1.0 / (sampleRate * 0.18)); break;
                    case 2: v.decay = std::exp(-1.0 / (sampleRate * 0.05)); break;
                    case 3: v.decay = std::exp(-1.0 / (sampleRate * 0.40)); break;
                    case 4: v.decay = std::exp(-1.0 / (sampleRate * 0.40)); break;
                    case 5: v.decay = std::exp(-1.0 / (sampleRate * 0.40)); break;
                    case 6: v.decay = std::exp(-1.0 / (sampleRate * 0.15)); break;
                    case 7: v.decay = std::exp(-1.0 / (sampleRate * 0.30)); break;
                    default: v.decay = 0.9999; break;
                }
            }

            if (v.amp < 0.0005) {
                v.active.store(false, std::memory_order_relaxed);
                continue;
            }

            mix += static_cast<float>(renderVoice(v));

            if (v.gateClosed.load(std::memory_order_relaxed)) {
                v.amp *= releaseFactor;
            } else if (!v.sample || v.sample->data.empty()) {
                v.amp *= v.decay;
            }
        }

        if (mix > 1.0f) {
            mix = 1.0f;
        } else if (mix < -1.0f) {
            mix = -1.0f;
        }

        output[frame] = mix * 0.8f;
    }

    return oboe::DataCallbackResult::Continue;
}
