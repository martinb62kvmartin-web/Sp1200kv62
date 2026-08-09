import io
import os
import sys

PATCHES = [
    (
        "app/src/main/cpp/audio_engine.h",
        """    void startCapture();
    bool stopCapture(const std::string& path);
""",
        """    void startCapture();
    bool stopCapture(const std::string& path);

    void setSongOn(bool enabled);
    void setSongLen(int len);
    void setSongBank(int slot, int bank);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.h",
        """    std::atomic<bool> capturing{false};
    std::mutex capMutex;
    std::vector<float> capBuf;
""",
        """    std::atomic<bool> capturing{false};
    std::mutex capMutex;
    std::vector<float> capBuf;

    std::atomic<bool> songOn{false};
    std::atomic<int> songLen{0};
    std::array<std::atomic<int>, 32> songBanks{};
    int songBar = 0;
    int playBank = 0;
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    for (auto& e : rollEndAt) e = -1;
""",
        """    for (auto& e : rollEndAt) e = -1;
    for (auto& s : songBanks) s.store(0);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """void AudioEngine::setGateMode(bool enabled) {""",
        """void AudioEngine::setSongOn(bool enabled) {
    songOn.store(enabled, std::memory_order_relaxed);
}

void AudioEngine::setSongLen(int len) {
    if (len < 0) len = 0;
    if (len > 32) len = 32;
    songLen.store(len, std::memory_order_relaxed);
}

void AudioEngine::setSongBank(int slot, int bank) {
    if (slot < 0 || slot >= 32) return;
    if (bank < 0 || bank >= kBanks) return;
    songBanks[slot].store(bank, std::memory_order_relaxed);
}

void AudioEngine::setGateMode(bool enabled) {"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """void AudioEngine::fireStep(int step) {
    currentStepPublic.store(step, std::memory_order_relaxed);

    const int b = currentBank.load(std::memory_order_relaxed);
""",
        """void AudioEngine::fireStep(int step) {
    currentStepPublic.store(step, std::memory_order_relaxed);

    const int b = playBank;
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """            if (seqRestart.exchange(false, std::memory_order_relaxed)) {
                nextStepFrame = absolute;
                nextTickFrame = absolute;
                seqStep = 0;
                tickAccum = 0;
            }
""",
        """            if (seqRestart.exchange(false, std::memory_order_relaxed)) {
                nextStepFrame = absolute;
                nextTickFrame = absolute;
                seqStep = 0;
                tickAccum = 0;
                songBar = 0;
                playBank = (songOn.load(std::memory_order_relaxed) && songLen.load(std::memory_order_relaxed) > 0)
                        ? songBanks[0].load(std::memory_order_relaxed)
                        : currentBank.load(std::memory_order_relaxed);
            }
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """            while (absolute >= nextStepFrame) {
                fireStep(seqStep);

                const int i = seqStep;
                const int next = (i + 1) % kSteps;
                double delta = fps;
                if (next % 2 == 1) delta += swingOff;
                if (i % 2 == 1) delta -= swingOff;
                nextStepFrame += delta;
                seqStep = next;
            }
""",
        """            while (absolute >= nextStepFrame) {
                fireStep(seqStep);

                const int i = seqStep;
                const int next = (i + 1) % kSteps;
                double delta = fps;
                if (next % 2 == 1) delta += swingOff;
                if (i % 2 == 1) delta -= swingOff;
                nextStepFrame += delta;
                seqStep = next;

                if (next == 0) {
                    songBar++;
                    const int sl = songLen.load(std::memory_order_relaxed);
                    if (songOn.load(std::memory_order_relaxed) && sl > 0) {
                        playBank = songBanks[songBar % sl].load(std::memory_order_relaxed);
                    } else {
                        playBank = currentBank.load(std::memory_order_relaxed);
                    }
                }
            }
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """            if (midiStartReq.exchange(false, std::memory_order_relaxed)) {
                seqStep = 0;
                tickAccum = 0;
                seqPlaying.store(true, std::memory_order_relaxed);
            }
""",
        """            if (midiStartReq.exchange(false, std::memory_order_relaxed)) {
                seqStep = 0;
                tickAccum = 0;
                songBar = 0;
                playBank = (songOn.load(std::memory_order_relaxed) && songLen.load(std::memory_order_relaxed) > 0)
                        ? songBanks[0].load(std::memory_order_relaxed)
                        : currentBank.load(std::memory_order_relaxed);
                seqPlaying.store(true, std::memory_order_relaxed);
            }
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """            while (tickAccum >= 6) {
                tickAccum -= 6;
                fireStep(seqStep);
                seqStep = (seqStep + 1) % kSteps;
            }
""",
        """            while (tickAccum >= 6) {
                tickAccum -= 6;
                fireStep(seqStep);
                seqStep = (seqStep + 1) % kSteps;

                if (seqStep == 0) {
                    songBar++;
                    const int sl = songLen.load(std::memory_order_relaxed);
                    if (songOn.load(std::memory_order_relaxed) && sl > 0) {
                        playBank = songBanks[songBar % sl].load(std::memory_order_relaxed);
                    } else {
                        playBank = currentBank.load(std::memory_order_relaxed);
                    }
                }
            }
"""
    ),
    (
        "app/src/main/cpp/native-lib.cpp",
        """    const bool ok = engine->stopCapture(std::string(s));
    env->ReleaseStringUTFChars(path, s);
    return ok ? JNI_TRUE : JNI_FALSE;
}
""",
        """    const bool ok = engine->stopCapture(std::string(s));
    env->ReleaseStringUTFChars(path, s);
    return ok ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetSongOn(JNIEnv*, jobject, jboolean enabled) {
    if (engine != nullptr) {
        engine->setSongOn(enabled == JNI_TRUE);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetSongLen(JNIEnv*, jobject, jint len) {
    if (engine != nullptr) {
        engine->setSongLen(static_cast<int>(len));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetSongBank(JNIEnv*, jobject, jint slot, jint bank) {
    if (engine != nullptr) {
        engine->setSongBank(static_cast<int>(slot), static_cast<int>(bank));
    }
}
"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private external fun nativeStartCapture()
    private external fun nativeStopCapture(path: String): Boolean
""",
        """    private external fun nativeStartCapture()
    private external fun nativeStopCapture(path: String): Boolean
    private external fun nativeSetSongOn(enabled: Boolean)
    private external fun nativeSetSongLen(len: Int)
    private external fun nativeSetSongBank(slot: Int, bank: Int)
"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var exportBars by mutableStateOf(2)""",
        """    private var songSlots by mutableStateOf(List(8) { 0 })
    private var songOn by mutableStateOf(false)
    private var exportBars by mutableStateOf(2)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            root.put("banks", banksArr)

            File(filesDir, "state.json").writeText(root.toString())""",
        """            root.put("banks", banksArr)
            root.put("song", JSONArray(songSlots))
            root.put("songon", songOn)

            File(filesDir, "state.json").writeText(root.toString())"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            patternBanks = newPatterns""",
        """            root.optJSONArray("song")?.let { sg ->
                songSlots = (0 until 8).map { sg.optInt(it, 0) }
            }
            songOn = root.optBoolean("songon", false)

            patternBanks = newPatterns"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        nativeSetBank(bank)
    }

    private fun restoreSamples() {""",
        """        nativeSetSongOn(songOn)
        nativeSetSongLen(8)
        for (i in 0 until 8) {
            nativeSetSongBank(i, songSlots[i])
        }

        nativeSetBank(bank)
    }

    private fun restoreSamples() {"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                        exportBars = exportBars,""",
        """                        songSlots = songSlots,
                        songOn = songOn,
                        onSongOnToggle = {
                            songOn = !songOn
                            nativeSetSongOn(songOn)
                        },
                        onSongSlotCycle = { i ->
                            val v = (songSlots[i] + 1) % 4
                            songSlots = songSlots.toMutableList().also { it[i] = v }
                            nativeSetSongBank(i, v)
                        },
                        exportBars = exportBars,"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    exportBars: Int,
    onExportBarsCycle: () -> Unit,""",
        """    songSlots: List<Int>,
    songOn: Boolean,
    onSongOnToggle: () -> Unit,
    onSongSlotCycle: (Int) -> Unit,
    exportBars: Int,
    onExportBarsCycle: () -> Unit,"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            SmallButton("LIB", view == 4) { onViewChange(4) }
        }""",
        """            SmallButton("LIB", view == 4) { onViewChange(4) }
            SmallButton("SONG", view == 5) { onViewChange(5) }
        }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            else -> {
                Text(
                    text = "Hold = play. Load samples in LIB. Bank: ${'A' + bank}",""",
        """            5 -> SongView(
                songSlots = songSlots,
                songOn = songOn,
                onSongOnToggle = onSongOnToggle,
                onSongSlotCycle = onSongSlotCycle
            )

            else -> {
                Text(
                    text = "Hold = play. Load samples in LIB. Bank: ${'A' + bank}","""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        Text(
            text = if (hasSample) "WAV ${index + 1}" else "PAD ${index + 1}",
            color = Color.Black,
            style = MaterialTheme.typography.titleMedium
        )
    }
}""",
        """        Text(
            text = if (hasSample) "WAV ${index + 1}" else "PAD ${index + 1}",
            color = Color.Black,
            style = MaterialTheme.typography.titleMedium
        )
    }
}

@Composable
fun SongView(
    songSlots: List<Int>,
    songOn: Boolean,
    onSongOnToggle: () -> Unit,
    onSongSlotCycle: (Int) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onSongOnToggle) {
                Text(if (songOn) "SONG ON" else "SONG OFF")
            }
            Text(
                text = "Each slot = 1 bar. Tap = change bank",
                color = Color(0xFF888888),
                style = MaterialTheme.typography.bodySmall
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (i in 0 until 4) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(44.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF262636))
                        .clickable { onSongSlotCycle(i) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${'A' + songSlots[i]}",
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium
                    )
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (i in 4 until 8) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(44.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF262636))
                        .clickable { onSongSlotCycle(i) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${'A' + songSlots[i]}",
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium
                    )
                }
            }
        }
    }
}"""
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
