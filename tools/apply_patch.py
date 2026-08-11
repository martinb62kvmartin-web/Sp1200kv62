import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""import androidx.compose.foundation.gestures.detectTapGestures""", """import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures""")

a("""    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    loopOn: Boolean,""", """    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    loopOn: Boolean,""")

a("""                        onLoopStart = { value ->
                            val end = loopEndBanks[bank][selectedPad]
                            val clamped = if (value > end - 1f) end - 1f else value
                            loopStartBanks = loopStartBanks.set2(bank, selectedPad, clamped)
                            nativeSetLoopPoints(selectedPad, clamped / 100f, end / 100f)
                        },""", """                        onLoopStart = { value ->
                            val end = loopEndBanks[bank][selectedPad]
                            val clamped = if (value > end - 1f) end - 1f else value
                            loopStartBanks = loopStartBanks.set2(bank, selectedPad, clamped)
                            nativeSetLoopPoints(selectedPad, clamped / 100f, end / 100f)
                        },
                        onLoopEnd = { value ->
                            val start = loopStartBanks[bank][selectedPad]
                            val clamped = if (value < start + 1f) start + 1f else value
                            loopEndBanks = loopEndBanks.set2(bank, selectedPad, clamped)
                            nativeSetLoopPoints(selectedPad, start / 100f, clamped / 100f)
                        },""")

a("""    loopOn: Boolean,
    onLoopToggle: () -> Unit,
    reverse: Boolean,""", """    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    loopOn: Boolean,
    onLoopToggle: () -> Unit,
    reverse: Boolean,""")

a("""                loopOn = loopOn,
                onLoopToggle = onLoopToggle,""", """                loopStart = loopStart,
                loopEnd = loopEnd,
                onLoopStart = onLoopStart,
                onLoopEnd = onLoopEnd,
                loopOn = loopOn,
                onLoopToggle = onLoopToggle,""")

a("""                Wave(
                    peaks = peaks,
                    bg = C_WAVEBG,
                    line = C_CYAN,
                    shake = if (flashes[selectedPad]) pollTick else 0,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(150.dp)
                )""", """                WaveEditor(
                    peaks = peaks,
                    loopStart = loopStart,
                    loopEnd = loopEnd,
                    onLoopStart = onLoopStart,
                    onLoopEnd = onLoopEnd,
                    shake = if (flashes[selectedPad]) pollTick else 0,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(150.dp)
                )""")

a("""        KBtn(if (exporting) "EXPORTING..." else "EXPORT BEAT", exporting, onExport, Modifier.fillMaxWidth().height(44.dp))
    }
}""", """        KBtn(if (exporting) "EXPORTING..." else "EXPORT BEAT", exporting, onExport, Modifier.fillMaxWidth().height(44.dp))
    }
}

@Composable
fun WaveEditor(
    peaks: FloatArray,
    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    shake: Int,
    modifier: Modifier = Modifier
) {
    var zoom by remember { mutableStateOf(1f) }
    var center by remember { mutableStateOf(0.5f) }

    val viewW = 1f / zoom
    var viewStart = center - viewW / 2f
    if (viewStart < 0f) viewStart = 0f
    if (viewStart > 1f - viewW) viewStart = 1f - viewW

    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()

        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .background(C_WAVEBG)
                .pointerInput(zoom) {
                    detectTransformGestures { _, pan, zoomChange, _ ->
                        zoom = (zoom * zoomChange).coerceIn(1f, 32f)
                        val vw = 1f / zoom
                        center = (center - pan.x / w * vw).coerceIn(vw / 2f, 1f - vw / 2f)
                    }
                }
        ) {
            val n = peaks.size
            val h = size.height
            val width = size.width
            if (n > 0) {
                val ls = ((loopStart / 100f - viewStart) / viewW).coerceIn(0f, 1f) * width
                val le = ((loopEnd / 100f - viewStart) / viewW).coerceIn(0f, 1f) * width
                drawRect(
                    color = Color(0x33FFFFFF),
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, h)
                )
                drawLine(Color(0x55FFFFFF), Offset(0f, h / 2), Offset(width, h / 2), 1f)
                val off = if (shake != 0) ((shake % 3) - 1) * h * 0.04f else 0f
                val bars = 160
                for (bIdx in 0 until bars) {
                    val fa = viewStart + viewW * bIdx / bars
                    val fb = viewStart + viewW * (bIdx + 1) / bars
                    var ia = (fa * n).toInt()
                    var ib = (fb * n).toInt()
                    if (ib <= ia) ib = ia + 1
                    if (ia < 0) ia = 0
                    if (ib > n) ib = n
                    var m = 0f
                    val stride = 1 + (ib - ia) / 32
                    var i = ia
                    while (i < ib) {
                        val a = kotlin.math.abs(peaks[i])
                        if (a > m) m = a
                        i += stride
                    }
                    val x = (bIdx + 0.5f) * width / bars
                    val p = m.coerceIn(0f, 1f) * (h / 2f) * 0.95f
                    drawLine(C_CYAN, Offset(x, h / 2 - p + off), Offset(x, h / 2 + p + off), width / bars)
                }
            }
        }

        Handle(xFrac = (loopStart / 100f - viewStart) / viewW, w = w, color = C_PINK) { d ->
            onLoopStart(loopStart + d * 100f)
        }
        Handle(xFrac = (loopEnd / 100f - viewStart) / viewW, w = w, color = C_CYAN) { d ->
            onLoopEnd(loopEnd + d * 100f)
        }

        Text(
            "x${zoom.toInt()}",
            color = Color.White,
            fontSize = 9.sp,
            modifier = Modifier.align(Alignment.TopEnd).padding(4.dp)
        )
    }
}

@Composable
fun Handle(
    xFrac: Float,
    w: Float,
    color: Color,
    onDelta: (Float) -> Unit
) {
    if (xFrac < 0f || xFrac > 1f) return
    Box(
        modifier = Modifier
            .offset { IntOffset((xFrac * w).toInt() - 7, 0) }
            .width(14.dp)
            .fillMaxHeight()
            .background(color.copy(alpha = 0.8f))
            .pointerInput(w) {
                detectDragGestures { change, drag ->
                    change.consume()
                    onDelta(drag.x / w)
                }
            }
    )
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
