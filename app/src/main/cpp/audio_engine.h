#pragma once

#include <oboe/Oboe.h>
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

struct Sample {
    std::vector<float> data;
    double sampleRate = 44100.0;
};

class AudioEngine : public oboe::AudioStreamDataCallback {
public:
    AudioEngine();
    ~AudioEngine() override;

    bool start();
    void stop();
    void triggerPad(int padIndex);
    void padRelease(int padIndex);
    void setGateMode(bool enabled);
    void setPitchSemitones(double semitones);
    void setCrunch(bool enabled);
    bool loadSample(int padIndex, int fd);
    bool previewFromFd(int fd);
    void clearPad(int padIndex);
    void setPadReverse(int padIndex, bool enabled);
    void setPadStretch(int padIndex, int steps);

    bool normalizePad(int padIndex);
    bool trimSilencePad(int padIndex);
    bool makeMonoPad(int padIndex);
    bool bouncePad(int padIndex);
    int autoChop(int padIndex);
    int splitStems(int padIndex);

    void setBank(int bank);
    void setMute(int padIndex, bool enabled);
    void setSolo(int padIndex, bool enabled);

    void setSeqPlaying(bool playing);
    void setSeqBpm(double bpm);
    void setSeqSwing(double swing);
    void setSeqMask(int padIndex, int mask);
    void setRoll(int padIndex, int step, int value, int len);

    void setLoopPoints(int padIndex, double startFrac, double endFrac);
    void setLoopOn(int padIndex, bool enabled);
    bool trimToLoop(int padIndex);
    std::vector<float> getPeaks(int padIndex, int buckets);

    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);

    void setPadVol(int padIndex, float vol);
    void setPadPan(int padIndex, float pan);
    void setMasterVol(float vol);
    void setMasterPan(float pan);

    std::array<float, 18> getLevels();

    void setMidiMode(int mode);
    void midiTick();
    void midiStart();
    void midiStop();
    long long getMidiTicksOut();

    void setDataDir(const std::string& dir);
    int getCurrentStep();
    long long getPadHits(int padIndex);

    bool startRecording(int padIndex);
    bool stopRecording();

    void startCapture();
    bool stopCapture(const std::string& path);

    oboe::DataCallbackResult onAudioReady(
            oboe::AudioStream* stream,
            void* audioData,
            int32_t numFrames
    ) override;

private:
    static constexpr int kNumPads = 16;
    static constexpr int kSteps = 16;
    static constexpr int kBanks = 4;

    struct Voice {
        std::atomic<bool> active{false};
        std::atomic<bool> resetRequest{false};
        std::atomic<bool> hasNextSample{false};
        std::atomic<bool> gateClosed{false};
        std::atomic<bool> playingSample{false};
        std::atomic<int> type{0};

        std::shared_ptr<const Sample> sample;
        std::shared_ptr<const Sample> nextSample;
        double pos = 0.0;
        bool reverse = false;

        int padIndex = 0;
        int bank = 0;
        bool loopEnabled = false;
        double loopStart = 0.0;
        double loopEnd = 0.0;

        std::atomic<double> nextPitchAdd{0.0};
        double pitchAddSemi = 0.0;
        double rate = 1.0;
        double aT = 0.0;
        double dT = 0.0;
        double sL = 1.0;
        double rT = 0.05;

        double envLevel = 0.0;
        int envStage = 0;
        double relStart = 0.0;
        double relTime = 0.0;

        double amp = 0.0;
        double decay = 0.9999;
        double phase = 0.0;
        double phase2 = 0.0;
        double prevNoise = 0.0;
        uint32_t rng = 123456789u;
        int age = 0;
    };

    double renderVoice(Voice& voice);
    double nextNoise(Voice& voice);
    void triggerVoice(int padIndex, double semiAdd);
    void fireStep(int step);
    std::shared_ptr<Sample> parseWav(const std::vector<uint8_t>& bytes);

    std::shared_ptr<oboe::AudioStream> outputStream;
    std::shared_ptr<oboe::AudioStream> inputStream;
    std::array<Voice, kNumPads + 1> voices;
    std::array<std::array<std::shared_ptr<const Sample>, kNumPads>, kBanks> samples{};
    std::mutex sampleMutex;
    std::atomic<bool> gateMode{false};
    std::atomic<bool> crunchOn{true};
    std::atomic<double> pitchRate{1.0};
    std::atomic<int> currentBank{0};

    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};

    std::array<std::array<std::atomic<bool>, kNumPads>, kBanks> padRev{};
    std::array<std::array<std::atomic<int>, kNumPads>, kBanks> padStretch{};

    std::array<std::atomic<float>, kNumPads> padVol{};
    std::array<std::atomic<float>, kNumPads> padPan{};
    std::atomic<float> masterVol{1.0f};
    std::atomic<float> masterPan{0.0f};

    std::array<std::atomic<float>, kNumPads> padLevel{};
    std::atomic<float> levelL{0.0f};
    std::atomic<float> levelR{0.0f};

    std::atomic<bool> seqPlaying{false};
    std::atomic<bool> seqRestart{false};
    std::atomic<double> seqBpm{90.0};
    std::atomic<double> seqSwing{0.0};
    std::array<std::array<std::atomic<int>, kNumPads>, kBanks> seqMask{};
    std::array<std::array<std::array<std::atomic<int>, kSteps>, kNumPads>, kBanks> rollPitch{};
    std::array<std::array<std::array<std::atomic<int>, kSteps>, kNumPads>, kBanks> rollLen{};
    std::array<int, kNumPads> rollEndAt{};
    double totalFrames = 0.0;
    double nextStepFrame = 0.0;
    double nextTickFrame = 0.0;
    int seqStep = 0;
    std::atomic<int> currentStepPublic{0};
    std::array<std::atomic<long long>, kNumPads> padHits{};

    std::atomic<int> midiMode{0};
    std::atomic<long long> midiTicksOut{0};
    std::atomic<int> pendingTicks{0};
    std::atomic<bool> midiStartReq{false};
    std::atomic<bool> midiStopReq{false};
    int tickAccum = 0;

    std::atomic<bool> capturing{false};
    std::mutex capMutex;
    std::vector<float> capBuf;

    std::string dataDir;
    std::atomic<bool> recording{false};
    std::mutex recMutex;
    std::vector<float> recBuffer;
    double recRate = 48000.0;
    int recPad = 0;
    int recBank = 0;

    float lpStateL = 0.0f;
    float lpStateR = 0.0f;

    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> loopStartFrac{};
    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> loopEndFrac{};
    std::array<std::array<std::atomic<bool>, kNumPads>, kBanks> loopOn{};

    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> padPitch{};
    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> padA{};
    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> padD{};
    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> padS{};
    std::array<std::array<std::atomic<double>, kNumPads>, kBanks> padR{};

    double sampleRate = 48000.0;
    bool running = false;
};
