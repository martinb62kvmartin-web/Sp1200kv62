import io
import os
import sys

PATCHES = [
    ("app/src/main/cpp/audio_engine.h", "    static constexpr int kNumPads = 8;", "    static constexpr int kNumPads = 16;"),
    (
        "app/src/main/cpp/audio_engine.h",
        """    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);
""",
        """    void setPadParams(int padIndex, double pitchSemi, double attack,
                      double decay, double sustain, double release);

    void setPadVol(int padIndex, float vol);
    void setPadPan(int padIndex, float pan);
    void setMasterVol(float vol);
    void setMasterPan(float pan);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.h",
        """    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};
""",
        """    std::array<std::atomic<bool>, kNumPads> mutes{};
    std::array<std::atomic<bool>, kNumPads> solos{};
    std::atomic<int> soloCount{0};

    std::array<std::atomic<float>, kNumPads> padVol{};
    std::array<std::atomic<float>, kNumPads> padPan{};
    std::atomic<float> masterVol{1.0f};
    std::atomic<float> masterPan{0.0f};
"""
    ),
    (
        "app/src/main/cpp/audio_engine.h",
        """    float lpState = 0.0f;
""",
        """    float lpStateL = 0.0f;
    float lpStateR = 0.0f;
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    for (auto& s : solos) s.store(false);
""",
        """    for (auto& s : solos) s.store(false);
    for (auto& v : padVol) v.store(1.0f);
    for (auto& p : padPan) p.store(0.0f);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """void AudioEngine::setGateMode(bool enabled) {""",
        """void AudioEngine::setPadVol(int padIndex, float vol) {
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

void AudioEngine::setGateMode(bool enabled) {"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate) {
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
""",
        """bool writeWavFile(const std::string& path, const std::vector<float>& data, uint32_t rate, int channels) {
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
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        writeWavFile(path, sample->data, static_cast<uint32_t>(rate));""",
        """        writeWavFile(path, sample->data, static_cast<uint32_t>(rate), 1);"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate));""",
        """        writeWavFile(path, dst->data, static_cast<uint32_t>(dst->sampleRate), 1);"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate));""",
        """    const bool ok = writeWavFile(path, data, static_cast<uint32_t>(sampleRate), 2);"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(1);
""",
        """    builder.setDirection(oboe::Direction::Output);
    builder.setPerformanceMode(oboe::PerformanceMode::LowLatency);
    builder.setFormat(oboe::AudioFormat::Float);
    builder.setChannelCount(2);
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        float mix = 0.0f;
""",
        """        float mixL = 0.0f;
        float mixR = 0.0f;
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """            mix += static_cast<float>(renderVoice(v) * v.envLevel);
""",
        """            {
                const int pIdx = v.padIndex;
                const float vol = padVol[pIdx].load(std::memory_order_relaxed);
                const float pan = padPan[pIdx].load(std::memory_order_relaxed);
                const float gl = vol * (pan < 0.0f ? 1.0f : 1.0f - pan);
                const float gr = vol * (pan > 0.0f ? 1.0f : 1.0f + pan);
                const float m = static_cast<float>(renderVoice(v) * v.envLevel);
                mixL += m * gl;
                mixR += m * gr;
            }
"""
    ),
    (
        "app/src/main/cpp/audio_engine.cpp",
        """        if (mix > 1.0f) {
            mix = 1.0f;
        } else if (mix < -1.0f) {
            mix = -1.0f;
        }

        if (crunch) {
            lpState += 0.35f * (mix - lpState);
            mix = vintage(lpState);
        }

        output[frame] = mix * 0.8f;
""",
        """        const float mv = masterVol.load(std::memory_order_relaxed);
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
"""
    ),
    (
        "app/src/main/cpp/native-lib.cpp",
        """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {""",
        """JNIEXPORT void JNICALL
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
Java_com_example_sp1200_MainActivity_nativeSetMidiMode(JNIEnv*, jobject, jint mode) {"""
    ),
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
                        .background(if (mutes[pad]) Color(0xFFB71C1C) else Color(0xFF152528))""",
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
                        .background(if (mutes[pad]) Color(0xFFB71C1C) else Color(0xFF152528))"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        for (pad in 0 until 8) {
                val bg = when {
                    armedFile != null -> Color(0xFF1B3236)""",
        """        for (pad in 0 until 16) {
                val bg = when {
                    armedFile != null -> Color(0xFF1B3236)"""
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
                        .background(Color(0xFF152528))
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
                        .background(Color(0xFF152528))
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
}"""
    ),
]

def main():
    if not PATCHES:
        print("No patches to apply.")
        return

    for item in PATCHES:
        optional = len(item) == 4 and item[3]
        path, old, new = item[0], item[1], item[2]

        if not os.path.exists(path):
            print("ERROR: missing file", path)
            sys.exit(1)

        with io.open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if old not in text:
            if optional:
                print("Skipped (not found):", old[:60].replace("\n", " "))
                continue
            print("ERROR: pattern not found in", path)
            print("PATTERN:", old[:120])
            sys.exit(1)

        text = text.replace(old, new, 1)

        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)

        print("Patched:", old[:60].replace("\n", " "))

main()
