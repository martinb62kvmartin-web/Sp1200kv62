import io
import os
import sys

PATCHES = [
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """import androidx.compose.foundation.lazy.LazyColumn""",
        """import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private external fun nativeSetSongOn(enabled: Boolean)
    private external fun nativeSetSongLen(len: Int)
    private external fun nativeSetSongBank(slot: Int, bank: Int)""",
        """    private external fun nativeSetSongOn(enabled: Boolean)
    private external fun nativeSetSongLen(len: Int)
    private external fun nativeSetSongBank(slot: Int, bank: Int)
    private external fun nativeSetPadVol(padIndex: Int, vol: Float)
    private external fun nativeSetPadPan(padIndex: Int, pan: Float)
    private external fun nativeSetMasterVol(vol: Float)
    private external fun nativeSetMasterPan(pan: Float)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var prevHits = MutableList(8) { 0L }""",
        """    private var prevHits = MutableList(16) { 0L }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var hitTimes by mutableStateOf(List(8) { 0L })""",
        """    private var hitTimes by mutableStateOf(List(16) { 0L })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var songOn by mutableStateOf(false)""",
        """    private var songOn by mutableStateOf(false)
    private var mixAssign by mutableStateOf(List(5) { it })
    private var volBanks by mutableStateOf(List(16) { 100f })
    private var panBanks by mutableStateOf(List(16) { 50f })
    private var masterVol by mutableStateOf(100f)
    private var masterPan by mutableStateOf(50f)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var mutes by mutableStateOf(List(8) { false })""",
        """    private var mutes by mutableStateOf(List(16) { false })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var solos by mutableStateOf(List(8) { false })""",
        """    private var solos by mutableStateOf(List(16) { false })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var patternBanks by mutableStateOf(List(4) { List(8) { 0 } })""",
        """    private var patternBanks by mutableStateOf(List(4) { List(16) { 0 } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var rollBanks by mutableStateOf(List(4) { List(8) { List(16) { 0 } } })""",
        """    private var rollBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var rollLenBanks by mutableStateOf(List(4) { List(8) { List(16) { 0 } } })""",
        """    private var rollLenBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var pitchBanks by mutableStateOf(List(4) { List(8) { 0f } })""",
        """    private var pitchBanks by mutableStateOf(List(4) { List(16) { 0f } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var attackBanks by mutableStateOf(List(4) { List(8) { 0f } })""",
        """    private var attackBanks by mutableStateOf(List(4) { List(16) { 0f } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var decayBanks by mutableStateOf(List(4) { List(8) { 0f } })""",
        """    private var decayBanks by mutableStateOf(List(4) { List(16) { 0f } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var sustainBanks by mutableStateOf(List(4) { List(8) { 100f } })""",
        """    private var sustainBanks by mutableStateOf(List(4) { List(16) { 100f } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    private var releaseBanks by mutableStateOf(List(4) { List(8) { 50f } })""",
        """    private var releaseBanks by mutableStateOf(List(4) { List(16) { 50f } })"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            root.put("songon", songOn)""",
        """            root.put("songon", songOn)
            root.put("vol", JSONArray(volBanks))
            root.put("pan", JSONArray(panBanks))
            root.put("mvol", masterVol)
            root.put("mpan", masterPan)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            songOn = root.optBoolean("songon", false)""",
        """            songOn = root.optBoolean("songon", false)
            root.optJSONArray("vol")?.let { va ->
                volBanks = (0 until 16).map { va.optDouble(it, 100.0).toFloat() }
            }
            root.optJSONArray("pan")?.let { va ->
                panBanks = (0 until 16).map { va.optDouble(it, 50.0).toFloat() }
            }
            masterVol = root.optDouble("mvol", 100.0).toFloat()
            masterPan = root.optDouble("mpan", 50.0).toFloat()"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                mutes = (0 until 8).map { m.optBoolean(it, false) }""",
        """                mutes = (0 until 16).map { m.optBoolean(it, false) }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                solos = (0 until 8).map { s.optBoolean(it, false) }""",
        """                solos = (0 until 16).map { s.optBoolean(it, false) }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                    newPatterns[b] = (0 until 8).map { pat.optInt(it, 0) }""",
        """                    newPatterns[b] = (0 until 16).map { pat.optInt(it, 0) }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                    for (p in 0 until minOf(8, ra.length())) {""",
        """                    for (p in 0 until minOf(16, ra.length())) {"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                    for (p in 0 until minOf(8, ra.length())) {""",
        """                    for (p in 0 until minOf(16, ra.length())) {"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                    for (p in 0 until minOf(8, la.length())) {""",
        """                    for (p in 0 until minOf(16, la.length())) {"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                    for (p in 0 until minOf(8, pa.length())) {""",
        """                    for (p in 0 until minOf(16, pa.length())) {"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        for (p in 0 until 8) {
            nativeSetMute(p, mutes[p])
            nativeSetSolo(p, solos[p])
        }""",
        """        for (p in 0 until 16) {
            nativeSetMute(p, mutes[p])
            nativeSetSolo(p, solos[p])
        }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            for (p in 0 until 8) {
                nativeSeqSetMask(p, patternBanks[b][p])""",
        """            for (p in 0 until 16) {
                nativeSeqSetMask(p, patternBanks[b][p])"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        nativeSetSongOn(songOn)
        nativeSetSongLen(8)
        for (i in 0 until 8) {
            nativeSetSongBank(i, songSlots[i])
        }

        nativeSetBank(bank)""",
        """        nativeSetSongOn(songOn)
        nativeSetSongLen(8)
        for (i in 0 until 8) {
            nativeSetSongBank(i, songSlots[i])
        }

        for (p in 0 until 16) {
            nativeSetPadVol(p, volBanks[p] / 100f)
            nativeSetPadPan(p, (panBanks[p] - 50f) / 50f)
        }
        nativeSetMasterVol(masterVol / 100f)
        nativeSetMasterPan((masterPan - 50f) / 50f)

        nativeSetBank(bank)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            for (p in 0 until 8) {
                val f = File(dir, "b${b}_p$p.wav")""",
        """            for (p in 0 until 16) {
                val f = File(dir, "b${b}_p$p.wav")"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                for (i in 0 until 8) {
                    val h = nativeGetPadHits(i)""",
        """                for (i in 0 until 16) {
                    val h = nativeGetPadHits(i)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                        onSongSlotCycle = { i ->
                            val v = (songSlots[i] + 1) % 4
                            songSlots = songSlots.toMutableList().also { it[i] = v }
                            nativeSetSongBank(i, v)
                        },""",
        """                        onSongSlotCycle = { i ->
                            val v = (songSlots[i] + 1) % 4
                            songSlots = songSlots.toMutableList().also { it[i] = v }
                            nativeSetSongBank(i, v)
                        },
                        mixAssign = mixAssign,
                        onMixAssignCycle = { i ->
                            mixAssign = mixAssign.toMutableList().also { it[i] = (it[i] + 1) % 16 }
                        },
                        volOf = { p -> volBanks[p] },
                        panOf = { p -> panBanks[p] },
                        onVol = { p, value ->
                            volBanks = volBanks.toMutableList().also { it[p] = value }
                            nativeSetPadVol(p, value / 100f)
                        },
                        onPan = { p, value ->
                            panBanks = panBanks.toMutableList().also { it[p] = value }
                            nativeSetPadPan(p, (value - 50f) / 50f)
                        },
                        masterVol = masterVol,
                        onMasterVol = { value ->
                            masterVol = value
                            nativeSetMasterVol(value / 100f)
                        },
                        masterPan = masterPan,
                        onMasterPan = { value ->
                            masterPan = value
                            nativeSetMasterPan((value - 50f) / 50f)
                        },"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    songSlots: List<Int>,
    songOn: Boolean,
    onSongOnToggle: () -> Unit,
    onSongSlotCycle: (Int) -> Unit,""",
        """    songSlots: List<Int>,
    songOn: Boolean,
    onSongOnToggle: () -> Unit,
    onSongSlotCycle: (Int) -> Unit,
    mixAssign: List<Int>,
    onMixAssignCycle: (Int) -> Unit,
    volOf: (Int) -> Float,
    panOf: (Int) -> Float,
    onVol: (Int, Float) -> Unit,
    onPan: (Int, Float) -> Unit,
    masterVol: Float,
    onMasterVol: (Float) -> Unit,
    masterPan: Float,
    onMasterPan: (Float) -> Unit,"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            SmallButton("SONG", view == 5) { onViewChange(5) }
        }""",
        """            SmallButton("SONG", view == 5) { onViewChange(5) }
            SmallButton("MIX", view == 6) { onViewChange(6) }
        }"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            else -> {
                Text(
                    text = "Hold = play. Load samples in LIB. Bank: ${'A' + bank}",""",
        """            6 -> MixView(
                mixAssign = mixAssign,
                onMixAssignCycle = onMixAssignCycle,
                volOf = volOf,
                panOf = panOf,
                onVol = onVol,
                onPan = onPan,
                masterVol = masterVol,
                onMasterVol = onMasterVol,
                masterPan = masterPan,
                onMasterPan = onMasterPan
            )

            else -> {
                Text(
                    text = "Hold = play. Load samples in LIB. Bank: ${'A' + bank}","""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                    items(8) { index ->""",
        """                    items(16) { index ->"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        for (pad in 0 until 8) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(26.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (mutes[pad]) Color(0xFFB71C1C) else Color(0xFF333333))""",
        """    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        for (pad in 0 until 16) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(26.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (mutes[pad]) Color(0xFFB71C1C) else Color(0xFF333333))"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        for (pad in 0 until 8) {
                val bg = when {
                    armedFile != null -> Color(0xFF3A3A5A)""",
        """        for (pad in 0 until 16) {
                val bg = when {
                    armedFile != null -> Color(0xFF3A3A5A)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            for (pad in 0 until 8) {
                val bg = when {
                    pad == selectedPad -> Color.White""",
        """            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> Color.White"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            for (pad in 0 until 8) {
                val bg = when {
                    pad == selectedPad -> Color.White""",
        """            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> Color.White"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {""",
        """    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "RELEASE ${padReleaseMs.toInt()} ms",""",
        """            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "VOL ${padVol.toInt()}%",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padVol,
                    onValueChange = onPadVol,
                    valueRange = 0f..150f
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "PAN ${padPan.toInt()}",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padPan,
                    onValueChange = onPadPan,
                    valueRange = 0f..100f
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "RELEASE ${padReleaseMs.toInt()} ms","""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                padReleaseMs = releaseBanks[bank][selectedPad],
                onPadReleaseMs = { value ->
                    releaseBanks = releaseBanks.set2(bank, selectedPad, value)
                    pushPadParams(selectedPad)
                }
            )""",
        """                padReleaseMs = releaseBanks[bank][selectedPad],
                onPadReleaseMs = { value ->
                    releaseBanks = releaseBanks.set2(bank, selectedPad, value)
                    pushPadParams(selectedPad)
                },
                padVol = volBanks[selectedPad],
                onPadVol = { value ->
                    volBanks = volBanks.toMutableList().also { it[selectedPad] = value }
                    nativeSetPadVol(selectedPad, value / 100f)
                },
                padPan = panBanks[selectedPad],
                onPadPan = { value ->
                    panBanks = panBanks.toMutableList().also { it[selectedPad] = value }
                    nativeSetPadPan(selectedPad, (value - 50f) / 50f)
                }
            )"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (i in 4 until 8) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(44.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF262636))
                        .clickable { onSongSlotCycle(i) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${'A' + songSlots[i]}",
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium
                    )
                }
            }
        }
    }
}""",
        """        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (i in 4 until 8) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(44.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF262636))
                        .clickable { onSongSlotCycle(i) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${'A' + songSlots[i]}",
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium
                    )
                }
            }
        }
    }
}

@Composable
fun MixView(
    mixAssign: List<Int>,
    onMixAssignCycle: (Int) -> Unit,
    volOf: (Int) -> Float,
    panOf: (Int) -> Float,
    onVol: (Int, Float) -> Unit,
    onPan: (Int, Float) -> Unit,
    masterVol: Float,
    onMasterVol: (Float) -> Unit,
    masterPan: Float,
    onMasterPan: (Float) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "MASTER",
                color = Color(0xFF4FC3F7),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.width(64.dp)
            )
            Column(modifier = Modifier.weight(1f)) {
                Text("VOL ${masterVol.toInt()}%", color = Color.White, fontSize = 9.sp)
                Slider(value = masterVol, onValueChange = onMasterVol, valueRange = 0f..150f)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text("PAN ${masterPan.toInt()}", color = Color.White, fontSize = 9.sp)
                Slider(value = masterPan, onValueChange = onMasterPan, valueRange = 0f..100f)
            }
        }

        for (ch in 0 until 5) {
            val pad = mixAssign[ch]
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(64.dp)
                        .height(40.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF262636))
                        .clickable { onMixAssignCycle(ch) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "CH${ch + 1}:P${pad + 1}",
                        color = Color.White,
                        fontSize = 9.sp
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text("VOL ${volOf(pad).toInt()}%", color = Color.White, fontSize = 9.sp)
                    Slider(value = volOf(pad), onValueChange = { onVol(pad, it) }, valueRange = 0f..150f)
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text("PAN ${panOf(pad).toInt()}", color = Color.White, fontSize = 9.sp)
                    Slider(value = panOf(pad), onValueChange = { onPan(pad, it) }, valueRange = 0f..100f)
                }
            }
        }
    }
}"""
    ),
]

def main():
    if not PATCHES:
        print("No patches to apply.")
        return

    for path, old, new in PATCHES:
        if not os.path.exists(path):
            print("ERROR: missing file", path)
            sys.exit(1)

        with io.open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if old not in text:
            print("ERROR: pattern not found in", path)
            print("PATTERN:", old[:120])
            sys.exit(1)

        text = text.replace(old, new, 1)

        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)

        print("Patched:", path)

main()
