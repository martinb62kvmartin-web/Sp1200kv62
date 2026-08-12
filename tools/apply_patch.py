import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""                .pointerInput(Unit) {
                    detectTransformGestures { centroid, pan, zoomChange, _ ->
                        val oldZ = zoomRef.value
                        val z = (oldZ * zoomChange).coerceIn(1f, 64f)
                        val oldVw = 1f / oldZ
                        val newVw = 1f / z
                        val cx = centroid.x / w
                        val lsX = (lsRef.value / 100f - vsRef.value) / oldVw
                        val leX = (leRef.value / 100f - vsRef.value) / oldVw
                        if (zoomChange == 1f && cx >= lsX && cx <= leX && centroid.y < 48f) {
                            val d = pan.x / w * oldVw * 100f
                            onLoopStart(lsRef.value + d)
                            onLoopEnd(leRef.value + d)
                        } else {
                            val anchor = vsRef.value + cx * oldVw
                            val ns = anchor - cx * newVw - (pan.x / w) * newVw
                            zoom = z
                            center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                        }
                    }
                }""", """                .pointerInput(Unit) {
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
                }""")

a("""        Handle(xFrac = (loopStart / 100f - viewStart) / viewW, w = w, color = C_PINK) { d ->
            onLoopStart(loopStart + d * 100f)
        }
        Handle(xFrac = (loopEnd / 100f - viewStart) / viewW, w = w, color = C_CYAN) { d ->
            onLoopEnd(loopEnd + d * 100f)
        }
""", "")

a("""                drawRect(
                    color = regionColor,
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, 6f)
                )""", """                drawRect(
                    color = regionColor,
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, 6f)
                )
                drawRect(color = regionColor, topLeft = Offset(ls, 0f), size = Size(5f, h))
                drawRect(color = regionColor, topLeft = Offset(le - 5f, 0f), size = Size(5f, h))""")

a("""                        val isNote = cover[step] >= 0
                        val isStart = cover[step] == step
                        val bg = when {
                            isNote -> C_PINK
                            playing && step == playhead -> Color(0xFF3A2F55)
                            step % 4 == 0 -> Color(0xFF2E2447)
                            else -> C_DARK
                        }
                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .clip(RoundedCornerShape(2.dp))
                                .background(bg)
                                .clickable {
                                    onToggleRollCell(selectedPad, step, enc)
                                }
                        ) {
                            if (isStart) {
                                Box(
                                    modifier = Modifier.fillMaxHeight().width(3.dp)
                                        .background(Color.White)
                                )
                            }
                        }""", """                        val isNote = cover[step] >= 0
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
