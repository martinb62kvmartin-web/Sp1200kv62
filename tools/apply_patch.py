import io

PATH = "app/src/main/java/com/example/sp1200/MainActivity.kt"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1) импорты жестов
if "import androidx.compose.foundation.gestures.awaitFirstDown" not in text:
    text = text.replace(
        "import androidx.compose.foundation.gestures.detectTapGestures",
        "import androidx.compose.foundation.gestures.detectTapGestures\n"
        "import androidx.compose.foundation.gestures.awaitFirstDown\n"
        "import androidx.compose.foundation.gestures.forEachGesture\n"
        "import androidx.compose.foundation.gestures.awaitPointerEventScope",
        1
    )
    print("Patched: imports gestures")

# 2) полная замена WaveEditor до конца файла
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
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .background(C_WAVEBG)
                .pointerInput(Unit) {
                    forEachGesture {
                        awaitPointerEventScope {
                            val down = awaitFirstDown()
                            down.consume()
                            val wpx = size.width.toFloat()
                            val x0 = down.position.x
                            val vw0 = 1f / zoomRef.value
                            val lsX = ((lsRef.value / 100f - vsRef.value) / vw0) * wpx
                            val leX = ((leRef.value / 100f - vsRef.value) / vw0) * wpx
                            var mode = when {
                                kotlin.math.abs(x0 - lsX) < 36f -> 1
                                kotlin.math.abs(x0 - leX) < 36f -> 2
                                x0 > lsX && x0 < leX -> 3
                                else -> 4
                            }
                            var prevX = x0
                            var prevDist = 0f
                            var prevCent = 0f
                            var c = centerRef.value
                            while (true) {
                                val ev = awaitPointerEvent()
                                val chs = ev.changes
                                if (chs.isEmpty() || !chs.any { it.pressed }) break
                                if (chs.size >= 2) {
                                    val pa = chs[0]
                                    val pb = chs[1]
                                    val dist = kotlin.math.abs(pa.position.x - pb.position.x) + 24f
                                    val cent = (pa.position.x + pb.position.x) / 2f
                                    if (prevDist > 0f) {
                                        val oldZ = zoomRef.value
                                        val z = (oldZ * dist / prevDist).coerceIn(1f, 64f)
                                        val oldVw = 1f / oldZ
                                        val newVw = 1f / z
                                        val anchor = vsRef.value + (cent / wpx) * oldVw
                                        val ns = anchor - (cent / wpx) * newVw - ((cent - prevCent) / wpx) * newVw
                                        zoom = z
                                        c = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                                        center = c
                                    }
                                    prevDist = dist
                                    prevCent = cent
                                    chs.forEach { it.consume() }
                                } else {
                                    val ch = chs.first()
                                    val dx = ch.position.x - prevX
                                    val vw = 1f / zoomRef.value
                                    when (mode) {
                                        1 -> onLoopStart(lsRef.value + dx / wpx * vw * 100f)
                                        2 -> onLoopEnd(leRef.value + dx / wpx * vw * 100f)
                                        3 -> {
                                            val d = dx / wpx * vw * 100f
                                            onLoopStart(lsRef.value + d)
                                            onLoopEnd(leRef.value + d)
                                        }
                                        else -> {
                                            c = (c - dx / wpx * vw).coerceIn(vw / 2f, 1f - vw / 2f)
                                            center = c
                                        }
                                    }
                                    ch.consume()
                                    prevX = ch.position.x
                                }
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
'''
    print("Patched: WaveEditor rewritten")

# 3) клетка piano roll, если ещё старая
if "onResizeDelta(selectedPad, start, whole)" not in text:
    s = text.find("val isNote = cover[step] >= 0")
    e = text.find("if (isStart) {")
    if s >= 0 and e >= 0:
        e2 = text.find("}", text.find("background(Color.White)", e))
        e3 = text.find("}", e2 + 1)
        e4 = text.find("}", e3 + 1)
        newCell = '''val isNote = cover[step] >= 0
                        val isStart = cover[step] == step
                        val start = cover[step]
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
                        ) {
                            if (isStart) {
                                Box(
                                    modifier = Modifier.fillMaxHeight().width(3.dp)
                                        .background(Color.White)
                                )
                            }
                        }'''
        text = text[:s] + newCell + text[e4 + 1:]
        print("Patched: roll cell rewritten")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Done")
