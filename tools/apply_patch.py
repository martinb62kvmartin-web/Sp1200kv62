import io

PATH = "app/src/main/java/com/example/sp1200/MainActivity.kt"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

old = """import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.forEachGesture
import androidx.compose.foundation.gestures.awaitPointerEventScope"""

new = """import androidx.compose.ui.input.pointer.awaitFirstDown
import androidx.compose.ui.input.pointer.forEachGesture
import androidx.compose.ui.input.pointer.awaitPointerEventScope"""

if old in text:
    text = text.replace(old, new, 1)
    print("Patched: gesture imports")
else:
    print("Skipped: gesture imports")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Done")
