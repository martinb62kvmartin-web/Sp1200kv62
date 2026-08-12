import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def h(old, new):
    P.append(("app/src/main/cpp/audio_engine.h", old, new))

h("""    void triggerVoice(int padIndex, double semiAdd, double vel);
    void setRollVel(int padIndex, int step, int vel);""", """    void triggerVoice(int padIndex, double semiAdd, double vel);""")

h("""    void setRoll(int padIndex, int step, int value, int len);""", """    void setRoll(int padIndex, int step, int value, int len);
    void setRollVel(int padIndex, int step, int vel);""")

a("""                vels = velBanks[bank],
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
            )""", """                vels = vels,
                onVel = onVel,
                playhead = playhead,
                playing = playing
            )""")

a("""    onToggleStep: (Int, Int) -> Unit,
    mutes: List<Boolean>,""", """    onToggleStep: (Int, Int) -> Unit,
    vels: List<List<Int>>,
    onVel: (Int, Int, Float) -> Unit,
    onResizeDelta: (Int, Int, Int) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    mutes: List<Boolean>,""")

a("""                        onToggleStep = { pad, step ->""", """                        onVel = { pad, st, d ->
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
                        onResizeDelta = { pad, st, d ->
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
                        onDeleteRoll = { pad, st ->
                            rollBanks = rollBanks.set2(
                                bank, pad,
                                rollBanks[bank][pad].toMutableList().also { it[st] = 0 }
                            )
                            rollLenBanks = rollLenBanks.set2(
                                bank, pad,
                                rollLenBanks[bank][pad].toMutableList().also { it[st] = 0 }
                            )
                            nativeSetRoll(pad, st, 0, 1)
                        },
                        onToggleStep = { pad, step ->""")

a("""            3 -> RollView(
                selectedPad = selectedPad,
                onSelectPad = onSelectPad,
                loadedPads = loadedPads,
                roll = roll,
                rollLens = rollLens,
                noteLen = noteLen,
                onNoteLenCycle = onNoteLenCycle,
                onToggleRollCell = onToggleRollCell,
                onAudition = onAudition,
                playhead = playhead,
                playing = playing
            )""", """            3 -> RollView(
                selectedPad = selectedPad,
                onSelectPad = onSelectPad,
                loadedPads = loadedPads,
                roll = roll,
                rollLens = rollLens,
                noteLen = noteLen,
                onNoteLenCycle = onNoteLenCycle,
                onToggleRollCell = onToggleRollCell,
                onResizeDelta = onResizeDelta,
                onVel = onVel,
                onDeleteRoll = onDeleteRoll,
                onAudition = onAudition,
                vels = velBanks[bank],
                playhead = playhead,
                playing = playing
            )""")

a("""    onToggleRollCell: (Int, Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> C_CYAN
                    loadedPads.contains(pad) -> C_PINK.copy(alpha = 0.75f)
                    else -> C_DARK
                }""", """    onToggleRollCell: (Int, Int, Int) -> Unit,
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
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> C_CYAN
                    loadedPads.contains(pad) -> C_PINK.copy(alpha = 0.75f)
                    else -> C_DARK
                }""")

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
