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

void AudioEngine::setPadStretch(int padIndex, int steps) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    if (steps < 0) steps = 0;
    if (steps > 256) steps = 256;
    const int b = currentBank.load(std::memory_order_relaxed);
    padStretch[b][padIndex].store(steps, std::memory_order_relaxed);
}

static void saveSampleToDir(const std::string& dir, int b, int p, const std::vector<float>& data, uint32_t rate) {
    if (dir.empty() || data.empty()) return;
    const std::string path = dir + "/b" + std::to_string(b) + "_p" + std::to_string(p) + ".wav";
    writeWavFile(path, data, rate, 1);
}

bool AudioEngine::normalizePad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return false;
    float m = 0.0f;
    for (float v : s->data) { const float a = v < 0 ? -v : v; if (a > m) m = a; }
    if (m < 0.0001f) return false;
    const float k = 1.0f / m;
    for (float& v : s->data) v *= k;
    saveSampleToDir(dataDir, b, padIndex, s->data, static_cast<uint32_t>(s->sampleRate));
    return true;
}

bool AudioEngine::trimSilencePad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return false;
    const float th = 0.02f;
    size_t i0 = 0, i1 = s->data.size();
    while (i0 < i1) { const float a = s->data[i0] < 0 ? -s->data[i0] : s->data[i0]; if (a > th) break; i0++; }
    while (i1 > i0) { const float a = s->data[i1 - 1] < 0 ? -s->data[i1 - 1] : s->data[i1 - 1]; if (a > th) break; i1--; }
    if (i1 <= i0 || (i0 == 0 && i1 == s->data.size())) return false;
    std::vector<float> cut(s->data.begin() + i0, s->data.begin() + i1);
    auto dst = std::make_shared<Sample>();
    dst->sampleRate = s->sampleRate;
    dst->data = std::move(cut);
    samples[b][padIndex] = dst;
    saveSampleToDir(dataDir, b, padIndex, dst->data, static_cast<uint32_t>(dst->sampleRate));
    return true;
}

bool AudioEngine::makeMonoPad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    return samples[b][padIndex] != nullptr;
}

bool AudioEngine::bouncePad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return false;
    float st = 0.0f;
    for (float& v : s->data) {
        st += 0.35f * (v - st);
        v = vintage(st);
    }
    saveSampleToDir(dataDir, b, padIndex, s->data, static_cast<uint32_t>(s->sampleRate));
    return true;
}

int AudioEngine::autoChop(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return 0;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::shared_ptr<const Sample> src;
    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        src = samples[b][padIndex];
        if (!src || src->data.empty()) return 0;
    }
    const size_t n = src->data.size();
    const int slices = 16;
    for (int p = 0; p < slices; ++p) {
        size_t a = n * static_cast<size_t>(p) / slices;
        size_t z = n * static_cast<size_t>(p + 1) / slices;
        if (z <= a) z = a + 1;
        auto dst = std::make_shared<Sample>();
        dst->sampleRate = src->sampleRate;
        dst->data.assign(src->data.begin() + a, src->data.begin() + z);
        {
            std::lock_guard<std::mutex> lock(sampleMutex);
            samples[b][p] = dst;
        }
        saveSampleToDir(dataDir, b, p, dst->data, static_cast<uint32_t>(dst->sampleRate));
    }
    return slices;
}

int AudioEngine::splitStems(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return 0;
    const int b = currentBank.load(std::memory_order_relaxed);
    const int p2 = (padIndex + 1) % kNumPads;
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return 0;
    std::vector<float> low(s->data.size()), high(s->data.size());
    float lp = 0.0f;
    const float k = 0.15f;
    for (size_t i = 0; i < s->data.size(); ++i) {
        lp += k * (s->data[i] - lp);
        low[i] = lp;
        high[i] = s->data[i] - lp;
    }
    auto dLow = std::make_shared<Sample>();
    dLow->sampleRate = s->sampleRate;
    dLow->data = std::move(low);
    auto dHigh = std::make_shared<Sample>();
    dHigh->sampleRate = s->sampleRate;
    dHigh->data = std::move(high);
    samples[b][padIndex] = dLow;
    samples[b][p2] = dHigh;
    saveSampleToDir(dataDir, b, padIndex, dLow->data, static_cast<uint32_t>(dLow->sampleRate));
    saveSampleToDir(dataDir, b, p2, dHigh->data, static_cast<uint32_t>(dHigh->sampleRate));
    return 2;
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
std::shared_ptr<Sample> AudioEngine::parseWav(const std::vector<uint8_t>& bytes) {
    if (bytes.size() < 44) {
        return nullptr;
    }

    if (std::memcmp(bytes.data(), "RIFF", 4) != 0 ||
        std::memcmp(bytes.data() + 8, "WAVE", 4) != 0) {
        return nullptr;
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
        return nullptr;
    }

    if (!(format == 1 && bits == 16)) {
        return nullptr;
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

    return sample;
}

bool AudioEngine::previewFromFd(int fd) {
    if (fd < 0) {
        return false;
    }

    std::vector<uint8_t> bytes;
    uint8_t buf[65536];
    ssize_t n;
    while ((n = ::read(fd, buf, sizeof(buf))) > 0) {
        bytes.insert(bytes.end(), buf, buf + n);
    }

    auto s = parseWav(bytes);
    if (!s) {
        return false;
    }

    Voice& v = voices[kNumPads];

    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        v.nextSample = s;
    }

    v.bank = currentBank.load(std::memory_order_relaxed);
    v.nextPitchAdd.store(0.0, std::memory_order_relaxed);
    v.gateClosed.store(false, std::memory_order_relaxed);
    v.type.store(0, std::memory_order_relaxed);
    v.hasNextSample.store(true, std::memory_order_relaxed);
    v.resetRequest.store(true, std::memory_order_relaxed);
    v.active.store(true, std::memory_order_relaxed);

    return true;
}

bool AudioEngine::loadSample(int padIndex, int fd) {
    if (padIndex < 0 || padIndex >= kNumPads || fd < 0) {
        return false;
    }

    const int b = currentBank.load(std::memory_order_relaxed);

    std::vector<uint8_t> bytes;
    uint8_t buf[65536];
    ssize_t n;
    while ((n = ::read(fd, buf, sizeof(buf))) > 0) {
        bytes.insert(bytes.end(), buf, buf + n);
    }

    auto sample = parseWav(bytes);
    if (!sample) {
        LOGI("Failed to parse WAV");
        return false;
    }

    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        samples[b][padIndex] = sample;
    }

    loopStartFrac[b][padIndex].store(0.0, std::memory_order_relaxed);
    loopEndFrac[b][padIndex].store(1.0, std::memory_order_relaxed);

    if (!dataDir.empty()) {
        const std::string path = dataDir + "/b" + std::to_string(b) + "_p" + std::to_string(padIndex) + ".wav";
        FILE* f = std::fopen(path.c_str(), "wb");
        if (f != nullptr) {
            std::fwrite(bytes.data(), 1, bytes.size(), f);
            std::fclose(f);
        }
    }

    LOGI("Loaded sample bank %d pad %d, frames=%zu", b, padIndex, sample->data.size());
    return true;
}

void AudioEngine::triggerVoice(int padIndex, double semiAdd) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }

    bool audible;
    if (soloCount.load(std::memory_order_relaxed) > 0) {
        audible = solos[padIndex].load(std::memory_order_relaxed);
    } else {
        audible = !mutes[padIndex].load(std::memory_order_relaxed);
    }

    if (!audible) {
        return;
    }

    const int b = currentBank.load(std::memory_order_relaxed);
    Voice& voice = voices[padIndex];

    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        voice.nextSample = samples[b][padIndex];
    }

    voice.bank = b;
    voice.nextPitchAdd.store(semiAdd, std::memory_order_relaxed);
    voice.gateClosed.store(false, std::memory_order_relaxed);
    voice.type.store(padIndex, std::memory_order_relaxed);
    voice.hasNextSample.store(true, std::memory_order_relaxed);
    voice.resetRequest.store(true, std::memory_order_relaxed);
    voice.active.store(true, std::memory_order_relaxed);

    padHits[padIndex].fetch_add(1, std::memory_order_relaxed);
}

void AudioEngine::triggerPad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) {
        return;
    }
    triggerVoice(padIndex, 0.0);
}

void AudioEngine::fireStep(int step) {
    currentStepPublic.store(step, std::memory_order_relaxed);

    const int b = currentBank.load(std::memory_order_relaxed);

    for (int p = 0; p < kNumPads; ++p) {
        if (rollEndAt[p] == step) {
            voices[p].gateClosed.store(true, std::memory_order_relaxed);
            rollEndAt[p] = -1;
        }

        const int m = seqMask[b][p].load(std::memory_order_relaxed);
        if ((m & (1 << step)) != 0) {
            triggerVoice(p, 0.0);
        }

        const int rp = rollPitch[b][p][step].load(std::memory_order_relaxed);
        if (rp != 0) {
            const int len = rollLen[b][p][step].load(std::memory_order_relaxed);
            triggerVoice(p, static_cast<double>(rp - 13));
            rollEndAt[p] = step + (len > 0 ? len : 1);
        }
    }
}

double AudioEngine::nextNoise(Voice& v) {
    v.rng = v.rng * 1664525u + 1013904223u;
    return (static_cast<double>(v.rng) / 2147483648.0) - 1.0;
}

double AudioEngine::renderVoice(Voice& v) {
    const double rate = pitchRate.load(std::memory_order_relaxed) * v.rate;
    const bool crunch = crunchOn.load(std::memory_order_relaxed);

    if (v.sample && !v.sample->data.empty()) {
        const std::vector<float>& d = v.sample->data;
        const double step = (v.sample->sampleRate / sampleRate) * rate;

        if (v.reverse) {
            if (v.pos < 0.0) {
                v.amp = 0.0;
                return 0.0;
            }
            const size_t i = static_cast<size_t>(v.pos);
            if (i >= d.size()) {
                v.amp = 0.0;
                return 0.0;
            }
            double out;
            if (crunch) {
                out = d[i];
            } else {
                const size_t i1 = (i + 1 < d.size()) ? i + 1 : i;
                const double frac = v.pos - static_cast<double>(i);
                out = d[i] + (d[i1] - d[i]) * frac;
            }
            v.pos -= step;
            if (v.loopEnabled && v.loopEnd > v.loopStart + 1.0 && v.pos <= v.loopStart) {
                v.pos = v.loopEnd - 1.0;
            }
            return out * v.amp;
        }

        const size_t i = static_cast<size_t>(v.pos);

        if (i + 1 >= d.size()) {
            v.amp = 0.0;
            return 0.0;
        }

        double out;
        if (crunch) {
            out = d[i];
        } else {
            const double frac = v.pos - static_cast<double>(i);
            out = d[i] + (d[i + 1] - d[i]) * frac;
        }

        v.pos += step;

        if (v.loopEnabled && v.loopEnd > v.loopStart + 1.0 && v.pos >= v.loopEnd) {
            v.pos = v.loopStart;
        }

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
    if (stream->getDirection() == oboe::Direction::Input) {
        if (recording.load(std::memory_order_relaxed)) {
            const float* in = static_cast<const float*>(audioData);
            std::lock_guard<std::mutex> lock(recMutex);
            recBuffer.insert(recBuffer.end(), in, in + numFrames);
            recRate = stream->getSampleRate();
        }
        return oboe::DataCallbackResult::Continue;
    }

    auto* output = static_cast<float*>(audioData);

    if (sampleRate <= 0.0 && stream != nullptr) {
        sampleRate = stream->getSampleRate();
    }

    if (sampleRate <= 0.0) {
        sampleRate = 48000.0;
    }

    const int midiModeNow = midiMode.load(std::memory_order_relaxed);
    const bool seqOn = seqPlaying.load(std::memory_order_relaxed);
    const bool crunch = crunchOn.load(std::memory_order_relaxed);
    double fps = 0.0;
    double swingOff = 0.0;
    double tickInterval = 0.0;

    if (seqOn && midiModeNow != 2) {
        const double bpm = seqBpm.load(std::memory_order_relaxed);
        fps = (60.0 / bpm) * sampleRate / 4.0;
        swingOff = seqSwing.load(std::memory_order_relaxed) * fps;
        tickInterval = fps / 6.0;
    }

    const double dt = 1.0 / sampleRate;

    float pk[16] = {0};
    float ml = 0.0f;
    float mr = 0.0f;

    for (int32_t frame = 0; frame < numFrames; ++frame) {
        const double absolute = totalFrames + static_cast<double>(frame);

        if (seqOn && midiModeNow == 2) {
            if (midiStartReq.exchange(false, std::memory_order_relaxed)) {
                seqStep = 0;
                tickAccum = 0;
                seqPlaying.store(true, std::memory_order_relaxed);
            }

            if (midiStopReq.exchange(false, std::memory_order_relaxed)) {
                seqPlaying.store(false, std::memory_order_relaxed);
            }

            const int t = pendingTicks.exchange(0, std::memory_order_relaxed);
            tickAccum += t;

            while (tickAccum >= 6) {
                tickAccum -= 6;
                fireStep(seqStep);
                seqStep = (seqStep + 1) % kSteps;
            }
        } else if (seqOn) {
            if (seqRestart.exchange(false, std::memory_order_relaxed)) {
                nextStepFrame = absolute;
                nextTickFrame = absolute;
                seqStep = 0;
                tickAccum = 0;
            }

            if (nextStepFrame < absolute - sampleRate) {
                nextStepFrame = absolute;
            }
            if (nextTickFrame < absolute - sampleRate) {
                nextTickFrame = absolute;
            }

            while (absolute >= nextTickFrame && tickInterval > 0.0) {
                midiTicksOut.fetch_add(1, std::memory_order_relaxed);
                nextTickFrame += tickInterval;
            }

            while (absolute >= nextStepFrame) {
                fireStep(seqStep);

                const int i = seqStep;
                const int next = (i + 1) % kSteps;
                double delta = fps;
                if (next % 2 == 1) delta += swingOff;
                if (i % 2 == 1) delta -= swingOff;
                nextStepFrame += delta;
                seqStep = next;
            }
        }

        float mixL = 0.0f;
        float mixR = 0.0f;

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
                const int b = v.bank;
                v.padIndex = type;
                v.age = 0;
                v.phase = 0.0;
                v.phase2 = 0.0;
                v.prevNoise = 0.0;
                v.amp = 1.0;
                v.rng = 123456789u + static_cast<uint32_t>(type) * 999983u;

                v.pitchAddSemi = v.nextPitchAdd.load(std::memory_order_relaxed);
                v.rate = std::pow(2.0,
                        (padPitch[b][type].load(std::memory_order_relaxed) + v.pitchAddSemi) / 12.0);

                const int stNow = padStretch[b][type].load(std::memory_order_relaxed);
                if (stNow > 0 && v.sample && !v.sample->data.empty()) {
                    const double dur = static_cast<double>(v.sample->data.size()) / v.sample->sampleRate;
                    const double bpmNow = seqBpm.load(std::memory_order_relaxed);
                    const double target = static_cast<double>(stNow) * (60.0 / bpmNow) / 4.0;
                    if (target > 0.01 && dur > 0.01) {
                        v.rate *= dur / target;
                    }
                }
                v.aT = padA[b][type].load(std::memory_order_relaxed);
                v.dT = padD[b][type].load(std::memory_order_relaxed);
                v.sL = padS[b][type].load(std::memory_order_relaxed);
                v.rT = padR[b][type].load(std::memory_order_relaxed);

                if (v.sample && !v.sample->data.empty()) {
                    v.reverse = padRev[b][type].load(std::memory_order_relaxed);
                    v.pos = v.reverse ? static_cast<double>(v.sample->data.size() - 2) : 0.0;
                    if (v.pos < 0.0) v.pos = 0.0;
                    v.loopEnabled = loopOn[b][type].load(std::memory_order_relaxed);
                    const double sz = static_cast<double>(v.sample->data.size());
                    v.loopStart = loopStartFrac[b][type].load(std::memory_order_relaxed) * sz;
                    v.loopEnd = loopEndFrac[b][type].load(std::memory_order_relaxed) * sz;
                } else {
                    v.reverse = false;
                    v.pos = 0.0;
                    v.loopEnabled = false;
                }

                v.envLevel = (v.aT <= 0.001) ? 1.0 : 0.0;
                v.envStage = (v.aT <= 0.001) ? 1 : 0;
                v.relStart = 0.0;
                v.relTime = 0.0;

                v.playingSample.store(v.sample && !v.sample->data.empty(),
                        std::memory_order_relaxed);

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

            if (v.gateClosed.load(std::memory_order_relaxed) && v.envStage < 3) {
                v.envStage = 3;
                v.relStart = v.envLevel;
                v.relTime = 0.0;
            }

            switch (v.envStage) {
                case 0:
                    v.envLevel += dt / v.aT;
                    if (v.envLevel >= 1.0) {
                        v.envLevel = 1.0;
                        v.envStage = 1;
                    }
                    break;
                case 1:
                    if (v.dT <= 0.001) {
                        v.envLevel = v.sL;
                        v.envStage = 2;
                    } else {
                        v.envLevel -= dt * (1.0 - v.sL) / v.dT;
                        if (v.envLevel <= v.sL) {
                            v.envLevel = v.sL;
                            v.envStage = 2;
                        }
                    }
                    break;
                case 2:
                    v.envLevel = v.sL;
                    break;
                case 3:
                    v.relTime += dt;
                    if (v.rT <= 0.001) {
                        v.envLevel = 0.0;
                    } else {
                        const double k = v.relStart * (1.0 - v.relTime / v.rT);
                        v.envLevel = (k > 0.0) ? k : 0.0;
                    }
                    break;
                default:
                    break;
            }

            const bool envDone = (v.envStage == 3 && v.envLevel <= 0.0);

            if (v.amp < 0.0005 || envDone) {
                v.active.store(false, std::memory_order_relaxed);
                continue;
            }

            {
                const int pIdx = v.padIndex;
                const float vol = padVol[pIdx].load(std::memory_order_relaxed);
                const float pan = padPan[pIdx].load(std::memory_order_relaxed);
                const float gl = vol * (pan < 0.0f ? 1.0f : 1.0f - pan);
                const float gr = vol * (pan > 0.0f ? 1.0f : 1.0f + pan);
                const float m = static_cast<float>(renderVoice(v) * v.envLevel);
                mixL += m * gl;
                mixR += m * gr;

                const float am = m < 0 ? -m : m;
                if (pIdx >= 0 && pIdx < 16 && am > pk[pIdx]) pk[pIdx] = am;
            }

            if (!v.sample || v.sample->data.empty()) {
                v.amp *= v.decay;
            }
        }

        const float mv = masterVol.load(std::memory_order_relaxed);
        const float mp = masterPan.load(std::memory_order_relaxed);
        float L = mixL * mv * (mp < 0.0f ? 1.0f : 1.0f - mp);
        float R = mixR * mv * (mp > 0.0f ? 1.0f : 1.0f + mp);

        if (L > 1.0f) L = 1.0f; else if (L < -1.0f) L = -1.0f;
        if (R > 1.0f) R = 1.0f; else if (R < -1.0f) R = -1.0f;

        if (crunch) {
            lpStateL += 0.35f * (L - lpStateL);
            L = vintage(lpStateL);
            lpStateR += 0.35f * (R - lpStateR);
            R = vintage(lpStateR);
        }

        output[frame * 2] = L * 0.8f;
        output[frame * 2 + 1] = R * 0.8f;

        const float al = L < 0 ? -L : L;
        const float ar = R < 0 ? -R : R;
        if (al > ml) ml = al;
        if (ar > mr) mr = ar;
    }

    for (int i = 0; i < 16; ++i) {
        const float old = padLevel[i].load(std::memory_order_relaxed) * 0.8f;
        padLevel[i].store(pk[i] > old ? pk[i] : old, std::memory_order_relaxed);
    }
    const float oldL = levelL.load(std::memory_order_relaxed) * 0.8f;
    levelL.store(ml > oldL ? ml : oldL, std::memory_order_relaxed);
    const float oldR = levelR.load(std::memory_order_relaxed) * 0.8f;
    levelR.store(mr > oldR ? mr : oldR, std::memory_order_relaxed);

    if (capturing.load(std::memory_order_relaxed)) {
        std::lock_guard<std::mutex> lock(capMutex);
        if (capBuf.size() < static_cast<size_t>(sampleRate) * 240) {
            capBuf.insert(capBuf.end(), output, output + numFrames * 2);
        }
    }

    totalFrames += static_cast<double>(numFrames);

    return oboe::DataCallbackResult::Continue;
}
