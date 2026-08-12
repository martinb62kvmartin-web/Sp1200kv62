import io

PATH = "app/src/main/java/com/example/sp1200/MainActivity.kt"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1) убрать плохие импорты
old_imp = """import androidx.compose.ui.input.pointer.awaitFirstDown
import androidx.compose.ui.input.pointer.forEachGesture
import androidx.compose.ui.input.pointer.awaitPointerEventScope
"""
if old_imp in text:
    text = text.replace(old_imp, "", 1)
    print("Patched: bad imports removed")

# 2) клетка piano roll: простые детекторы
old_cell = """.pointerInput(start, isNote, isEnd, rowLen.getOrElse(start) { 0 }) {
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
                        ) {"""
new_cell = """.pointerInput(start, isNote, isEnd, rowLen.getOrElse(start) { 0 }) {
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
                                }
                        ) {"""
if old_cell in text:
    text = text.replace(old_cell, new_cell, 1)
    print("Patched: roll cell gestures")
else:
    print("Skipped: roll cell gestures")

# 3) WaveEditor: перезапись хвоста на detectTransformGestures
marker = "@Composable\nfun WaveEditor("
idx = text.find(marker)
if idx >= 0:
    text = text[:idx] + '''@Composable
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

    val zoomRef = rememberUpdatedState(zoom)
    val centerRef = rememberUpdatedState(center)
    val vsRef = rememberUpdatedState(viewStart)
    val lsRef = rememberUpdatedState(loopStart)
    val leRef = rememberUpdatedState(loopEnd)
    val lineColor = C_CYAN
    val regionColor = C_PINK

    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .background(C_WAVEBG)
                .pointerInput(Unit) {
                    detectTransformGestures { centroid, pan, zoomChange, _ ->
                        val oldZ = zoomRef.value
                        val z = (oldZ * zoomChange).coerceIn(1f, 64f)
                        val oldVw = 1f / oldZ
                        val newVw = 1f / z
                        val cx = centroid.x / w
                        val lsX = (lsRef.value / 100f - vsRef.value) / oldVw
                        val leX = (leRef.value / 100f - vsRef.value) / oldVw
                        val edge = 30f / w
                        when {
                            zoomChange != 1f -> {
                                val anchor = vsRef.value + cx * oldVw
                                val ns = anchor - cx * newVw - (pan.x / w) * newVw
                                zoom = z
                                center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                            }
                            kotlin.math.abs(cx - lsX) < edge -> {
                                onLoopStart(lsRef.value + pan.x / w * oldVw * 100f)
                            }
                            kotlin.math.abs(cx - leX) < edge -> {
                                onLoopEnd(leRef.value + pan.x / w * oldVw * 100f)
                            }
                            cx > lsX && cx < leX -> {
                                val d = pan.x / w * oldVw * 100f
                                onLoopStart(lsRef.value + d)
                                onLoopEnd(leRef.value + d)
                            }
                            else -> {
                                val anchor = vsRef.value + cx * oldVw
                                val ns = anchor - cx * newVw - (pan.x / w) * newVw
                                center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                            }
                        }
                    }
                }
        ) {
            val n = peaks.size
            val h = size.height
            val width = size.width
            if (n > 0) {
                val ls = ((loopStart / 100f - viewStart) / viewW).coerceIn(0f, 1f) * width
                val le = ((loopEnd / 100f - viewStart) / viewW).coerceIn(0f, 1f) * width
                drawRoundRect(
                    color = regionColor.copy(alpha = 0.35f),
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, h),
                    cornerRadius = CornerRadius(10f)
                )
                drawRect(color = regionColor, topLeft = Offset(ls, 0f), size = Size(le - ls, 6f))
                drawRect(color = regionColor, topLeft = Offset(ls, 0f), size = Size(5f, h))
                drawRect(color = regionColor, topLeft = Offset(le - 5f, 0f), size = Size(5f, h))
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
                    drawLine(lineColor, Offset(x, h / 2 - p + off), Offset(x, h / 2 + p + off), width / bars)
                }
            }
        }
        Text(
            "x${zoom.toInt()}",
            color = Color.White,
            fontSize = 9.sp,
            modifier = Modifier.align(Alignment.TopEnd).padding(4.dp)
        )
    }
}

fun dySafe(y: Float): Float = y / 2f
'''
    print("Patched: WaveEditor rewritten v27")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Done")
