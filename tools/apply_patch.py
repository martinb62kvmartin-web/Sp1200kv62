import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit
) {
    var showBpm""", """    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit,
    labels: List<String>,
    onLabel: (String) -> Unit
) {
    var showBpm""")

a("""        val zoomRef = rememberUpdatedState(zoom)
        val centerRef = rememberUpdatedState(center)""", """        val zoomRef = rememberUpdatedState(zoom)
        val centerRef = rememberUpdatedState(center)
        val vsRef = rememberUpdatedState(viewStart)""")

a("""                .pointerInput(Unit) {
                    detectTransformGestures { _, pan, zoomChange, _ ->
                        val z = (zoomRef.value * zoomChange).coerceIn(1f, 32f)
                        val vw = 1f / z
                        val c = (centerRef.value - pan.x / w * vw).coerceIn(vw / 2f, 1f - vw / 2f)
                        zoom = z
                        center = c
                    }
                }""", """                .pointerInput(Unit) {
                    detectTransformGestures { centroid, pan, zoomChange, _ ->
                        val oldZ = zoomRef.value
                        val z = (oldZ * zoomChange).coerceIn(1f, 64f)
                        val oldVw = 1f / oldZ
                        val newVw = 1f / z
                        val anchor = vsRef.value + (centroid.x / w) * oldVw
                        val ns = anchor - (centroid.x / w) * newVw - (pan.x / w) * newVw
                        zoom = z
                        center = ns + newVw / 2f
                    }
                }""")

a("""                            detectTapGestures(
                                onPress = {
                                    onPadDown(index)""", """                            detectTapGestures(
                                onPress = {
                                    onSelectPad(index)
                                    onPadDown(index)""")

a("""                    Text(
                        text = "${index + 1}",
                        color = Color.White,
                        fontSize = 9.sp,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(4.dp)
                    )""", """                    Text(
                        text = labels[index].ifEmpty { "${index + 1}" },
                        color = Color.White,
                        fontSize = 9.sp,
                        maxLines = 1,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(4.dp)
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
