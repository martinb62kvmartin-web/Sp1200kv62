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
c("""bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate) {
    FILE* f = std::fopen(path.c_str(), "wb");
    if (f == nullptr) {
        return false;
    }

    const uint32_t n = static_cast<uint32_t>(data.size());
    const uint32_t dataSize = n * 2;
    const uint32_t chunkSize = 36 + dataSize;
    const uint16_t one = 1;
    const uint16_t ch = 1;
    const uint16_t bps = 16;
    const uint32_t fmtSize = 16;
    const uint32_t byteRate = rate * 2;
    const uint16_t blockAlign = 2;
""", """bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate, int channels) {
    FILE* f = std::fopen(path.c_str(), "wb");
    if (f == nullptr) {
        return false;
    }

    const uint16_t ch = static_cast<uint16_t>(channels > 0 ? channels : 1);
    const uint32_t n = static_cast<uint32_t>(data.size());
    const uint32_t dataSize = n * 2;
    const uint32_t chunkSize = 36 + dataSize;
    const uint16_t one = 1;
    const uint16_t bps = 16;
    const uint32_t fmtSize = 16;
    const uint32_t byteRate = rate * ch;
    const uint16_t blockAlign = static_cast<uint16_t>(2 * ch);
""")
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
a("""            SmallButton("LIB", view == 4) { onViewChange(4) }
        }""", """            SmallButton("LIB", view == 4) { onViewChange(4) }
            SmallButton("MIX", view == 6) { onViewChange(6) }
        }""")
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
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {""", """    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {""")
a("""            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "RELEASE ${padReleaseMs.toInt()} ms",""", """            Column(modifier = Modifier.weight(1f)) {
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
                    text = "RELEASE ${padReleaseMs.toInt()} ms",""")
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

def main():
    for path, old, new in P:
        if not os.path.exists(path):
            print("ERROR: missing file", path)
            sys.exit(1)

        with io.open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if old not in text:
            print("Skipped (not found or already applied):", old[:60].replace("\n", " "))
            continue

        text = text.replace(old, new, 1)

        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)

        print("Patched:", old[:60].replace("\n", " "))

main()
