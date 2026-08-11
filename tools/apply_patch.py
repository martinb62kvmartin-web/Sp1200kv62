import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""import androidx.compose.ui.unit.IntSize""", """import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.geometry.CornerRadius""")

a("""        val zoomRef = rememberUpdatedState(zoom)
        val lineColor = C_CYAN""", """        val zoomRef = rememberUpdatedState(zoom)
        val lineColor = C_CYAN
        val regionColor = C_PINK
        val lsRef = rememberUpdatedState(loopStart)
        val leRef = rememberUpdatedState(loopEnd)""")

a("""                .pointerInput(Unit) {
                    detectTransformGestures { centroid, pan, zoomChange, _ ->
                        val oldZ = zoomRef.value
                        val z = (oldZ * zoomChange).coerceIn(1f, 64f)
                        val oldVw = 1f / oldZ
                        val newVw = 1f / z
                        val anchor = vsRef.value + (centroid.x / w) * oldVw
                        val ns = anchor - (centroid.x / w) * newVw - (pan.x / w) * newVw
                        zoom = z
                        center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                    }
                }""", """                .pointerInput(Unit) {
                    detectTransformGestures { centroid, pan, zoomChange, _ ->
                        val oldZ = zoomRef.value
                        val z = (oldZ * zoomChange).coerceIn(1f, 64f)
                        val oldVw = 1f / oldZ
                        val newVw = 1f / z
                        val cx = centroid.x / w
                        val lsX = (lsRef.value / 100f - vsRef.value) / oldVw
                        val leX = (leRef.value / 100f - vsRef.value) / oldVw
                        if (zoomChange == 1f && cx >= lsX && cx <= leX) {
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
                }""")

a("""                drawRect(
                    color = Color(0x33FFFFFF),
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, h)
                )""", """                drawRoundRect(
                    color = regionColor.copy(alpha = 0.35f),
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, h),
                    cornerRadius = CornerRadius(10f)
                )
                drawRect(
                    color = regionColor,
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, 6f)
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
