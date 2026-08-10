import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def h(old, new):
    P.append(("app/src/main/cpp/audio_engine.h", old, new))
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))
def j(old, new):
    P.append(("app/src/main/cpp/native-lib.cpp", old, new))

# ---------- 16 pads / stereo / mixer (engine) ----------
h("    static constexpr int kNumPads = 8;", "    static constexpr int kNumPads = 16;")
h("""    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);
""", """    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);

    void setPadVol(int padIndex, float vol);
    void setPadPan(int padIndex, float pan);
    void setMasterVol(float vol);
    void setMasterPan(float pan);
""")
h("""    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};
""", """    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};

    std::array<std::atomic<float>, kNumPads> padVol{};
    std::array<std::atomic<float>, kNumPads> padPan{};
    std::atomic<float> masterVol{1.0f};
    std::atomic<float> masterPan{0.0f};
""")
h("""    float lpState = 0.0f;
""", """    float lpStateL = 0.0f;
    float lpStateR = 0.0f;
""")
c("""    for (auto& s : solos) s.store(false);
""", """    for (auto& s : solos) s.store(false);
    for (auto& v : padVol) v.store(1.0f);
    for (auto& p : padPan) p.store(0.0f);
""")
c("""void AudioEngine::setGateMode(bool enabled) {""", """void AudioEngine::setPadVol(int padIndex, float vol) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    padVol[padIndex].store(clampd(vol, 0.0f, 1.5f), std::memory_order_relaxed);
}

void AudioEngine::setPadPan(int padIndex, float pan) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    padPan[padIndex].store(clampd(pan, -1.0f, 1.0f), std::memory_order_relaxed);
}

void AudioEngine::setMasterVol(float vol) {
    masterVol.store(clampd(vol, 0.0f, 1.5f), std::memory_order_relaxed);
}

void AudioEngine::setMasterPan(float pan) {
    masterPan.store(clampd(pan, -1.0f, 1.0f), std::memory_order_relaxed);
}

void AudioEngine::setGateMode(bool enabled) {""")
c("""bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate) {""", """bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate, int channels) {""")
c("""    const uint16_t ch = 1;""", """    const uint16_t ch = static_cast<uint16_t>(channels > 0 ? channels : 1);""")
c("""    const uint32_t byteRate = rate * 2;
    const uint16_t blockAlign = 2;""", """    const uint32_t byteRate = rate * ch;
    const uint16_t blockAlign = static_cast<uint16_t>(2 * ch);""")
c("""        writeWavFile(path, sample->data, static_cast<uint32_t>(rate));""", """        writeWavFile(path, sample->data, static_cast<uint32_t>(rate), 1);""")
c("""        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate));""", """        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate), 1);""")
c("""    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate));""", """    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate), 2);""")
c("""    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(1);
""", """    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(2);
""")
c("""        float mix = 0.0f;
""", """        float mixL = 0.0f;
        float mixR = 0.0f;
""")
c("""            mix += static_cast<float>(renderVoice(v) * v.envLevel);
""", """            {
                const int pIdx = v.padIndex;
                const float vol = padVol[pIdx].load(std::memory_order_relaxed);
                const float pan = padPan[pIdx].load(std::memory_order_relaxed);
                const float gl = vol * (pan < 0.0f ? 1.0f : 1.0f - pan);
                const float gr = vol * (pan > 0.0f ? 1.0f : 1.0f + pan);
                const float m = static_cast<float>(renderVoice(v) * v.envLevel);
                mixL += m * gl;
                mixR += m * gr;
            }
""")
c("""        if (mix > 1.0f) {
            mix = 1.0f;
        } else if (mix < -1.0f) {
            mix = -1.0f;
        }

        if (crunch) {
            lpState += 0.35f * (mix - lpState);
            mix = vintage(lpState);
        }

        output[frame] = mix * 0.8f;
""", """        const float mv = masterVol.load(std::memory_order_relaxed);
        const float mp = masterPan.load(std::memory_order_relaxed);
        float L = mixL * mv * (mp < 0.0f ? 1.0f : 1.0f - mp);
        float R = mixR * mv * (mp > 0.0f ? 1.0f : 1.0f + mp);

        if (L > 1.0f) L = 1.0f; else if (L < -1.0f) L = -1.0f;
        if (R > 1.0f) R = 1.0f; else if (R < -1.0f) R = -1.0f;

        if (crunch) {
            lpStateL += 0.35f * (L - lpStateL);
            L = vintage(lpStateL);
            lpStateR += 0.35f * (R - lpStateR);
            R = vintage(lpStateR);
        }

        output[frame * 2] = L * 0.8f;
        output[frame * 2 + 1] = R * 0.8f;
""")
j("""JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {""", """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadVol(JNIEnv*, jobject, jint padIndex, jfloat vol) {
    if (engine != nullptr) {
        engine->setPadVol(padIndex, vol);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadPan(JNIEnv*, jobject, jint padIndex, jfloat pan) {
    if (engine != nullptr) {
        engine->setPadPan(padIndex, pan);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMasterVol(JNIEnv*, jobject, jfloat vol) {
    if (engine != nullptr) {
        engine->setMasterVol(vol);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMasterPan(JNIEnv*, jobject, jfloat pan) {
    if (engine != nullptr) {
        engine->setMasterPan(pan);
    }
}

JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {""")

# ---------- 16 pads / mixer (kotlin) ----------
a("""import androidx.compose.foundation.lazy.LazyColumn""", """import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll""")
a("""    private external fun nativeStopCapture(path: String): Boolean""", """    private external fun nativeStopCapture(path: String): Boolean
    private external fun nativeSetPadVol(padIndex: Int, vol: Float)
    private external fun nativeSetPadPan(padIndex: Int, pan: Float)
    private external fun nativeSetMasterVol(vol: Float)
    private external fun nativeSetMasterPan(pan: Float)""")
a("""    private var prevHits = MutableList(8) { 0L }""", """    private var prevHits = MutableList(16) { 0L }""")
a("""    private var hitTimes by mutableStateOf(List(8) { 0L })""", """    private var hitTimes by mutableStateOf(List(16) { 0L })""")
a("""    private var exportBars by mutableStateOf(2)""", """    private var mixAssign by mutableStateOf(List(5) { it })
    private var volBanks by mutableStateOf(List(16) { 100f })
    private var panBanks by mutableStateOf(List(16) { 50f })
    private var masterVol by mutableStateOf(100f)
    private var masterPan by mutableStateOf(50f)
    private var exportBars by mutableStateOf(2)""")
a("""    private var mutes by mutableStateOf(List(8) { false })""", """    private var mutes by mutableStateOf(List(16) { false })""")
a("""    private var solos by mutableStateOf(List(8) { false })""", """    private var solos by mutableStateOf(List(16) { false })""")
a("""    private var patternBanks by mutableStateOf(List(4) { List(8) { 0 } })""", """    private var patternBanks by mutableStateOf(List(4) { List(16) { 0 } })""")
a("""    private var rollBanks by mutableStateOf(List(4) { List(8) { List(16) { 0 } } })""", """    private var rollBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })""")
a("""    private var rollLenBanks by mutableStateOf(List(4) { List(8) { List(16) { 0 } } })""", """    private var rollLenBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })""")
a("""    private var pitchBanks by mutableStateOf(List(4) { List(8) { 0f } })""", """    private var pitchBanks by mutableStateOf(List(4) { List(16) { 0f } })""")
a("""    private var attackBanks by mutableStateOf(List(4) { List(8) { 0f } })""", """    private var attackBanks by mutableStateOf(List(4) { List(16) { 0f } })""")
a("""    private var decayBanks by mutableStateOf(List(4) { List(8) { 0f } })""", """    private var decayBanks by mutableStateOf(List(4) { List(16) { 0f } })""")
a("""    private var sustainBanks by mutableStateOf(List(4) { List(8) { 100f } })""", """    private var sustainBanks by mutableStateOf(List(4) { List(16) { 100f } })""")
a("""    private var releaseBanks by mutableStateOf(List(4) { List(8) { 50f } })""", """    private var releaseBanks by mutableStateOf(List(4) { List(16) { 50f } })""")
a("""            root.put("banks", banksArr)""", """            root.put("banks", banksArr)
            root.put("vol", JSONArray(volBanks))
            root.put("pan", JSONArray(panBanks))
            root.put("mvol", masterVol)
            root.put("mpan", masterPan)""")
a("""            patternBanks = newPatterns""", """            root.optJSONArray("vol")?.let { va ->
                volBanks = (0 until 16).map { va.optDouble(it, 100.0).toFloat() }
            }
            root.optJSONArray("pan")?.let { va ->
                panBanks = (0 until 16).map { va.optDouble(it, 50.0).toFloat() }
            }
            masterVol = root.optDouble("mvol", 100.0).toFloat()
            masterPan = root.optDouble("mpan", 50.0).toFloat()

            patternBanks = newPatterns""")
a("""                mutes = (0 until 8).map { m.optBoolean(it, false) }""", """                mutes = (0 until 16).map { m.optBoolean(it, false) }""")
a("""                solos = (0 until 8).map { s.optBoolean(it, false) }""", """                solos = (0 until 16).map { s.optBoolean(it, false) }""")
a("""                    newPatterns[b] = (0 until 8).map { pat.optInt(it, 0) }""", """                    newPatterns[b] = (0 until 16).map { pat.optInt(it, 0) }""")
a("""                    for (p in 0 until minOf(8, ra.length())) {""", """                    for (p in 0 until minOf(16, ra.length())) {""")
a("""                    for (p in 0 until minOf(8, ra.length())) {""", """                    for (p in 0 until minOf(16, ra.length())) {""")
a("""                    for (p in 0 until minOf(8, la.length())) {""", """                    for (p in 0 until minOf(16, la.length())) {""")
a("""                    for (p in 0 until minOf(8, pa.length())) {""", """                    for (p in 0 until minOf(16, pa.length())) {""")
a("""        for (p in 0 until 8) {
            nativeSetMute(p, mutes[p])
            nativeSetSolo(p, solos[p])
        }""", """        for (p in 0 until 16) {
            nativeSetMute(p, mutes[p])
            nativeSetSolo(p, solos[p])
        }""")
a("""            for (p in 0 until 8) {
                nativeSeqSetMask(p, patternBanks[b][p])""", """            for (p in 0 until 16) {
                nativeSeqSetMask(p, patternBanks[b][p])""")
a("""        nativeSetBank(bank)
    }

    private fun restoreSamples() {""", """        for (p in 0 until 16) {
            nativeSetPadVol(p, volBanks[p] / 100f)
            nativeSetPadPan(p, (panBanks[p] - 50f) / 50f)
        }
        nativeSetMasterVol(masterVol / 100f)
        nativeSetMasterPan((masterPan - 50f) / 50f)

        nativeSetBank(bank)
    }

    private fun restoreSamples() {""")
a("""            for (p in 0 until 8) {
                val f = File(dir, "b${b}_p$p.wav")""", """            for (p in 0 until 16) {
                val f = File(dir, "b${b}_p$p.wav")""")
a("""                for (i in 0 until 8) {
                    val h = nativeGetPadHits(i)""", """                for (i in 0 until 16) {
                    val h = nativeGetPadHits(i)""")
a("""                        exportBars = exportBars,""", """                        mixAssign = mixAssign,
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
                        },
                        exportBars = exportBars,""")
a("""    exportBars: Int,
    onExportBarsCycle: () -> Unit,""", """    mixAssign: List<Int>,
    onMixAssignCycle: (Int) -> Unit,
    volOf: (Int) -> Float,
    panOf: (Int) -> Float,
    onVol: (Int, Float) -> Unit,
    onPan: (Int, Float) -> Unit,
    masterVol: Float,
    onMasterVol: (Float) -> Unit,
    masterPan: Float,
    onMasterPan: (Float) -> Unit,
    exportBars: Int,
    onExportBarsCycle: () -> Unit,""")
a("""            SmallButton("LIB", view == 4) { onViewChange(4) }""", """            SmallButton("LIB", view == 4) { onViewChange(4) }
            SmallButton("MIX", view == 6) { onViewChange(6) }""")
a("""            else -> {
                Text(
                    text = "Hold = play. Load samples in LIB. Bank: ${'A' + bank}",""", """            6 -> MixView(
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
                    text = "Hold = play. Load samples in LIB. Bank: ${'A' + bank}",""")
a("""                    items(8) { index ->""", """                    items(16) { index ->""")
a("""    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {""", """    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {""")
a("""        for (pad in 0 until 8) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(26.dp)""", """        for (pad in 0 until 16) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(26.dp)""")
a("""        for (pad in 0 until 8) {
                val bg = when {
                    armedFile != null ->""", """        for (pad in 0 until 16) {
                val bg = when {
                    armedFile != null ->""")
a("""            for (pad in 0 until 8) {
                val bg = when {
                    pad == selectedPad -> Color.White""", """            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> Color.White""")
a("""            for (pad in 0 until 8) {
                val bg = when {
                    pad == selectedPad -> Color.White""", """            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> Color.White""")
a("""    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit
) {""", """    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit
) {""")
a("""                    releaseBanks = releaseBanks.set2(bank, selectedPad, value)
                    pushPadParams(selectedPad)
                }""", """                    releaseBanks = releaseBanks.set2(bank, selectedPad, value)
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
                }""")
a("""        Text(
            text = if (hasSample) "WAV ${index + 1}" else "PAD ${index + 1}",
            color = Color.Black,
            style = MaterialTheme.typography.titleMedium
        )
    }
}""", """        Text(
            text = if (hasSample) "WAV ${index + 1}" else "PAD ${index + 1}",
            color = Color.Black,
            style = MaterialTheme.typography.titleMedium
        )
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
                color = Color(0xFF2DD4BF),
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
                        .background(Color(0xFF152528))
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
}""")

# ---------- тема (бирюза) ----------
a("color = Color(0xFF141428)", "color = Color(0xFF0C1416)")
a("""        colors = ButtonDefaults.buttonColors(
            containerColor = if (active) Color(0xFFE91E5A) else Color(0xFF262636)
        ),""", """        colors = ButtonDefaults.buttonColors(
            containerColor = if (active) Color(0xFF2DD4BF) else Color(0xFF152528)
        ),""")
a("""        Text(
            text = label,
            color = Color.White,
            fontSize = 10.sp,
            maxLines = 1
        )""", """        Text(
            text = label,
            color = if (active) Color(0xFF06201D) else Color(0xFFBFE6E2),
            fontSize = 10.sp,
            maxLines = 1
        )""")
a("""            style = MaterialTheme.typography.titleLarge,
            color = Color(0xFF4FC3F7)""", """            style = MaterialTheme.typography.titleLarge,
            color = Color(0xFF2DD4BF)""")
a("""fun padColor(index: Int): Color = when (index) {
    0 -> Color(0xFFE53935)
    1 -> Color(0xFFFB8C00)
    2 -> Color(0xFFFDD835)
    3 -> Color(0xFF43A047)
    4 -> Color(0xFF1E88E5)
    5 -> Color(0xFF8E24AA)
    6 -> Color(0xFF00ACC1)
    else -> Color(0xFF546E7A)
}""", """fun padColor(index: Int): Color = when (index) {
    0 -> Color(0xFF2DD4BF)
    1 -> Color(0xFF4CC3E0)
    2 -> Color(0xFF7FA8F0)
    3 -> Color(0xFFA78BFA)
    4 -> Color(0xFFE07FA0)
    5 -> Color(0xFFF0A45C)
    6 -> Color(0xFFB8E05C)
    7 -> Color(0xFF5EEAD4)
    8 -> Color(0xFF38BDF8)
    9 -> Color(0xFF818CF8)
    10 -> Color(0xFFC084FC)
    11 -> Color(0xFFF472B6)
    12 -> Color(0xFFFBBF24)
    13 -> Color(0xFFA3E635)
    14 -> Color(0xFF34D399)
    else -> Color(0xFF22D3EE)
}""")
a("Color(0xFFE91E5A)", "Color(0xFF2DD4BF)")
a("Color(0xFFE91E5A)", "Color(0xFF2DD4BF)")
a("Color(0xFFE91E5A)", "Color(0xFF2DD4BF)")
a("Color(0xFF262636)", "Color(0xFF152528)")
a("Color(0xFF262636)", "Color(0xFF152528)")
a("Color(0xFF262636)", "Color(0xFF152528)")
a("Color(0xFF262636)", "Color(0xFF152528)")
a("Color(0xFF2A2A2A)", "Color(0xFF101C1F)")
a("Color(0xFF2A2A2A)", "Color(0xFF101C1F)")
a("Color(0xFF2A2A2A)", "Color(0xFF101C1F)")
a("Color(0xFF3A3A3A)", "Color(0xFF1B3236)")
a("Color(0xFF3A3A3A)", "Color(0xFF1B3236)")
a("Color(0xFF262626)", "Color(0xFF0F1B1E)")
a("Color(0xFF262626)", "Color(0xFF0F1B1E)")
a("Color(0xFF5A5A7A)", "Color(0xFF27464B)")
a("Color(0xFF5A5A7A)", "Color(0xFF27464B)")
a("Color(0xFF333333)", "Color(0xFF152528)")
a("Color(0xFF333333)", "Color(0xFF152528)")
a(".background(Color(0xFF1E1E1E))", ".background(Color(0xFF0F1B1E))")
a(".background(Color(0xFF4FC3F7))", ".background(Color(0xFF2DD4BF))")
a("""                        color = Color(0xFF4FC3F7),
                        start = Offset""", """                        color = Color(0xFF2DD4BF),
                        start = Offset""")
a("Color(0xFF1A1A2E)", "Color(0xFF0A1214)")
a("Color(0xFFDDDDEE)", "Color(0xFFBFE6E2)")
a("Color(0xFF3A3A5A)", "Color(0xFF1B3236)")

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
