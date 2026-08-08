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

}