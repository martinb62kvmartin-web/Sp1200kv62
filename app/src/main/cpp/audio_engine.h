#pragma once

#include <oboe/Oboe.h>
#include <array>
#include <atomic>
#include <memory>

class AudioEngine : public oboe::AudioStreamDataCallback {
public:
    AudioEngine();
    ~AudioEngine() override;

    bool start();
    void stop();
    void triggerPad(int padIndex);

    oboe::DataCallbackResult onAudioReady(
            oboe::AudioStream* stream,
            void* audioData,
            int32_t numFrames
    ) override;

private:
    static constexpr int kNumPads = 8;

    struct Voice {
        std::atomic<bool> active{false};
        std::atomic<double> amp{0.0};
        std::atomic<double> frequency{440.0};
        double phase = 0.0;
    };

    std::shared_ptr<oboe::AudioStream> outputStream;
    std::array<Voice, kNumPads> voices;
    std::array<double, kNumPads> frequencies{};
    double sampleRate = 48000.0;
    bool running = false;
};
