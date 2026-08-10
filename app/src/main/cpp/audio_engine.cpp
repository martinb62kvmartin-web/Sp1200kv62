#include "audio_engine.h"

#include <android/log.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <unistd.h>

#define LOG_TAG "SP1200Engine"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = 2.0 * kPi;

double clampd(double v, double lo, double hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

float ulawEncode(float x) {
    const float mu = 255.0f;
    const float s = x < 0.0f ? -1.0f : 1.0f;
    const float a = std::fabs(x);
    const float y = std::log1p(mu * a) / std::log1p(mu);
    return s * y;
}

float ulawDecode(float y) {
    const float mu = 255.0f;
    const float s = y < 0.0f ? -1.0f : 1.0f;
    const float a = std::fabs(y);
    const float x = (std::pow(1.0f + mu, a) - 1.0f) / mu;
    return s * x;
}

float vintage(float x) {
    float e = ulawEncode(x);
    constexpr float q = 2048.0f;
    e = std::floor(e * q + 0.5f) / q;
    return ulawDecode(e);
}

bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate, int channels) {
    FILE* f = std::fopen(path.c_str(), "wb");
    if (f == nullptr) {
        return false;
    }

    const uint16_t ch = static_cast<uint16_t>(channels > 0 ? channels : 1);
    const uint32_t n = static_cast<uint32_t>(data.size());
    const uint32_t dataSize = n * 2;
    const uint32_t chunkSize = 36 + dataSize;
    const uint16_t one = 1;
    const uint16_t bps = 16;
    const uint32_t fmtSize = 16;
    const uint32_t byteRate = rate * ch;
    const uint16_t blockAlign = static_cast<uint16_t>(2 * ch);

    std::fwrite("RIFF", 1, 4, f);
    std::fwrite(&chunkSize, 4, 1, f);
    std::fwrite("WAVE", 1, 4, f);
    std::fwrite("fmt ", 1, 4, f);
    std::fwrite(&fmtSize, 4, 1, f);
    std::fwrite(&one, 2, 1, f);
    std::fwrite(&ch, 2, 1, f);
    std::fwrite(&rate, 4, 1, f);
    std::fwrite(&byteRate, 4, 1, f);
    std::fwrite(&blockAlign, 2, 1, f);
    std::fwrite(&bps, 2, 1, f);
    std::fwrite("data", 1, 4, f);
    std::fwrite(&dataSize, 4, 1, f);

    for (float v : data) {
        const float c = v < -1.0f ? -1.0f : (v > 1.0f ? 1.0f : v);
        const int16_t s = static_cast<int16_t>(c * 32767.0f);
        std::fwrite(&s, 2, 1, f);
    }

    std::fclose(f);
    return true;
}
}

AudioEngine::AudioEngine() {
    for (auto& row : loopStartFrac) for (auto& f : row) f.store(0.0);
    for (auto& row : loopEndFrac) for (auto& f : row) f.store(1.0);
    for (auto& row : loopOn) for (auto& f : row) f.store(false);
    for (auto& row : padRev) for (auto& f : row) f.store(false);
    for (auto& row : padPitch) for (auto& f : row) f.store(0.0);
    for (auto& row : padA) for (auto& f : row) f.store(0.0);
    for (auto& row : padD) for (auto& f : row) f.store(0.0);
    for (auto& row : padS) for (auto& f : row) f.store(1.0);
    for (auto& row : padR) for (auto& f : row) f.store(0.05);
    for (auto& m : mutes) m.store(false);
    for (auto& s : solos) s.store(false);
    for (auto& v : padVol) v.store(1.0f);
    for (auto& p : padPan) p.store(0.0f);
    for (auto& l : padLevel) l.store(0.0f);
    for (auto& h : padHits) h.store(0);
    for (auto& e : rollEndAt) e = -1;
}

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
    builder.setChannelCount(2);
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
    recording.store(false, std::memory_order_relaxed);
    capturing.store(false, std::memory_order_relaxed);

    if (inputStream) {
        inputStream->stop();
        inputStream->close();
        inputStream.reset();
    }

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

std::array<float, 18> AudioEngine::getLevels() {
    std::array<float, 18> out{};
    for (int i = 0; i < kNumPads; ++i) {
        out[static_cast<size_t>(i)] = padLevel[i].load(std::memory_order_relaxed);
    }
    out[16] = levelL.load(std::memory_order_relaxed);
    out[17] = levelR.load(std::memory_order_relaxed);
    return out;
}

void AudioEngine::clearPad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    samples[b][padIndex].reset();
}

void AudioEngine::setPadReverse(int padIndex, bool enabled) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    const int b = currentBank.load(std::memory_order_relaxed);
    padRev[b][padIndex].store(enabled, std::memory_order_relaxed);
}

void AudioEngine::startCapture() {
    std::lock_guard<std::mutex> lock(capMutex);
    capBuf.clear();
    capturing.store(true, std::memory_order_relaxed);
}

bool AudioEngine::stopCapture(const std::string& path) {
    capturing.store(false, std::memory_order_relaxed);

    std::vector<float> data;
    {
        std::lock_guard<std::mutex> lock(capMutex);
        data.swap(capBuf);
    }

    if (data.empty()) {
        return false;
    }

    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate), 2);
    LOGI("Export written: %s (%zu frames)", path.c_str(), data.size());
    return ok;
}

void AudioEngine::setGateMode(bool enabled) {
    gateMode.store(enabled, std::memory_order_relaxed);
}

void AudioEngine::setPitchSemitones(double semitones) {
    pitchRate.store(std::pow(2.0, semitones / 12.0), std::memory_order_relaxed);
}

void AudioEngine::setCrunch(bool enabled) {
    crunchOn.store(enabled, std::memory_order_relaxed);
}

void AudioEngine::setPadVol(int padIndex, float vol) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    padVol[padIndex].store(clampd(vol, 0.0f, 1.5f), std::memory_order_relaxed);
}

void AudioEngine::setPadPan(int padIndex, float pan) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    padPan[padIndex].store(clampd(pan, -1.0f, 1.0f), std::memory_order_relaxed);
}

void AudioEngine::setMasterVol(float vol) {
    masterVol.store(clampd(vol, 0.0f, 1.5f), std::memory_order_relaxed);
}

void AudioEngine::setMasterPan(float pan) {
    masterPan.store(clampd(pan, -1.0f, 1.0f), std::memory_order_relaxed);
}

void AudioEngine::setMidiMode(int mode) {
    if (mode < 0) mode = 0;
    if (mode > 2) mode = 2;
    midiMode.store(mode, std::memory_order_relaxed);
}

void AudioEngine::midiTick() {
    pendingTicks.fetch_add(1, std::memory_order_relaxed);
}

void AudioEngine::midiStart() {
    midiStartReq.store(true, std::memory_order_relaxed);
}

void AudioEngine::midiStop() {
    midiStopReq.store(true, std::memory_order_relaxed);
}

long long AudioEngine::getMidiTicksOut() {
    return midiTicksOut.load(std::memory_order_relaxed);
}

void AudioEngine::setDataDir(const std::string& dir) {
    dataDir = dir;
}

int AudioEngine::getCurrentStep() {
    return currentStepPublic.load(std::memory_order_relaxed);
}

long long AudioEngine::getPadHits(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return 0;
    }
    return padHits[padIndex].load(std::memory_order_relaxed);
}

bool AudioEngine::startRecording(int padIndex) {
    if (recording.load(std::memory_order_relaxed)) {
        return false;
    }
    if (padIndex < 0 || padIndex >= kNumPads) {
        return false;
    }

    recPad = padIndex;
    recBank = currentBank.load(std::memory_order_relaxed);

    {
        std::lock_guard<std::mutex> lock(recMutex);
        recBuffer.clear();
        recRate = 48000.0;
    }

    oboe::AudioStreamBuilder builder;
    builder.setDirection(oboe::Direction::Input);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(1);
    builder.setDataCallback(this);

    oboe::Result r = builder.openStream(inputStream);
    if (r != oboe::Result::OK) {
        LOGI("Failed to open input stream");
        return false;
    }

    r = inputStream->requestStart();
    if (r != oboe::Result::OK) {
        inputStream->close();
        inputStream.reset();
        return false;
    }

    recording.store(true, std::memory_order_relaxed);
    LOGI("Recording started on pad %d", padIndex);
    return true;
}

bool AudioEngine::stopRecording() {
    if (!recording.exchange(false, std::memory_order_relaxed)) {
        return false;
    }

    if (inputStream) {
        inputStream->stop();
        inputStream->close();
        inputStream.reset();
    }

    std::vector<float> buf;
    double rate;
    {
        std::lock_guard<std::mutex> lock(recMutex);
        buf.swap(recBuffer);
        rate = recRate;
    }

    if (buf.size() < 1600 || rate <= 0.0) {
        LOGI("Recording too short");
        return false;
    }

    auto sample = std::make_shared<Sample>();
    sample->sampleRate = rate;
    sample->data = std::move(buf);

    const int b = recBank;
    const int p = recPad;

    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        samples[b][p] = sample;
    }

    loopStartFrac[b][p].store(0.0, std::memory_order_relaxed);
    loopEndFrac[b][p].store(1.0, std::memory_order_relaxed);

    if (!dataDir.empty()) {
        const std::string path = dataDir + "/b" + std::to_string(b) + "_p" + std::to_string(p) + ".wav";
        writeWavFile(path, sample->data, static_cast<uint32_t>(rate), 1);
    }

    LOGI("Recording stored on bank %d pad %d", b, p);
    return true;
}

void AudioEngine::setBank(int bank) {
    if (bank < 0 || bank >= kBanks) {
        return;
    }
    currentBank.store(bank, std::memory_order_relaxed);
}

void AudioEngine::setMute(int padIndex, bool enabled) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }
    mutes[padIndex].store(enabled, std::memory_order_relaxed);
}

void AudioEngine::setSolo(int padIndex, bool enabled) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    const bool old = solos[padIndex].load(std::memory_order_relaxed);
    if (old != enabled) {
        solos[padIndex].store(enabled, std::memory_order_relaxed);
        soloCount.store(soloCount.load(std::memory_order_relaxed) + (enabled ? 1 : -1),
                        std::memory_order_relaxed);
    }
}

void AudioEngine::setPadParams(int padIndex, double pitchSemi, double attack,
                               double decay, double sustain, double release) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    const int b = currentBank.load(std::memory_order_relaxed);

    padPitch[b][padIndex].store(clampd(pitchSemi, -24.0, 24.0), std::memory_order_relaxed);
    padA[b][padIndex].store(clampd(attack, 0.0, 2.0), std::memory_order_relaxed);
    padD[b][padIndex].store(clampd(decay, 0.0, 3.0), std::memory_order_relaxed);
    padS[b][padIndex].store(clampd(sustain, 0.0, 1.0), std::memory_order_relaxed);
    padR[b][padIndex].store(clampd(release, 0.0, 3.0), std::memory_order_relaxed);
}

void AudioEngine::setRoll(int padIndex, int step, int value, int len) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }
    if (step < 0 || step >= kSteps) {
        return;
    }

    const int b = currentBank.load(std::memory_order_relaxed);
    rollPitch[b][padIndex][step].store(value, std::memory_order_relaxed);
    rollLen[b][padIndex][step].store(len > 0 ? len : 1, std::memory_order_relaxed);
}

void AudioEngine::padRelease(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    const int b = currentBank.load(std::memory_order_relaxed);
    const bool loopHeld = loopOn[b][padIndex].load(std::memory_order_relaxed);
    const bool sampleHeld = voices[padIndex].playingSample.load(std::memory_order_relaxed);

    if (gateMode.load(std::memory_order_relaxed) || loopHeld || sampleHeld) {
        voices[padIndex].gateClosed.store(true, std::memory_order_relaxed);
    }
}

void AudioEngine::setSeqPlaying(bool playing) {
    seqPlaying.store(playing, std::memory_order_relaxed);
    if (playing) {
        seqRestart.store(true, std::memory_order_relaxed);
    }
}

void AudioEngine::setSeqBpm(double bpm) {
    seqBpm.store(clampd(bpm, 30.0, 300.0), std::memory_order_relaxed);
}

void AudioEngine::setSeqSwing(double swing) {
    seqSwing.store(clampd(swing, 0.0, 0.5), std::memory_order_relaxed);
}

void AudioEngine::setSeqMask(int padIndex, int mask) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }
    const int b = currentBank.load(std::memory_order_relaxed);
    seqMask[b][padIndex].store(mask, std::memory_order_relaxed);
}

void AudioEngine::setLoopPoints(int padIndex, double startFrac, double endFrac) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    const int b = currentBank.load(std::memory_order_relaxed);

    startFrac = clampd(startFrac, 0.0, 1.0);
    endFrac = clampd(endFrac, 0.0, 1.0);

    if (endFrac < startFrac) {
        const double t = startFrac;
        startFrac = endFrac;
        endFrac = t;
    }

    loopStartFrac[b][padIndex].store(startFrac, std::memory_order_relaxed);
    loopEndFrac[b][padIndex].store(endFrac, std::memory_order_relaxed);
}

void AudioEngine::setLoopOn(int padIndex, bool enabled) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }
    const int b = currentBank.load(std::memory_order_relaxed);
    loopOn[b][padIndex].store(enabled, std::memory_order_relaxed);
}

bool AudioEngine::trimToLoop(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return false;
    }

    const int b = currentBank.load(std::memory_order_relaxed);

    std::lock_guard<std::mutex> lock(sampleMutex);

    auto src = samples[b][padIndex];
    if (!src || src->data.empty()) {
        return false;
    }

    const double s = loopStartFrac[b][padIndex].load(std::memory_order_relaxed);
    const double e = loopEndFrac[b][padIndex].load(std::memory_order_relaxed);

    if (e <= s) {
        return false;
    }

    const size_t n = src->data.size();
    size_t i0 = static_cast<size_t>(s * static_cast<double>(n));
    size_t i1 = static_cast<size_t>(e * static_cast<double>(n));

    if (i0 >= n) i0 = n - 1;
    if (i1 > n) i1 = n;
    if (i1 <= i0) i1 = i0 + 1;

    auto dst = std::make_shared<Sample>();
    dst->sampleRate = src->sampleRate;
    dst->data.assign(src->data.begin() + static_cast<long>(i0),
                     src->data.begin() + static_cast<long>(i1));

    samples[b][padIndex] = dst;

    loopStartFrac[b][padIndex].store(0.0, std::memory_order_relaxed);
    loopEndFrac[b][padIndex].store(1.0, std::memory_order_relaxed);

    if (!dataDir.empty()) {
        const std::string path = dataDir + "/b" + std::to_string(b) + "_p" + std::to_string(padIndex) + ".wav";
        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate), 1);
    }

    LOGI("Trimmed bank %d pad %d to %zu frames", b, padIndex, dst->data.size());
    return true;
}

std::vector<float> AudioEngine::getPeaks(int padIndex, int buckets) {
    std::vector<float> out(static_cast<size_t>(buckets > 0 ? buckets : 0), 0.0f);

    if (padIndex < 0 || padIndex >= kNumPads || buckets <= 0) {
        return out;
    }

    const int b = currentBank.load(std::memory_order_relaxed);

    std::shared_ptr<const Sample> s;
    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        s = samples[b][padIndex];
    }

    if (!s || s->data.empty()) {
        return out;
    }

    const size_t n = s->data.size();

    for (int bkt = 0; bkt < buckets; ++bkt) {
        size_t i0 = static_cast<size_t>(static_cast<double>(bkt) * static_cast<double>(n) / buckets);
        size_t i1 = static_cast<size_t>(static_cast<double>(bkt + 1) * static_cast<double>(n) / buckets);
        if (i1 <= i0) i1 = i0 + 1;
        if (i1 > n) i1 = n;

        const size_t stride = 1 + (i1 - i0) / 64;
        float m = 0.0f;

        for (size_t i = i0; i < i1; i += stride) {
            const float a = std::fabs(s->data[i]);
            if (a > m) m = a;
        }

        out[static_cast<size_t>(bkt)] = m;
    }

    return out;
}
