#include "audio_engine.h"

#include <android/log.h>
#include <cmath>

#define LOG_TAG "SP1200Engine"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

AudioEngine::AudioEngine() {
    frequencies = std::array<double, kNumPads>{
            55.0,
            65.41,
            73.42,
            82.41,
            98.0,
            110.0,
            130.81,
            146.83
    };
}

AudioEngine::~AudioEngine() {
    stop();
}

bool AudioEngine::start() {
    if (running) {
        return true;
    }

    oboe::AudioStreamBuilder builder;

    oboe::Result result = builder
            .setDirection(oboe::Direction::Output)
            .setPerformanceMode(oboe::PerformanceMode::LowLatency)
            .setFormat(oboe::AudioFormat::Float)
            .setChannelCount(1)
            .setDataCallback(this)
            .openStream(outputStream);

    if (result != oboe::Result::OK) {
        LOGI("Failed to open audio stream");
        return false;
    }

    sampleRate = outputStream->getSampleRate();
    if (sampleRate <= 0.0) {
        sampleRate = 48000.0;
    }

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

void AudioEngine::triggerPad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    Voice& voice = voices[padIndex];

    voice.frequency.store(frequencies[padIndex], std::memory_order_relaxed);
    voice.amp.store(0.9, std::memory_order_relaxed);
    voice.active.store(true, std::memory_order_relaxed);
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

    constexpr double kTwoPi = 2.0 * 3.14159265358979323846;

    for (int32_t frame = 0; frame < numFrames; ++frame) {
        float mix = 0.0f;

        for (auto& voice : voices) {
            bool isActive = voice.active.load(std::memory_order_relaxed);
            if (!isActive) {
                continue;
            }

            double amp = voice.amp.load(std::memory_order_relaxed);

            if (amp < 0.0005) {
                voice.active.store(false, std::memory_order_relaxed);
                continue;
            }

            double frequency = voice.frequency.load(std::memory_order_relaxed);

            voice.phase += kTwoPi * frequency / sampleRate;

            while (voice.phase >= kTwoPi) {
                voice.phase -= kTwoPi;
            }

            mix += static_cast<float>(std::sin(voice.phase) * amp);

            amp *= 0.9995;
            voice.amp.store(amp, std::memory_order_relaxed);
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
