import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))

c("""        const int rp = rollPitch[b][p][step].load(std::memory_order_relaxed);
        if (rp != 0) {
            const int len = rollLen[b][p][step].load(std::memory_order_relaxed);
            triggerVoice(p, static_cast<double>(rp - 13), rollVel[b][p][step].load(std::memory_order_relaxed) / 100.0);
            rollEndAt[p] = step + (len > 0 ? len : 1);
        }""", """        const int maskNow = rollPitch[b][p][step].load(std::memory_order_relaxed);
        if (maskNow != 0) {
            const int len = rollLen[b][p][step].load(std::memory_order_relaxed);
            for (int e = 1; e <= 25; ++e) {
                if ((maskNow & (1 << e)) != 0) {
                    triggerVoice(p, static_cast<double>(e - 13), rollVel[b][p][step].load(std::memory_order_relaxed) / 100.0);
                }
            }
            rollEndAt[p] = step + (len > 0 ? len : 1);
        }""")

a("""                val cover = IntArray(16) { -1 }
                for (s0 in 0 until 16) {
                    if (row[s0] == enc) {
                        val L = rowLen[s0]
                        for (s in s0 until minOf(16, s0 + L)) {
                            if (cover[s] == -1) cover[s] = s0
                        }
                    }
                }""", """                val cover = IntArray(16) { -1 }
                for (s0 in 0 until 16) {
                    if ((row[s0] and (1 shl enc)) != 0) {
                        val L = rowLen[s0]
                        for (s in s0 until minOf(16, s0 + L)) {
                            if (cover[s] == -1) cover[s] = s0
                        }
                    }
                }""")

a("""                        Text(
                            if (pitchOff >= 0) "+$pitchOff" else "$pitchOff",
                            color = if (blackKey) Color.White else Color.Black, fontSize = 7.sp
                        )""", """                        Text(
                            if (pc == 0) "C${(60 + pitchOff) / 12 - 1}" else "",
                            color = if (blackKey) Color.White else Color.Black, fontSize = 7.sp
                        )""")

a("""                        onToggleRollCell = { pad, step, enc ->
                            val row = rollBanks[bank][pad]
                            val rowLen = rollLenBanks[bank][pad]

                            var coverStart = -1
                            if (row[step] == enc) {
                                coverStart = step
                            } else {
                                for (s0 in 0 until step) {
                                    if (row[s0] == enc && step < s0 + rowLen[s0]) {
                                        coverStart = s0
                                        break
                                    }
                                }
                            }

                            if (coverStart >= 0) {
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[coverStart] = 0 }
                                )
                                rollLenBanks = rollLenBanks.set2(
                                    bank, pad,
                                    rollLenBanks[bank][pad].toMutableList().also { it[coverStart] = 0 }
                                )
                                nativeSetRoll(pad, coverStart, 0, 1)
                            } else {
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[step] = enc }
                                )
                                rollLenBanks = rollLenBanks.set2(
                                    bank, pad,
                                    rollLenBanks[bank][pad].toMutableList().also { it[step] = noteLen }
                                )
                                nativeSetRoll(pad, step, enc, noteLen)
                            }
                        },""", """                        onToggleRollCell = { pad, step, enc ->
                            val cur = rollBanks[bank][pad][step]
                            val bit = 1 shl enc
                            if ((cur and bit) != 0) {
                                val nm = cur and bit.inv()
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[step] = nm }
                                )
                                if (nm == 0) {
                                    rollLenBanks = rollLenBanks.set2(
                                        bank, pad,
                                        rollLenBanks[bank][pad].toMutableList().also { it[step] = 0 }
                                    )
                                    nativeSetRoll(pad, step, 0, 1)
                                } else {
                                    nativeSetRoll(pad, step, nm, rollLenBanks[bank][pad][step])
                                }
                            } else {
                                val nm = cur or bit
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[step] = nm }
                                )
                                if (cur == 0) {
                                    rollLenBanks = rollLenBanks.set2(
                                        bank, pad,
                                        rollLenBanks[bank][pad].toMutableList().also { it[step] = noteLen }
                                    )
                                }
                                nativeSetRoll(pad, step, nm, if (cur == 0) noteLen else rollLenBanks[bank][pad][step])
                            }
                        },""")

a("""                                .pointerInput(start, isNote, isEnd, rowLen.getOrElse(start) { 0 }) {
                                    var buf = 0f
                                    if (!isNote) {
                                        detectTapGestures(onTap = { onToggleRollCell(selectedPad, step, enc) })
                                    } else if (isEnd) {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            buf += drag.x / size.width.toFloat()
                                            val whole = Math.round(buf).toInt()
                                            if (whole != 0) {
                                                onResizeDelta(selectedPad, start, whole)
                                                buf -= whole.toFloat()
                                            }
                                        }
                                    } else {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            onVel(selectedPad, start, -dySafe(drag.y))
                                        }
                                    }
                                }
                                .pointerInput(start, isNote) {
                                    if (isNote) {
                                        detectTapGestures(
                                            onTap = { onAudition(selectedPad, pitchOff) },
                                            onLongPress = { onDeleteRoll(selectedPad, start) }
                                        )
                                    }
                                }""", """                                .pointerInput(start, isNote, isEnd, rowLen.getOrElse(start) { 0 }) {
                                    var buf = 0f
                                    if (!isNote) {
                                        detectTapGestures(onTap = { onToggleRollCell(selectedPad, step, enc) })
                                    } else if (isEnd) {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            buf += drag.x / size.width.toFloat()
                                            val whole = Math.round(buf).toInt()
                                            if (whole != 0) {
                                                onResizeDelta(selectedPad, start, whole)
                                                buf -= whole.toFloat()
                                            }
                                        }
                                    } else {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            onVel(selectedPad, start, -dySafe(drag.y))
                                        }
                                    }
                                }
                                .pointerInput(start, isNote) {
                                    if (isNote) {
                                        detectTapGestures(
                                            onTap = { onToggleRollCell(selectedPad, start, enc) },
                                            onLongPress = { onDeleteRoll(selectedPad, start) }
                                        )
                                    }
                                }""")

a("""                                } else {
                                    detectDragGestures(
                                        onDragEnd = { }
                                    ) { change, drag ->
                                        change.consume()
                                        onVel(pad, step, -drag.y / 2f)
                                    }
                                }""", """                                } else {
                                    var moved = false
                                    detectDragGestures(
                                        onDragStart = { moved = false },
                                        onDragEnd = { if (!moved) onToggleStep(pad, step) }
                                    ) { change, drag ->
                                        change.consume()
                                        moved = true
                                        onVel(pad, step, -drag.y / 2f)
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
