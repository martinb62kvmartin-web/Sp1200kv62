#include <jni.h>
#include "audio_engine.h"

static AudioEngine* engine = nullptr;

extern "C" {

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetup(JNIEnv*, jobject) {
    if (engine == nullptr) {
        engine = new AudioEngine();
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeStart(JNIEnv*, jobject) {
    if (engine != nullptr) {
        engine->start();
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeStop(JNIEnv*, jobject) {
    if (engine != nullptr) {
        engine->stop();
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeRelease(JNIEnv*, jobject) {
    delete engine;
    engine = nullptr;
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeTriggerPad(JNIEnv*, jobject, jint padIndex) {
    if (engine != nullptr) {
        engine->triggerPad(padIndex);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativePadRelease(JNIEnv*, jobject, jint padIndex) {
    if (engine != nullptr) {
        engine->padRelease(padIndex);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetGateMode(JNIEnv*, jobject, jboolean enabled) {
    if (engine != nullptr) {
        engine->setGateMode(enabled == JNI_TRUE);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPitch(JNIEnv*, jobject, jfloat semitones) {
    if (engine != nullptr) {
        engine->setPitchSemitones(static_cast<double>(semitones));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetCrunch(JNIEnv*, jobject, jboolean enabled) {
    if (engine != nullptr) {
        engine->setCrunch(enabled == JNI_TRUE);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetBank(JNIEnv*, jobject, jint bank) {
    if (engine != nullptr) {
        engine->setBank(static_cast<int>(bank));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMute(JNIEnv*, jobject, jint padIndex, jboolean enabled) {
    if (engine != nullptr) {
        engine->setMute(padIndex, enabled == JNI_TRUE);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetSolo(JNIEnv*, jobject, jint padIndex, jboolean enabled) {
    if (engine != nullptr) {
        engine->setSolo(padIndex, enabled == JNI_TRUE);
    }
}

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeLoadSample(JNIEnv*, jobject, jint padIndex, jint fd) {
    if (engine == nullptr) {
        return JNI_FALSE;
    }
    return engine->loadSample(padIndex, fd) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSeqSetPlaying(JNIEnv*, jobject, jboolean playing) {
    if (engine != nullptr) {
        engine->setSeqPlaying(playing == JNI_TRUE);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSeqSetBpm(JNIEnv*, jobject, jfloat bpm) {
    if (engine != nullptr) {
        engine->setSeqBpm(static_cast<double>(bpm));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSeqSetSwing(JNIEnv*, jobject, jfloat swing) {
    if (engine != nullptr) {
        engine->setSeqSwing(static_cast<double>(swing));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSeqSetMask(JNIEnv*, jobject, jint padIndex, jint mask) {
    if (engine != nullptr) {
        engine->setSeqMask(padIndex, static_cast<int>(mask));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetRoll(JNIEnv*, jobject, jint padIndex, jint step, jint value) {
    if (engine != nullptr) {
        engine->setRoll(padIndex, static_cast<int>(step), static_cast<int>(value));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetLoopPoints(JNIEnv*, jobject, jint padIndex, jfloat startFrac, jfloat endFrac) {
    if (engine != nullptr) {
        engine->setLoopPoints(padIndex, static_cast<double>(startFrac), static_cast<double>(endFrac));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetLoopOn(JNIEnv*, jobject, jint padIndex, jboolean enabled) {
    if (engine != nullptr) {
        engine->setLoopOn(padIndex, enabled == JNI_TRUE);
    }
}

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeTrimToLoop(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) {
        return JNI_FALSE;
    }
    return engine->trimToLoop(padIndex) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jfloatArray JNICALL
Java_com_example_sp1200_MainActivity_nativeGetPeaks(JNIEnv* env, jobject, jint padIndex, jint buckets) {
    jfloatArray result = env->NewFloatArray(buckets > 0 ? buckets : 1);

    if (engine == nullptr || result == nullptr) {
        return result;
    }

    std::vector<float> peaks = engine->getPeaks(padIndex, buckets);

    env->SetFloatArrayRegion(result, 0, static_cast<jsize>(peaks.size()), peaks.data());

    return result;
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadParams(JNIEnv*, jobject, jint padIndex,
                                                        jfloat pitch, jfloat attack, jfloat decay,
                                                        jfloat sustain, jfloat release) {
    if (engine != nullptr) {
        engine->setPadParams(padIndex,
                             static_cast<double>(pitch),
                             static_cast<double>(attack),
                             static_cast<double>(decay),
                             static_cast<double>(sustain),
                             static_cast<double>(release));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {
    if (engine != nullptr) {
        engine->setMidiMode(static_cast<int>(mode));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeMidiTick(JNIEnv*, jobject) {
    if (engine != nullptr) {
        engine->midiTick();
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeMidiStart(JNIEnv*, jobject) {
    if (engine != nullptr) {
        engine->midiStart();
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeMidiStop(JNIEnv*, jobject) {
    if (engine != nullptr) {
        engine->midiStop();
    }
}

JNIEXPORT jlong JNICALL
Java_com_example_sp1200_MainActivity_nativeGetMidiTicks(JNIEnv*, jobject) {
    if (engine == nullptr) {
        return 0;
    }
    return static_cast<jlong>(engine->getMidiTicksOut());
}

}
