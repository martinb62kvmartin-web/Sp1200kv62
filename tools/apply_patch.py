import io
import os
import sys

PATCHES = [
    (
        "app/src/main/cpp/audio_engine.h",
        "    static constexpr int kNumPads = 8;",
        "    static constexpr int kNumPads = 16;"
    ),
    (
        "app/src/main/cpp/audio_engine.h",
        """    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);
""",
        """    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);

    void setPadVol(int padIndex, float vol);
    void setPadPan(int padIndex, float pan);
    void setMasterVol(float vol);
    void setMasterPan(float pan);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.h",
        """    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};
""",
        """    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};

    std::array<std::atomic<float>, kNumPads> padVol{};
    std::array<std::atomic<float>, kNumPads> padPan{};
    std::atomic<float> masterVol{1.0f};
    std::atomic<float> masterPan{0.0f};
"""
    ),
    (
        "app/src/main/cpp/audio_engine.h",
        """    float lpState = 0.0f;
""",
        """    float lpStateL = 0.0f;
    float lpStateR = 0.0f;
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    for (auto& s : solos) s.store(false);
""",
        """    for (auto& s : solos) s.store(false);
    for (auto& v : padVol) v.store(1.0f);
    for (auto& p : padPan) p.store(0.0f);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """void AudioEngine::setGateMode(bool enabled) {""",
        """void AudioEngine::setPadVol(int padIndex, float vol) {
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

void AudioEngine::setGateMode(bool enabled) {"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate) {
    FILE* f = std::fopen(path.c_str(), "wb");
    if (f == nullptr) {
        return false;
    }

    const uint32_t n = static_cast<uint32_t>(data.size());
    const uint32_t dataSize = n * 2;
    const uint32_t chunkSize = 36 + dataSize;
    const uint16_t one = 1;
    const uint16_t ch = 1;
    const uint16_t bps = 16;
    const uint32_t fmtSize = 16;
    const uint32_t byteRate = rate * 2;
    const uint16_t blockAlign = 2;
""",
        """bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate, int channels) {
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
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        writeWavFile(path, sample->data, static_cast<uint32_t>(rate));""",
        """        writeWavFile(path, sample->data, static_cast<uint32_t>(rate), 1);"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate));""",
        """        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate), 1);"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate));""",
        """    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate), 2);"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(1);
""",
        """    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(2);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        float mix = 0.0f;
""",
        """        float mixL = 0.0f;
        float mixR = 0.0f;
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """            mix += static_cast<float>(renderVoice(v) * v.envLevel);
""",
        """            {
                const int pIdx = v.padIndex;
                const float vol = padVol[pIdx].load(std::memory_order_relaxed);
                const float pan = padPan[pIdx].load(std::memory_order_relaxed);
                const float gl = vol * (pan < 0.0f ? 1.0f : 1.0f - pan);
                const float gr = vol * (pan > 0.0f ? 1.0f : 1.0f + pan);
                const float m = static_cast<float>(renderVoice(v) * v.envLevel);
                mixL += m * gl;
                mixR += m * gr;
            }
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        if (mix > 1.0f) {
            mix = 1.0f;
        } else if (mix < -1.0f) {
            mix = -1.0f;
        }

        if (crunch) {
            lpState += 0.35f * (mix - lpState);
            mix = vintage(lpState);
        }

        output[frame] = mix * 0.8f;
""",
        """        const float mv = masterVol.load(std::memory_order_relaxed);
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
"""
    ),
    (
        "app/src/main/cpp/native-lib.cpp",
        """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {""",
        """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadVol(JNIEnv*, jobject, jint padIndex, jfloat vol) {
    if (engine != nullptr) {
        engine->setPadVol(padIndex, vol);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadPan(JNIEnv*, jobject, jint padIndex, jfloat pan) {
    if (engine != nullptr) {
        engine->setPadPan(padIndex, pan);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMasterVol(JNIEnv*, jobject, jfloat vol) {
    if (engine != nullptr) {
        engine->setMasterVol(vol);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMasterPan(JNIEnv*, jobject, jfloat pan) {
    if (engine != nullptr) {
        engine->setMasterPan(pan);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {"""
    ),
]

def main():
    if not PATCHES:
        print("No patches to apply.")
        return

    for path, old, new in PATCHES:
        if not os.path.exists(path):
            print("ERROR: missing file", path)
            sys.exit(1)

        with io.open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if old not in text:
            print("ERROR: pattern not found in", path)
            print("PATTERN:", old[:120])
            sys.exit(1)

        text = text.replace(old, new, 1)

        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)

        print("Patched:", path)

main()
