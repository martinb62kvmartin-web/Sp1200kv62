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

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeLoadSample(JNIEnv*, jobject, jint padIndex, jint fd) {
    if (engine == nullptr) {
        return JNI_FALSE;
    }
    return engine->loadSample(padIndex, fd) ? JNI_TRUE : JNI_FALSE;
}

}
