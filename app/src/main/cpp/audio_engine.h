#pragma once

#include <oboe/Oboe.h>
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
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
    bool loadSample(int padIndex, int fd);

    void setSeqPlaying(bool playing);
    void setSeqBpm(double bpm);
    void setSeqSwing(double swing);
    void setSeqMask(int padIndex, int mask);

    void setLoopPoints(int padIndex, double startFrac, double endFrac);
    void setLoopOn(int padIndex, bool enabled);
    bool trimToLoop(int padIndex);
    std::vector<float> getPeaks(int padIndex, int buckets);

    oboe::DataCallbackResult onAudioReady(
            oboe::AudioStream* stream,
            void* audioData,
            int32_t numFrames
    ) override;

private:
    static constexpr int kNumPads = 8;
    static constexpr int kSteps = 16;

    struct Voice {
        std::atomic<bool> active{false};
        std::atomic<bool> resetRequest{false};
        std::atomic<bool> hasNextSample{false};
        std::atomic<bool> gateClosed{false};
        std::atomic<int> type{0};

        std::shared_ptr<const Sample> sample;
        std::shared_ptr<const Sample> nextSample;
        double pos = 0.0;

        int padIndex = 0;
        bool loopEnabled = false;
        double loopStart = 0.0;
        double loopEnd = 0.0;

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
    void triggerVoice(int padIndex);
    void fireStep(int step);

    std::shared_ptr<oboe::AudioStream> outputStream;
    std::array<Voice, kNumPads> voices;
    std::array<std::shared_ptr<const Sample>, kNumPads> samples;
    std::mutex sampleMutex;
    std::atomic<bool> gateMode{false};
    std::atomic<double> pitchRate{1.0};

    std::atomic<bool> seqPlaying{false};
    std::atomic<bool> seqRestart{false};
    std::atomic<double> seqBpm{90.0};
    std::atomic<double> seqSwing{0.0};
    std::array<std::atomic<int>, kNumPads> seqMask{};
    double totalFrames = 0.0;
    double nextStepFrame = 0.0;
    int seqStep = 0;

    std::array<std::atomic<double>, kNumPads> loopStartFrac{};
    std::array<std::atomic<double>, kNumPads> loopEndFrac{};
    std::array<std::atomic<bool>, kNumPads> loopOn{};

    double sampleRate = 48000.0;
    double releaseFactor = 0.999;
    bool running = false;
};
