import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def h(old, new):
    P.append(("app/src/main/cpp/audio_engine.h", old, new))
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))
def j(old, new):
    P.append(("app/src/main/cpp/native-lib.cpp", old, new))

a("""import androidx.compose.material3.Text""", """import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.KeyboardOptions""")

a("""    private external fun nativeSetPadReverse(padIndex: Int, enabled: Boolean)""", """    private external fun nativeSetPadReverse(padIndex: Int, enabled: Boolean)
    private external fun nativeSetPadStretch(padIndex: Int, steps: Int)""")

a("""    private var reverseBanks by mutableStateOf(List(4) { List(16) { false } })""", """    private var reverseBanks by mutableStateOf(List(4) { List(16) { false } })
    private var stretchBanks by mutableStateOf(List(4) { List(16) { 0 } })""")

a("""                val revArr = JSONArray()
                for (p in 0 until 16) {
                    revArr.put(reverseBanks[b][p])
                }
                bo.put("rev", revArr)""", """                val revArr = JSONArray()
                for (p in 0 until 16) {
                    revArr.put(reverseBanks[b][p])
                }
                bo.put("rev", revArr)

                val stArr = JSONArray()
                for (p in 0 until 16) {
                    stArr.put(stretchBanks[b][p])
                }
                bo.put("stretch", stArr)""")

a("""                bo.optJSONArray("rev")?.let { rv ->
                    newRev[b] = (0 until 16).map { rv.optBoolean(it, false) }
                }""", """                bo.optJSONArray("rev")?.let { rv ->
                    newRev[b] = (0 until 16).map { rv.optBoolean(it, false) }
                }

                bo.optJSONArray("stretch")?.let { sta ->
                    val rows = stretchBanks[b].toMutableList()
                    for (p in 0 until minOf(16, sta.length())) {
                        rows[p] = sta.optInt(p, 0)
                    }
                    newStretch[b] = rows
                }""")

a("""            val newRev = reverseBanks.toMutableList()""", """            val newRev = reverseBanks.toMutableList()
            val newStretch = stretchBanks.toMutableList()""")

a("""            reverseBanks = newRev""", """            reverseBanks = newRev
            stretchBanks = newStretch""")

a("""                nativeSetLoopOn(p, loopOnBanks[b][p])
                nativeSetPadReverse(p, reverseBanks[b][p])""", """                nativeSetLoopOn(p, loopOnBanks[b][p])
                nativeSetPadReverse(p, reverseBanks[b][p])
                nativeSetPadStretch(p, stretchBanks[b][p])""")

a("""            TabBtn("LIB", view == 4) { onViewChange(4) }
        }""", """            TabBtn("LIB", view == 4) { onViewChange(4) }
            TabBtn("SET", view == 7) { onViewChange(7) }
        }""")

a("""            TabBtn(
                when (midiMode) {
                    1 -> "MIDI M"
                    2 -> "MIDI S"
                    else -> "MIDI"
                },
                midiMode != 0
            ) { onMidiModeChange() }
            TabBtn("x$exportBars", false) { onExportBarsCycle() }
            TabBtn(if (exporting) "..." else "EXP", exporting) { onExport() }
            TabBtn(if (recording) "REC*" else "REC", recording) { onRecToggle() }""", """            TabBtn(if (recording) "REC*" else "REC", recording) { onRecToggle() }""")

a("""            else -> SampleView(""", """            7 -> SettingsView(
                midiMode = midiMode,
                onMidiModeChange = onMidiModeChange,
                exportBars = exportBars,
                onExportBarsCycle = onExportBarsCycle,
                exporting = exporting,
                onExport = onExport
            )

            else -> SampleView(""")

a("""                swing = swing,
                onSwingChange = onSwingChange,
                pollTick = pollTick,""", """                swing = swing,
                onSwingChange = onSwingChange,
                stretch = stretchBanks[bank][selectedPad],
                onStretch = { v ->
                    stretchBanks = stretchBanks.set2(bank, selectedPad, v)
                    nativeSetPadStretch(selectedPad, v)
                },
                pollTick = pollTick,""")

a("""    swing: Float,
    onSwingChange: (Float) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {""", """    swing: Float,
    onSwingChange: (Float) -> Unit,
    stretch: Int,
    onStretch: (Int) -> Unit
) {
    var showBpm by remember { mutableStateOf(false) }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {""")

a("""                    Text(
                        text = "${index + 1}",
                        color = Color.White,
                        fontSize = 9.sp,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(4.dp)
                    )
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("BPM ${bpm.toInt()}", color = Color.White, fontSize = 10.sp)
                Fader(bpm, 60f..180f, onBpmChange, Modifier.fillMaxWidth())
            }
            Column(modifier = Modifier.weight(1f)) {
                Text("SWING ${swing.toInt()}%", color = Color.White, fontSize = 10.sp)
                Fader(swing, 0f..50f, onSwingChange, Modifier.fillMaxWidth())
            }
        }
    }
}""", """                    Text(
                        text = "${index + 1}",
                        color = Color.White,
                        fontSize = 9.sp,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(4.dp)
                    )
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "BPM ${bpm.toInt()}  (2x tap)",
                    color = Color.White, fontSize = 10.sp,
                    modifier = Modifier.pointerInput(Unit) {
                        detectTapGestures(onDoubleTap = { showBpm = !showBpm })
                    }
                )
                Fader(bpm, 60f..180f, onBpmChange, Modifier.fillMaxWidth())
            }
            Column(modifier = Modifier.weight(1f)) {
                Text("SWING ${swing.toInt()}%", color = Color.White, fontSize = 10.sp)
                Fader(swing, 0f..50f, onSwingChange, Modifier.fillMaxWidth())
            }
        }

        if (showBpm) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                var txt by remember { mutableStateOf(bpm.toInt().toString()) }
                TextField(
                    value = txt,
                    onValueChange = { txt = it.filter { ch -> ch.isDigit() } },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.width(110.dp).height(48.dp)
                )
                KBtn("SET", false, {
                    val v = txt.toFloatOrNull()
                    if (v != null) onBpmChange(v.coerceIn(60f, 180f))
                    showBpm = false
                }, Modifier.width(70.dp).height(40.dp))
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            listOf(0 to "OFF", 16 to "1BAR", 32 to "2BAR", 64 to "4BAR", 4 to "1BEAT", 8 to "2BEAT").forEach { (v, label) ->
                KBtn(label, stretch == v, { onStretch(v) }, Modifier.weight(1f).height(32.dp))
            }
        }
    }
}""")

a("""@Composable
fun Fader(
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onValueChange: (Float) -> Unit,
    modifier: Modifier = Modifier
) {
    val span = range.endInclusive - range.start
    val frac = ((value - range.start) / span).coerceIn(0f, 1f)

    BoxWithConstraints(
        modifier = modifier
            .height(30.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(C_DARK)
            .pointerInput(value, range.start, range.endInclusive) {
                detectDragGestures { change, drag ->
                    change.consume()
                    val d = drag.x / size.width.toFloat() * span
                    onValueChange((value + d).coerceIn(range))
                }
            }
    ) {
        val w = constraints.maxWidth
        val x = (frac * (w - 20)).toInt()

        Box(
            modifier = Modifier
                .offset { IntOffset(x, 0) }
                .width(20.dp)
                .fillMaxHeight()
                .background(C_CYAN)
        )
    }
}""", """@Composable
fun Fader(
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onValueChange: (Float) -> Unit,
    modifier: Modifier = Modifier
) {
    val span = range.endInclusive - range.start
    val frac = ((value - range.start) / span).coerceIn(0f, 1f)
    val cur = rememberUpdatedState(value)
    val startVal = remember { mutableStateOf(0f) }
    val acc = remember { mutableStateOf(0f) }

    BoxWithConstraints(
        modifier = modifier
            .height(30.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(C_DARK)
            .pointerInput(range.start, range.endInclusive) {
                detectDragGestures(
                    onDragStart = {
                        startVal.value = cur.value
                        acc.value = 0f
                    }
                ) { change, drag ->
                    change.consume()
                    acc.value += drag.x / size.width.toFloat() * span
                    onValueChange((startVal.value + acc.value).coerceIn(range))
                }
            }
    ) {
        val w = constraints.maxWidth
        val x = (frac * (w - 20)).toInt()

        Box(
            modifier = Modifier
                .offset { IntOffset(x, 0) }
                .width(20.dp)
                .fillMaxHeight()
                .background(C_CYAN)
        )
    }
}""")

a("""                .pointerInput(value, range.start, range.endInclusive) {
                    detectDragGestures { change, drag ->
                        change.consume()
                        onValueChange((value - drag.y / 200f * span).coerceIn(range))
                    }
                },""", """                .pointerInput(range.start, range.endInclusive) {
                    val cur2 = rememberUpdatedState(value)
                    val sv = remember { mutableStateOf(0f) }
                    val ac = remember { mutableStateOf(0f) }
                    detectDragGestures(
                        onDragStart = {
                            sv.value = cur2.value
                            ac.value = 0f
                        }
                    ) { change, drag ->
                        change.consume()
                        ac.value -= drag.y / 200f * span
                        onValueChange((sv.value + ac.value).coerceIn(range))
                    }
                },""")

a("""                    Text(
                        name,
                        color = if (armedFile == name) Color.White else Color(0xFFD7E6EE),
                        fontSize = 10.sp,
                        modifier = Modifier.padding(horizontal = 12.dp)
                    )
                }
            }
        }
    }
}""", """                    Text(
                        name,
                        color = if (armedFile == name) Color.White else Color(0xFFD7E6EE),
                        fontSize = 10.sp,
                        modifier = Modifier.padding(horizontal = 12.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun SettingsView(
    midiMode: Int,
    onMidiModeChange: () -> Unit,
    exportBars: Int,
    onExportBarsCycle: () -> Unit,
    exporting: Boolean,
    onExport: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("SETTINGS", color = C_CYAN, fontWeight = FontWeight.Bold)
        KBtn(
            when (midiMode) {
                1 -> "MIDI: MASTER"
                2 -> "MIDI: SLAVE"
                else -> "MIDI: OFF"
            },
            midiMode != 0,
            onMidiModeChange,
            Modifier.fillMaxWidth().height(44.dp)
        )
        KBtn("EXPORT LENGTH: x$exportBars", false, onExportBarsCycle, Modifier.fillMaxWidth().height(44.dp))
        KBtn(if (exporting) "EXPORTING..." else "EXPORT BEAT", exporting, onExport, Modifier.fillMaxWidth().height(44.dp))
    }
}""")

h("""    std::array<std::array<std::atomic<bool>, kNumPads>, kBanks> padRev{};""", """    std::array<std::array<std::atomic<bool>, kNumPads>, kBanks> padRev{};
    std::array<std::array<std::atomic<int>, kNumPads>, kBanks> padStretch{};""")

h("""    void setPadReverse(int padIndex, bool enabled);""", """    void setPadReverse(int padIndex, bool enabled);
    void setPadStretch(int padIndex, int steps);""")

c("""void AudioEngine::setPadReverse(int padIndex, bool enabled) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    const int b = currentBank.load(std::memory_order_relaxed);
    padRev[b][padIndex].store(enabled, std::memory_order_relaxed);
}""", """void AudioEngine::setPadReverse(int padIndex, bool enabled) {
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
}""")

c("""                v.pitchAddSemi = v.nextPitchAdd.load(std::memory_order_relaxed);
                v.rate = std::pow(2.0,
                        (padPitch[b][type].load(std::memory_order_relaxed) + v.pitchAddSemi) / 12.0);""", """                v.pitchAddSemi = v.nextPitchAdd.load(std::memory_order_relaxed);
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
                }""")

j("""JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadReverse(JNIEnv*, jobject, jint padIndex, jboolean enabled) {
    if (engine != nullptr) {
        engine->setPadReverse(padIndex, enabled == JNI_TRUE);
    }
}""", """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadReverse(JNIEnv*, jobject, jint padIndex, jboolean enabled) {
    if (engine != nullptr) {
        engine->setPadReverse(padIndex, enabled == JNI_TRUE);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadStretch(JNIEnv*, jobject, jint padIndex, jint steps) {
    if (engine != nullptr) {
        engine->setPadStretch(padIndex, static_cast<int>(steps));
    }
}""")

def main():
    for path, old, new in P:
        if not os.path.exists(path):
            print("ERROR: missing file", path)
            sys.exit(1)
        with io.open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if old not in text:
            print("Skipped:", old[:60].replace("\n", " "))
            continue
        text = text.replace(old, new, 1)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("Patched:", old[:60].replace("\n", " "))

main()
