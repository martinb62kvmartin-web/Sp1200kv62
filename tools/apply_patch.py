import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""import androidx.compose.ui.unit.IntOffset""", """import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.window.Dialog""")

a("""    private var stretchBanks by mutableStateOf(List(4) { List(16) { 0 } })""", """    private var stretchBanks by mutableStateOf(List(4) { List(16) { 0 } })
    private var toneBanks by mutableStateOf(List(4) { List(16) { 50f } })""")

a("""                val stArr = JSONArray()
                for (p in 0 until 16) {
                    stArr.put(stretchBanks[b][p])
                }
                bo.put("stretch", stArr)""", """                val stArr = JSONArray()
                for (p in 0 until 16) {
                    stArr.put(stretchBanks[b][p])
                }
                bo.put("stretch", stArr)

                val toneArr = JSONArray()
                for (p in 0 until 16) {
                    toneArr.put(toneBanks[b][p])
                }
                bo.put("tone", toneArr)""")

a("""                bo.optJSONArray("stretch")?.let { sta ->
                    val rows = stretchBanks[b].toMutableList()
                    for (p in 0 until minOf(16, sta.length())) {
                        rows[p] = sta.optInt(p, 0)
                    }
                    newStretch[b] = rows
                }""", """                bo.optJSONArray("stretch")?.let { sta ->
                    val rows = stretchBanks[b].toMutableList()
                    for (p in 0 until minOf(16, sta.length())) {
                        rows[p] = sta.optInt(p, 0)
                    }
                    newStretch[b] = rows
                }

                bo.optJSONArray("tone")?.let { ta ->
                    val rows = toneBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ta.length())) {
                        rows[p] = ta.optDouble(p, 50.0).toFloat()
                    }
                    newTone[b] = rows
                }""")

a("""            val newStretch = stretchBanks.toMutableList()""", """            val newStretch = stretchBanks.toMutableList()
            val newTone = toneBanks.toMutableList()""")

a("""            stretchBanks = newStretch""", """            stretchBanks = newStretch
            toneBanks = newTone""")

a("""                        stretch = stretchBanks[bank][selectedPad],
                        onStretch = { v ->
                            stretchBanks = stretchBanks.set2(bank, selectedPad, v)
                            nativeSetPadStretch(selectedPad, v)
                        },""", """                        stretch = stretchBanks[bank][selectedPad],
                        onStretch = { v ->
                            stretchBanks = stretchBanks.set2(bank, selectedPad, v)
                            nativeSetPadStretch(selectedPad, v)
                        },
                        padAttack = attackBanks[bank][selectedPad],
                        onPadAttack = { value ->
                            attackBanks = attackBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padRelease = releaseBanks[bank][selectedPad],
                        onPadRelease = { value ->
                            releaseBanks = releaseBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padTone = toneBanks[bank][selectedPad],
                        onPadTone = { value ->
                            toneBanks = toneBanks.set2(bank, selectedPad, value)
                        },
                        onExport = { startExport() },
                        onTool = { name ->
                            Toast.makeText(this, "$name: soon", Toast.LENGTH_SHORT).show()
                        },
                        onPreviewPad = { nativeTriggerPad(selectedPad) },""")

a("""    stretch: Int,
    onStretch: (Int) -> Unit
) {
    var showBpm by remember { mutableStateOf(false) }""", """    stretch: Int,
    onStretch: (Int) -> Unit,
    padAttack: Float,
    onPadAttack: (Float) -> Unit,
    padRelease: Float,
    onPadRelease: (Float) -> Unit,
    padTone: Float,
    onPadTone: (Float) -> Unit,
    onExport: () -> Unit,
    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit
) {
    var showBpm by remember { mutableStateOf(false) }
    var page by remember { mutableStateOf(0) }
    var showStretch by remember { mutableStateOf(false) }
    var showTools by remember { mutableStateOf(false) }
    var algo by remember { mutableStateOf(0) }
    var stretchLen by remember { mutableStateOf(4) }""")

a("""                stretch = stretch,
                onStretch = onStretch""", """                stretch = stretch,
                onStretch = onStretch,
                padAttack = padAttack,
                onPadAttack = onPadAttack,
                padRelease = padRelease,
                onPadRelease = onPadRelease,
                padTone = padTone,
                onPadTone = onPadTone,
                onExport = onExport,
                onTool = onTool,
                onPreviewPad = onPreviewPad""")

a("""                        .fillMaxWidth()
                        .height(150.dp)
                )""", """                        .fillMaxWidth()
                        .height(110.dp)
                )""")

a("""                    KBtn("<", false, { onSelectPad((selectedPad + 15) % 16) }, Modifier.size(38.dp))
                    KBtn("ONE SHOT", !gateMode, { onGateModeChange(!gateMode) }, Modifier.weight(1f).height(42.dp))
                    KBtn("REVERSE", reverse, { onReverseToggle() }, Modifier.weight(1f).height(42.dp))
                    KBtn("LOOP", loopOn, { onLoopToggle() }, Modifier.weight(1f).height(42.dp))
                    KBtn(">", false, { onSelectPad((selectedPad + 1) % 16) }, Modifier.size(38.dp))""", """                    KBtn("<", false, { page = (page + 2) % 3 }, Modifier.size(38.dp))
                    when (page) {
                        0 -> {
                            KBtn("ONE SHOT", !gateMode, { onGateModeChange(!gateMode) }, Modifier.weight(1f).height(42.dp))
                            KBtn("REVERSE", reverse, { onReverseToggle() }, Modifier.weight(1f).height(42.dp))
                            KBtn("LOOP", loopOn, { onLoopToggle() }, Modifier.weight(1f).height(42.dp))
                        }
                        1 -> {
                            Knob("ATK", padAttack, 0f..500f, onPadAttack)
                            Knob("REL", padRelease, 0f..1000f, onPadRelease)
                            Knob("TONE", padTone, 0f..100f, onPadTone)
                        }
                        else -> {
                            KBtn("STRETCH", false, { showStretch = true }, Modifier.weight(1f).height(42.dp))
                            KBtn("TOOLS", false, { showTools = true }, Modifier.weight(1f).height(42.dp))
                        }
                    }
                    KBtn(">", false, { page = (page + 1) % 3 }, Modifier.size(38.dp))""")

a("""        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            listOf(0 to "OFF", 16 to "1BAR", 32 to "2BAR", 64 to "4BAR", 4 to "1BEAT", 8 to "2BEAT").forEach { (v, label) ->
                KBtn(label, stretch == v, { onStretch(v) }, Modifier.weight(1f).height(32.dp))
            }
        }""", """        if (showStretch) {
            Dialog(onDismissRequest = { showStretch = false }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF3A1220))
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("TIMESTRETCH", color = Color.White, fontWeight = FontWeight.Bold)
                    KBtn(
                        "duration: " + when (stretchLen) {
                            4 -> "1 BEAT"
                            8 -> "2 BEAT"
                            16 -> "1 BAR"
                            32 -> "2 BAR"
                            64 -> "4 BAR"
                            else -> "OFF"
                        },
                        false,
                        {
                            stretchLen = when (stretchLen) {
                                4 -> 8
                                8 -> 16
                                16 -> 32
                                32 -> 64
                                else -> 4
                            }
                        },
                        Modifier.fillMaxWidth().height(44.dp)
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        listOf("MODERN", "RETRO", "BEATS", "REPITCH", "CYCLIC").forEachIndexed { i, s ->
                            KBtn(s, algo == i, { algo = i }, Modifier.weight(1f).height(36.dp))
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        KBtn("PREVIEW", false, { onPreviewPad() }, Modifier.weight(1f).height(42.dp))
                        KBtn("OK", false, { onStretch(stretchLen); showStretch = false }, Modifier.weight(1f).height(42.dp))
                    }
                }
            }
        }

        if (showTools) {
            Dialog(onDismissRequest = { showTools = false }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF3A1220))
                        .padding(8.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    listOf(
                        "LABEL", "CROP", "NORMALIZE", "TRIM SILENCE", "AUTO-CHOP",
                        "SPLIT STEMS", "MAKE MONO", "BOUNCE", "EXPORT"
                    ).forEach { item ->
                        KBtn(item, false, {
                            showTools = false
                            when (item) {
                                "CROP" -> onTrim()
                                "EXPORT" -> onExport()
                                else -> onTool(item)
                            }
                        }, Modifier.fillMaxWidth().height(40.dp))
                    }
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
