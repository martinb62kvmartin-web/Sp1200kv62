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

h("""    void triggerVoice(int padIndex, double semiAdd);""", """    void triggerVoice(int padIndex, double semiAdd, double vel);
    void setRollVel(int padIndex, int step, int vel);""")

h("""        std::atomic<double> nextPitchAdd{0.0};""", """        std::atomic<double> nextPitchAdd{0.0};
        std::atomic<double> nextVel{1.0};""")

h("""    std::array<std::array<std::array<std::atomic<int>, kSteps>, kNumPads>, kBanks> rollLen{};""", """    std::array<std::array<std::array<std::atomic<int>, kSteps>, kNumPads>, kBanks> rollLen{};
    std::array<std::array<std::array<std::atomic<int>, kSteps>, kNumPads>, kBanks> rollVel{};""")

c("""    for (auto& h : padHits) h.store(0);""", """    for (auto& row : rollVel) for (auto& r : row) for (auto& v : r) v.store(100);
    for (auto& h : padHits) h.store(0);""")

c("""void AudioEngine::triggerVoice(int padIndex, double semiAdd) {""", """void AudioEngine::setRollVel(int padIndex, int step, int vel) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    if (step < 0 || step >= kSteps) return;
    if (vel < 10) vel = 10;
    if (vel > 150) vel = 150;
    const int b = currentBank.load(std::memory_order_relaxed);
    rollVel[b][padIndex][step].store(vel, std::memory_order_relaxed);
}

void AudioEngine::triggerVoice(int padIndex, double semiAdd, double vel) {""")

c("""    voice.nextPitchAdd.store(semiAdd, std::memory_order_relaxed);
    voice.gateClosed.store(false, std::memory_order_relaxed);
    voice.type.store(padIndex, std::memory_order_relaxed);""", """    voice.nextPitchAdd.store(semiAdd, std::memory_order_relaxed);
    voice.nextVel.store(vel, std::memory_order_relaxed);
    voice.gateClosed.store(false, std::memory_order_relaxed);
    voice.type.store(padIndex, std::memory_order_relaxed);""")

c("""                v.amp = 1.0;""", """                v.amp = v.nextVel.load(std::memory_order_relaxed);""")

c("""        const int m = seqMask[b][p].load(std::memory_order_relaxed);
        if ((m & (1 << step)) != 0) {
            triggerVoice(p, 0.0);
        }""", """        const int m = seqMask[b][p].load(std::memory_order_relaxed);
        if ((m & (1 << step)) != 0) {
            triggerVoice(p, 0.0, rollVel[b][p][step].load(std::memory_order_relaxed) / 100.0);
        }""")

c("""            triggerVoice(p, static_cast<double>(rp - 13));""", """            triggerVoice(p, static_cast<double>(rp - 13), rollVel[b][p][step].load(std::memory_order_relaxed) / 100.0);""")

c("""    triggerVoice(padIndex, 0.0);
}""", """    triggerVoice(padIndex, 0.0, 1.0);
}""")

j("""JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetRoll(JNIEnv*, jobject, jint padIndex, jint step, jint value, jint len) {""", """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetRollVel(JNIEnv*, jobject, jint padIndex, jint step, jint vel) {
    if (engine != nullptr) {
        engine->setRollVel(padIndex, static_cast<int>(step), static_cast<int>(vel));
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetRoll(JNIEnv*, jobject, jint padIndex, jint step, jint value, jint len) {""")

a("""    private external fun nativeSetRoll(padIndex: Int, step: Int, value: Int, len: Int)""", """    private external fun nativeSetRoll(padIndex: Int, step: Int, value: Int, len: Int)
    private external fun nativeSetRollVel(padIndex: Int, step: Int, vel: Int)""")

a("""    private var rollLenBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })""", """    private var rollLenBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })
    private var velBanks by mutableStateOf(List(4) { List(16) { List(16) { 100 } } })""")

a("""                bo.put("roll", rollArr)
                bo.put("rolllen", rollLenArr)""", """                bo.put("roll", rollArr)
                bo.put("rolllen", rollLenArr)

                val velArr = JSONArray()
                for (p in 0 until 16) {
                    velArr.put(JSONArray(velBanks[b][p]))
                }
                bo.put("vel", velArr)""")

a("""            val newRollLens = rollLenBanks.toMutableList()""", """            val newRollLens = rollLenBanks.toMutableList()
            val newVels = velBanks.toMutableList()""")

a("""                bo.optJSONArray("rolllen")?.let { ra ->
                    val rows = rollLenBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ra.length())) {
                        val st = ra.optJSONArray(p) ?: continue
                        rows[p] = (0 until 16).map { st.optInt(it, 0) }
                    }
                    newRollLens[b] = rows
                }""", """                bo.optJSONArray("rolllen")?.let { ra ->
                    val rows = rollLenBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ra.length())) {
                        val st = ra.optJSONArray(p) ?: continue
                        rows[p] = (0 until 16).map { st.optInt(it, 0) }
                    }
                    newRollLens[b] = rows
                }

                bo.optJSONArray("vel")?.let { va2 ->
                    val rows = velBanks[b].toMutableList()
                    for (p in 0 until minOf(16, va2.length())) {
                        val st = va2.optJSONArray(p) ?: continue
                        rows[p] = (0 until 16).map { st.optInt(it, 100) }
                    }
                    newVels[b] = rows
                }""")

a("""            rollLenBanks = newRollLens""", """            rollLenBanks = newRollLens
            velBanks = newVels""")

a("""                for (st in 0 until 16) {
                    nativeSetRoll(p, st, rollBanks[b][p][st], rollLenBanks[b][p][st])
                }""", """                for (st in 0 until 16) {
                    nativeSetRoll(p, st, rollBanks[b][p][st], rollLenBanks[b][p][st])
                    nativeSetRollVel(p, st, velBanks[b][p][st])
                }""")

a("""                        onCycleRollLen = { pad, st ->
                            val cur = rollLenBanks[bank][pad][st]
                            val next = when (cur) {
                                1 -> 2
                                2 -> 4
                                4 -> 8
                                8 -> 16
                                else -> 1
                            }
                            rollLenBanks = rollLenBanks.set2(
                                bank, pad,
                                rollLenBanks[bank][pad].toMutableList().also { it[st] = next }
                            )
                            nativeSetRoll(pad, st, rollBanks[bank][pad][st], next)
                        },""", """                        onResizeDelta = { pad, st, d ->
                            val cur = rollLenBanks[bank][pad][st]
                            val next = (cur + d).coerceIn(1, 16 - st)
                            if (next != cur) {
                                rollLenBanks = rollLenBanks.set2(
                                    bank, pad,
                                    rollLenBanks[bank][pad].toMutableList().also { it[st] = next }
                                )
                                nativeSetRoll(pad, st, rollBanks[bank][pad][st], next)
                            }
                        },
                        onVel = { pad, st, d ->
                            val cur = velBanks[bank][pad][st]
                            val next = (cur + d.toInt()).coerceIn(10, 150)
                            if (next != cur) {
                                velBanks = velBanks.set2(
                                    bank, pad,
                                    velBanks[bank][pad].toMutableList().also { it[st] = next }
                                )
                                nativeSetRollVel(pad, st, next)
                            }
                        },""")

a("""    onToggleRollCell: (Int, Int, Int) -> Unit,
    onCycleRollLen: (Int, Int) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    playhead: Int,
    flashes: List<Boolean>,""", """    onToggleRollCell: (Int, Int, Int) -> Unit,
    onResizeDelta: (Int, Int, Int) -> Unit,
    onVel: (Int, Int, Float) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    playhead: Int,
    flashes: List<Boolean>,""")

a("""                onToggleRollCell = onToggleRollCell,
                onCycleRollLen = onCycleRollLen,
                onDeleteRoll = onDeleteRoll,
                onAudition = onAudition,
                playhead = playhead,
                playing = playing
            )""", """                onToggleRollCell = onToggleRollCell,
                onResizeDelta = onResizeDelta,
                onVel = onVel,
                onDeleteRoll = onDeleteRoll,
                onAudition = onAudition,
                vels = velBanks[bank],
                playhead = playhead,
                playing = playing
            )""")

a("""    onToggleRollCell: (Int, Int, Int) -> Unit,
    onCycleRollLen: (Int, Int) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {""", """    onToggleRollCell: (Int, Int, Int) -> Unit,
    onResizeDelta: (Int, Int, Int) -> Unit,
    onVel: (Int, Int, Float) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    vels: List<List<Int>>,
    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {""")

a("""                        val bg = when {
                            isNote -> C_PINK
                            playing && step == playhead -> Color(0x33FFFFFF)
                            step % 4 == 0 -> Color(0x14FFFFFF)
                            else -> Color(0x00000000)
                        }
                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .clip(RoundedCornerShape(4.dp))
                                .background(bg)
                                .pointerInput(cover[step], isStart, isNote) {
                                    detectTapGestures(
                                        onTap = {
                                            if (isNote) {
                                                onCycleRollLen(selectedPad, cover[step])
                                            } else {
                                                onToggleRollCell(selectedPad, step, enc)
                                            }
                                        },
                                        onLongPress = {
                                            if (isNote) {
                                                onDeleteRoll(selectedPad, cover[step])
                                            }
                                        }
                                    )
                                }
                        ) {""", """                        val start = cover[step]
                        val isEnd = isNote && start + rowLen[start] - 1 == step
                        val vel = if (isNote) vels[selectedPad][start] else 100
                        val bg = when {
                            playing && step == playhead -> Color(0x33FFFFFF)
                            step % 4 == 0 -> Color(0x14FFFFFF)
                            else -> Color(0x00000000)
                        }
                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .clip(RoundedCornerShape(4.dp))
                                .background(
                                    if (isNote) C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)) else bg
                                )
                                .pointerInput(start, isNote, isEnd, rowLen.getOrElse(start) { 0 }) {
                                    if (!isNote) {
                                        detectTapGestures(
                                            onTap = { onToggleRollCell(selectedPad, step, enc) }
                                        )
                                    } else {
                                        forEachGesture {
                                            awaitPointerEventScope {
                                                val down = awaitFirstDown()
                                                down.consume()
                                                var moved = false
                                                var accX = 0f
                                                var accY = 0f
                                                var buf = 0f
                                                val t0 = System.currentTimeMillis()
                                                while (true) {
                                                    val ev = awaitPointerEvent()
                                                    val ch = ev.changes.firstOrNull() ?: break
                                                    if (!ch.pressed) break
                                                    val dx = ch.positionChange().x
                                                    val dy = ch.positionChange().y
                                                    accX += dx
                                                    accY += dy
                                                    if (kotlin.math.abs(accX) > 12 || kotlin.math.abs(accY) > 12) moved = true
                                                    ch.consume()
                                                    if (moved) {
                                                        if (isEnd && kotlin.math.abs(accX) >= kotlin.math.abs(accY)) {
                                                            buf += dx / size.width.toFloat()
                                                            val whole = Math.round(buf).toInt()
                                                            if (whole != 0) {
                                                                onResizeDelta(selectedPad, start, whole)
                                                                buf -= whole.toFloat()
                                                            }
                                                        } else {
                                                            onVel(selectedPad, start, -dy / 2f)
                                                        }
                                                    }
                                                }
                                                val dt = System.currentTimeMillis() - t0
                                                if (!moved) {
                                                    if (dt > 400) {
                                                        onDeleteRoll(selectedPad, start)
                                                    } else {
                                                        onAudition(selectedPad, pitchOff)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                        ) {""")

a("""fun SequencerGrid(
    pattern: List<Int>,
    onToggleStep: (Int, Int) -> Unit,
    mutes: List<Boolean>,
    onMuteToggle: (Int) -> Unit,
    solos: List<Boolean>,
    onSoloToggle: (Int) -> Unit,
    playhead: Int,
    playing: Boolean
) {""", """fun SequencerGrid(
    pattern: List<Int>,
    onToggleStep: (Int, Int) -> Unit,
    mutes: List<Boolean>,
    onMuteToggle: (Int) -> Unit,
    solos: List<Boolean>,
    onSoloToggle: (Int) -> Unit,
    vels: List<List<Int>>,
    onVel: (Int, Int, Float) -> Unit,
    playhead: Int,
    playing: Boolean
) {""")

a("""                for (step in 0 until 16) {
                    val on = (pattern[pad] ushr step) and 1 == 1
                    val offColor = when {
                        playing && step == playhead -> Color(0xFF3A2F55)
                        step % 4 == 0 -> Color(0xFF2E2447)
                        else -> C_DARK
                    }
                    Box(
                        modifier = Modifier.weight(1f).height(24.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(if (on) C_PINK else offColor)
                            .clickable { onToggleStep(pad, step) }
                    )
                }""", """                for (step in 0 until 16) {
                    val on = (pattern[pad] ushr step) and 1 == 1
                    val vel = vels[pad][step]
                    val offColor = when {
                        playing && step == playhead -> Color(0xFF3A2F55)
                        step % 4 == 0 -> Color(0xFF2E2447)
                        else -> C_DARK
                    }
                    Box(
                        modifier = Modifier.weight(1f).height(24.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(
                                if (on) C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)) else offColor
                            )
                            .pointerInput(on) {
                                if (!on) {
                                    detectTapGestures(onTap = { onToggleStep(pad, step) })
                                } else {
                                    detectDragGestures(
                                        onDragEnd = { }
                                    ) { change, drag ->
                                        change.consume()
                                        onVel(pad, step, -drag.y / 2f)
                                    }
                                }
                            }
                    )
                }""")

a("""            1 -> SequencerGrid(
                pattern = pattern,
                onToggleStep = onToggleStep,
                mutes = mutes,
                onMuteToggle = onMuteToggle,
                solos = solos,
                onSoloToggle = onSoloToggle,
                playhead = playhead,
                playing = playing
            )""", """            1 -> SequencerGrid(
                pattern = pattern,
                onToggleStep = onToggleStep,
                mutes = mutes,
                onMuteToggle = onMuteToggle,
                solos = solos,
                onSoloToggle = onSoloToggle,
                vels = velBanks[bank],
                onVel = { pad, st, d ->
                    val cur = velBanks[bank][pad][st]
                    val next = (cur + d.toInt()).coerceIn(10, 150)
                    if (next != cur) {
                        velBanks = velBanks.set2(
                            bank, pad,
                            velBanks[bank][pad].toMutableList().also { it[st] = next }
                        )
                        nativeSetRollVel(pad, st, next)
                    }
                },
                playhead = playhead,
                playing = playing
            )""")

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
