import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))

c("""            rollEndAt[p] = step + (len > 0 ? len : 1);""", """            rollEndAt[p] = step + ((len + 1) / 2);""")

a("""                        onNoteLenCycle = {
                            noteLen = when (noteLen) {
                                1 -> 2
                                2 -> 4
                                4 -> 8
                                8 -> 16
                                else -> 1
                            }
                        },""", """                        onNoteLenCycle = {
                            noteLen = when (noteLen) {
                                2 -> 4
                                4 -> 8
                                8 -> 16
                                16 -> 32
                                else -> 2
                            }
                        },""")

a("""    var colorEl by remember { mutableStateOf(-1) }""", """    var colorEl by remember { mutableStateOf(-1) }
    var snapRoll by remember { mutableStateOf(true) }""")

a("""                KBtn(
                    "LEN $noteLen", false, onNoteLenCycle,
                    Modifier.height(36.dp)
                )
                Text(
                    "Tap key = hear. Tap cell = note. Tap note = delete",
                    color = Color(0xFF9FB8C1), fontSize = 9.sp
                )""", """                KBtn(
                    "LEN " + (if (noteLen % 2 == 0) "${noteLen / 2}" else "${noteLen / 2f}"),
                    false, onNoteLenCycle,
                    Modifier.height(36.dp)
                )
                KBtn("SNAP", snapRoll, { snapRoll = !snapRoll }, Modifier.height(36.dp))
                Text(
                    "Tap key = hear. Tap cell = note. Tap note = delete",
                    color = Color(0xFF9FB8C1), fontSize = 9.sp
                )""")

a("""                for (s0 in 0 until 16) {
                    if ((row[s0] and (1 shl enc)) != 0) {
                        val L = rowLen[s0]
                        for (s in s0 until minOf(16, s0 + L)) {
                            if (cover[s] == -1) cover[s] = s0
                        }
                    }
                }""", """                for (s0 in 0 until 16) {
                    if ((row[s0] and (1 shl enc)) != 0) {
                        val L = rowLen[s0]
                        for (s in s0 until minOf(16, s0 + (L + 1) / 2)) {
                            if (cover[s] == -1) cover[s] = s0
                        }
                    }
                }""")

a("""                        val isEnd = isNote && start + rowLen[start] - 1 == step""", """                        val isEnd = isNote && start + (rowLen[start] + 1) / 2 - 1 == step""")

a("""                                    } else if (isEnd) {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            buf += drag.x / size.width.toFloat()
                                            val whole = Math.round(buf).toInt()
                                            if (whole != 0) {
                                                onResizeDelta(selectedPad, start, whole)
                                                buf -= whole.toFloat()
                                            }
                                        }
                                    } else {""", """                                    } else if (isEnd) {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            val per = if (snapRoll) 1f else 2f
                                            buf += drag.x / size.width.toFloat() * per
                                            val whole = Math.round(buf).toInt()
                                            if (whole != 0) {
                                                onResizeDelta(selectedPad, start, whole)
                                                buf -= whole.toFloat()
                                            }
                                        }
                                    } else {""")

a("""            rollLenBanks = newRollLens
            velBanks = newVels""", """            if (!root.has("lenscale")) {
                for (b2 in 0 until 4) {
                    newRollLens[b2] = newRollLens[b2].map { row -> row.map { it * 2 } }
                }
            }
            rollLenBanks = newRollLens
            velBanks = newVels""")

a("""            val thArr = JSONArray()""", """            root.put("lenscale", 2)

            val thArr = JSONArray()""")

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
