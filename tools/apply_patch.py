import io

PATH = "app/src/main/java/com/example/sp1200/MainActivity.kt"
CPP = "app/src/main/cpp/audio_engine.cpp"

with io.open(CPP, "r", encoding="utf-8") as f:
    ct = f.read()
ct = ct.replace(
    "rollEndAt[p] = step + ((len + 1) / 2);",
    "rollEndAt[p] = step + ((len + 3) / 4);",
    1
)
with io.open(CPP, "w", encoding="utf-8") as f:
    f.write(ct)
print("Patched: engine len 1/64")

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1) clamp ресайза в 1/64
text = text.replace(
    "val next = (cur + d).coerceIn(1, 16 - st)",
    "val next = (cur + d).coerceIn(1, (16 - st) * 4)",
    1
)
print("Patched: resize clamp")

# 2) цикл LEN в 1/64 юнитах
text = text.replace(
    """                            noteLen = when (noteLen) {
                                2 -> 4
                                4 -> 8
                                8 -> 16
                                16 -> 32
                                else -> 2
                            }""",
    """                            noteLen = when (noteLen) {
                                4 -> 8
                                8 -> 16
                                16 -> 32
                                32 -> 64
                                else -> 4
                            }""",
    1
)
print("Patched: LEN cycle")

# 3) snapSel вместо snapRoll + кнопка SNAP с меню
text = text.replace(
    "var snapRoll by remember { mutableStateOf(true) }",
    "var snapSel by remember { mutableStateOf(4) }",
    1
)
text = text.replace(
    """                KBtn(
                    "LEN " + (if (noteLen % 2 == 0) "${noteLen / 2}" else "${noteLen / 2f}"),
                    false, onNoteLenCycle,
                    Modifier.height(36.dp)
                )
                KBtn("SNAP", snapRoll, { snapRoll = !snapRoll }, Modifier.height(36.dp))""",
    """                KBtn(
                    "LEN " + fmtSteps(noteLen),
                    false, onNoteLenCycle,
                    Modifier.height(36.dp)
                )
                KBtn(
                    "SNAP: " + when (snapSel) {
                        16 -> "1/4"
                        8 -> "1/8"
                        4 -> "1/16"
                        2 -> "1/32"
                        1 -> "1/64"
                        else -> "FREE"
                    },
                    false,
                    {
                        snapSel = when (snapSel) {
                            16 -> 8
                            8 -> 4
                            4 -> 2
                            2 -> 1
                            1 -> 0
                            else -> 16
                        }
                    },
                    Modifier.height(36.dp)
                )""",
    1
)
print("Patched: SNAP selector")

# 4) хелпер + fmtSteps перед RollView
text = text.replace(
    "@Composable\nfun RollView(",
    """fun fmtSteps(u: Int): String {
    val st = u / 4f
    return if (st == st.toInt().toFloat()) "${st.toInt()}" else "$st"
}

fun coverStartOf(row: List<Int>, rowLen: List<Int>, step: Int, enc: Int): Int {
    if ((row[step] and (1 shl enc)) != 0) return step
    for (s0 in 0 until step) {
        if ((row[s0] and (1 shl enc)) != 0) {
            val cells = (rowLen[s0] + 3) / 4
            if (step < s0 + cells) return s0
        }
    }
    return -1
}

@Composable
fun RollView(""",
    1
)
print("Patched: helpers")

# 5) перезапись rows: сплошные ноты + жесты
s = text.find("items(25) { r ->")
e = text.find("\n@Composable\nfun ", s + 10)
if s >= 0 and e >= 0:
    new_items = """items(25) { r ->
                val enc = r
                val pitchOff = 12 - r
                val pc = ((60 + pitchOff) % 12 + 12) % 12
                val blackKey = pc in listOf(1, 3, 6, 8, 10)
                val row = roll[selectedPad]
                val rowLen = rollLens[selectedPad]
                val velRow = vels[selectedPad]
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(0.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.width(26.dp).height(18.dp)
                            .clip(RoundedCornerShape(3.dp))
                            .background(if (blackKey) Color(0xFF171021) else Color(0xFFE8F4F8))
                            .clickable { onAudition(selectedPad, pitchOff) },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            if (pc == 0) "C${(60 + pitchOff) / 12 - 1}" else "",
                            color = if (blackKey) Color.White else Color.Black, fontSize = 7.sp
                        )
                    }
                    BoxWithConstraints(modifier = Modifier.weight(1f).height(18.dp)) {
                        val w = constraints.maxWidth.toFloat()
                        val cellW = w / 16f
                        Canvas(
                            modifier = Modifier
                                .fillMaxSize()
                                .pointerInput(row, rowLen, snapSel) {
                                    detectTapGestures(
                                        onTap = { pos ->
                                            val stp = (pos.x / cellW).toInt().coerceIn(0, 15)
                                            val st = coverStartOf(row, rowLen, stp, enc)
                                            onToggleRollCell(selectedPad, if (st >= 0) st else stp, enc)
                                        },
                                        onLongPress = { pos ->
                                            val stp = (pos.x / cellW).toInt().coerceIn(0, 15)
                                            val st = coverStartOf(row, rowLen, stp, enc)
                                            if (st >= 0) onDeleteRoll(selectedPad, st)
                                        }
                                    )
                                }
                                .pointerInput(row, rowLen, snapSel) {
                                    var buf = 0f
                                    var last = 0
                                    detectDragGestures { change, drag ->
                                        change.consume()
                                        val stp = (change.position.x / cellW).toInt().coerceIn(0, 15)
                                        val st = coverStartOf(row, rowLen, stp, enc)
                                        if (st >= 0) {
                                            val lenF = rowLen[st] / 4f
                                            val x1 = (st + lenF) * cellW
                                            if (kotlin.math.abs(change.position.x - x1) < 28f || kotlin.math.abs(drag.x) >= kotlin.math.abs(drag.y)) {
                                                buf += drag.x / cellW * 4f
                                                val per = if (snapSel > 0) snapSel.toFloat() else 1f
                                                val snapped = (Math.round(buf / per) * per).toInt()
                                                val delta = snapped - last
                                                if (delta != 0) {
                                                    onResizeDelta(selectedPad, st, delta)
                                                    last = snapped
                                                }
                                            } else {
                                                onVel(selectedPad, st, -drag.y / 2f)
                                            }
                                        }
                                    }
                                }
                        ) {
                            for (s2 in 0 until 16) {
                                val cc = when {
                                    playing && s2 == playhead -> Color(0x44FFFFFF)
                                    s2 % 4 == 0 -> Color(0xFF24303B)
                                    r % 2 == 0 -> Color(0xFF1B232C)
                                    else -> Color(0xFF161D25)
                                }
                            drawRect(cc, Offset(s2 * cellW + 0.5f, 0f), Size(cellW - 1f, size.height))
                            }
                            for (s0 in 0 until 16) {
                                if ((row[s0] and (1 shl enc)) != 0) {
                                    val lenF = rowLen[s0] / 4f
                                    val x0 = s0 * cellW
                                    val x1 = (s0 + lenF) * cellW
                                    val vel = velRow[s0]
                                    drawRoundRect(
                                        color = C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)),
                                        topLeft = Offset(x0, 1f),
                                        size = Size((x1 - x0).coerceAtLeast(2f), size.height - 2f),
                                        cornerRadius = CornerRadius(4f)
                                    )
                                    drawRect(Color.White, Offset(x0, 1f), Size(2f, size.height - 2f))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
"""
    text = text[:s] + new_items + text[e:]
    print("Patched: roll rows rewritten")

# 6) миграция lenscale 2 -> 4
text = text.replace(
    """            if (!root.has("lenscale")) {
                for (b2 in 0 until 4) {
                    newRollLens[b2] = newRollLens[b2].map { row -> row.map { it * 2 } }
                }
            }""",
    """            val lsOld = root.optInt("lenscale", 1)
            if (lsOld < 4) {
                val mult = 4 / lsOld
                for (b2 in 0 until 4) {
                    newRollLens[b2] = newRollLens[b2].map { row -> row.map { it * mult } }
                }
            }""",
    1
)
text = text.replace(
    """            root.put("lenscale", 2)""",
    """            root.put("lenscale", 4)""",
    1
)
print("Patched: lenscale migration")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Done")
