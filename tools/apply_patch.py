import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""import androidx.compose.ui.window.Dialog""", """import androidx.compose.ui.window.Dialog
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.IntSize
import android.graphics.BitmapFactory""")

a("""val C_BG = Color(0xFF0F1418)
val C_CYAN = Color(0xFF29C5F6)
val C_PINK = Color(0xFFE9255B)
val C_WAVEBG = Color(0xFFA62645)
val C_DARK = Color(0xFF241B3F)""", """private val thBg = mutableStateOf(Color(0xFF0F1418))
private val thCy = mutableStateOf(Color(0xFF29C5F6))
private val thPk = mutableStateOf(Color(0xFFE9255B))
private val thWv = mutableStateOf(Color(0xFFA62645))
private val thDk = mutableStateOf(Color(0xFF241B3F))

val C_BG: Color @Composable get() = thBg.value
val C_CYAN: Color @Composable get() = thCy.value
val C_PINK: Color @Composable get() = thPk.value
val C_WAVEBG: Color @Composable get() = thWv.value
val C_DARK: Color @Composable get() = thDk.value

fun themeGet(i: Int): Color = when (i) {
    0 -> thBg.value
    1 -> thCy.value
    2 -> thPk.value
    3 -> thWv.value
    else -> thDk.value
}

fun themeSet(i: Int, c: Color) {
    when (i) {
        0 -> thBg.value = c
        1 -> thCy.value = c
        2 -> thPk.value = c
        3 -> thWv.value = c
        else -> thDk.value = c
    }
}

val PALETTE = listOf(
    Color(0xFF0F1418), Color(0xFF241B3F), Color(0xFF29C5F6), Color(0xFFE9255B),
    Color(0xFFA62645), Color(0xFF2DD4BF), Color(0xFFFBBF24), Color(0xFFA3E635),
    Color(0xFF38BDF8), Color(0xFFC084FC), Color(0xFFF472B6), Color(0xFF101C1F),
    Color(0xFFFFFFFF), Color(0xFF000000), Color(0xFF7FA6A3), Color(0xFFF0A45C)
)""")

a("""    private var padLabels by mutableStateOf(List(4) { List(16) { "" } })""", """    private var padLabels by mutableStateOf(List(4) { List(16) { "" } })
    private var wallFx by mutableStateOf(0)
    private var wallBitmap by mutableStateOf<ImageBitmap?>(null)""")

a("""            File(filesDir, "state.json").writeText(root.toString())""", """            val thArr = JSONArray()
            for (i in 0 until 5) {
                thArr.put(themeGet(i).toArgb().toLong() and 0xFFFFFFFFL)
            }
            root.put("theme", thArr)
            root.put("wallfx", wallFx)

            File(filesDir, "state.json").writeText(root.toString())""")

a("""            masterVol = root.optDouble("mvol", 100.0).toFloat()
            masterPan = root.optDouble("mpan", 50.0).toFloat()""", """            masterVol = root.optDouble("mvol", 100.0).toFloat()
            masterPan = root.optDouble("mpan", 50.0).toFloat()
            wallFx = root.optInt("wallfx", 0)

            root.optJSONArray("theme")?.let { ta ->
                for (i in 0 until minOf(5, ta.length())) {
                    themeSet(i, Color(ta.optLong(i, 0L).toInt()))
                }
            }""")

a("""    private val pickSample =""", """    private val wallLauncher =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            if (uri == null) return@registerForActivityResult
            try {
                val target = File(filesDir, "wallpaper.png")
                contentResolver.openInputStream(uri)?.use { ins ->
                    target.outputStream().use { outs -> ins.copyTo(outs) }
                }
                wallBitmap = BitmapFactory.decodeFile(target.absolutePath)?.asImageBitmap()
            } catch (_: Exception) {
            }
        }

    private val pickSample =""")

a("""        midiManager = getSystemService(MIDI_SERVICE) as MidiManager""", """        val wf = File(filesDir, "wallpaper.png")
        if (wf.exists()) {
            wallBitmap = BitmapFactory.decodeFile(wf.absolutePath)?.asImageBitmap()
        }

        midiManager = getSystemService(MIDI_SERVICE) as MidiManager""")

a("""                        onPreviewPad = { nativeTriggerPad(selectedPad) }""", """                        onPreviewPad = { nativeTriggerPad(selectedPad) },
                        wall = wallBitmap,
                        wallFx = wallFx,
                        onLoadWallpaper = { wallLauncher.launch(arrayOf("image/*")) },
                        onWallFx = { wallFx = (wallFx + 1) % 4 },
                        onClearWallpaper = {
                            wallBitmap = null
                            File(filesDir, "wallpaper.png").delete()
                        }""")

a("""    labels: List<String>,
    onLabel: (String) -> Unit
) {
    Column(""", """    labels: List<String>,
    onLabel: (String) -> Unit,
    wall: ImageBitmap?,
    wallFx: Int,
    onLoadWallpaper: () -> Unit,
    onWallFx: () -> Unit,
    onClearWallpaper: () -> Unit
) {
    Box(modifier = Modifier.fillMaxSize()) {
        if (wall != null) {
            Wallpaper(bmp = wall, fx = wallFx)
        }
        Column(""")

a("""        }
    }
}

@Composable
fun SampleView(""", """        }
        }
    }
}

@Composable
fun SampleView(""")

a("""            7 -> SettingsView(
                midiMode = midiMode,
                onMidiModeChange = onMidiModeChange,
                exportBars = exportBars,
                onExportBarsCycle = onExportBarsCycle,
                exporting = exporting,
                onExport = onExport
            )""", """            7 -> SettingsView(
                midiMode = midiMode,
                onMidiModeChange = onMidiModeChange,
                exportBars = exportBars,
                onExportBarsCycle = onExportBarsCycle,
                exporting = exporting,
                onExport = onExport,
                wallFx = wallFx,
                onLoadWallpaper = onLoadWallpaper,
                onWallFx = onWallFx,
                onClearWallpaper = onClearWallpaper
            )""")

a("""    exporting: Boolean,
    onExport: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("SETTINGS", color = C_CYAN, fontWeight = FontWeight.Bold)""", """    exporting: Boolean,
    onExport: () -> Unit,
    wallFx: Int,
    onLoadWallpaper: () -> Unit,
    onWallFx: () -> Unit,
    onClearWallpaper: () -> Unit
) {
    var colorEl by remember { mutableStateOf(-1) }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("SETTINGS", color = C_CYAN, fontWeight = FontWeight.Bold)

        Text("COLORS", color = C_CYAN, fontWeight = FontWeight.Bold)
        listOf("BACKGROUND", "ACCENT", "PINK", "WAVE BG", "PANELS").forEachIndexed { i, name ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(name, color = Color.White, fontSize = 11.sp, modifier = Modifier.weight(1f))
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(themeGet(i))
                        .clickable { colorEl = i }
                )
            }
        }

        Text("WALLPAPER", color = C_CYAN, fontWeight = FontWeight.Bold)
        KBtn("LOAD WALLPAPER", false, onLoadWallpaper, Modifier.fillMaxWidth().height(44.dp))
        KBtn(
            "FX: " + when (wallFx) { 0 -> "OFF"; 1 -> "ZOOM"; 2 -> "PAN"; else -> "PULSE" },
            wallFx != 0, onWallFx, Modifier.fillMaxWidth().height(44.dp)
        )
        KBtn("CLEAR WALLPAPER", false, onClearWallpaper, Modifier.fillMaxWidth().height(44.dp))""")

a("""        KBtn(if (exporting) "EXPORTING..." else "EXPORT BEAT", exporting, onExport, Modifier.fillMaxWidth().height(44.dp))
    }
}""", """        KBtn(if (exporting) "EXPORTING..." else "EXPORT BEAT", exporting, onExport, Modifier.fillMaxWidth().height(44.dp))

        if (colorEl >= 0) {
            Dialog(onDismissRequest = { colorEl = -1 }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF201018))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("COLOR", color = Color.White, fontWeight = FontWeight.Bold)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        PALETTE.take(8).forEach { c ->
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .height(40.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(c)
                                    .clickable {
                                        themeSet(colorEl, c)
                                        colorEl = -1
                                    }
                            )
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        PALETTE.drop(8).forEach { c ->
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .height(40.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(c)
                                    .clickable {
                                        themeSet(colorEl, c)
                                        colorEl = -1
                                    }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun Wallpaper(bmp: ImageBitmap, fx: Int) {
    val inf = rememberInfiniteTransition()
    val t by inf.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(6000), RepeatMode.Reverse)
    )
    val scale = when (fx) { 1 -> 1f + 0.15f * t; else -> 1f }
    val alpha = when (fx) { 3 -> 0.4f + 0.3f * t; else -> 0.7f }
    val offX = when (fx) { 2 -> (t - 0.5f) * 0.1f; else -> 0f }

    Canvas(modifier = Modifier.fillMaxSize()) {
        val w = size.width
        val h = size.height
        val bw = bmp.width.toFloat()
        val bh = bmp.height.toFloat()
        if (bw > 0f && bh > 0f) {
            val base = maxOf(w / bw, h / bh)
            val s = base * scale
            val dw = bw * s
            val dh = bh * s
            val dx = (w - dw) / 2 + offX * w
            val dy = (h - dh) / 2
            drawImage(
                image = bmp,
                dstOffset = IntOffset(dx.toInt(), dy.toInt()),
                dstSize = IntSize(dw.toInt(), dh.toInt()),
                alpha = alpha
            )
        }
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
