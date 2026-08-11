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

h("""    void setPadStretch(int padIndex, int steps);""", """    void setPadStretch(int padIndex, int steps);

    bool normalizePad(int padIndex);
    bool trimSilencePad(int padIndex);
    bool makeMonoPad(int padIndex);
    bool bouncePad(int padIndex);
    int autoChop(int padIndex);
    int splitStems(int padIndex);""")

c("""void AudioEngine::setPadStretch(int padIndex, int steps) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    if (steps < 0) steps = 0;
    if (steps > 256) steps = 256;
    const int b = currentBank.load(std::memory_order_relaxed);
    padStretch[b][padIndex].store(steps, std::memory_order_relaxed);
}""", """void AudioEngine::setPadStretch(int padIndex, int steps) {
    if (padIndex < 0 || padIndex >= kNumPads) return;
    if (steps < 0) steps = 0;
    if (steps > 256) steps = 256;
    const int b = currentBank.load(std::memory_order_relaxed);
    padStretch[b][padIndex].store(steps, std::memory_order_relaxed);
}

static void saveSampleToDir(const std::string& dir, int b, int p, const std::vector<float>& data, uint32_t rate) {
    if (dir.empty() || data.empty()) return;
    const std::string path = dir + "/b" + std::to_string(b) + "_p" + std::to_string(p) + ".wav";
    writeWavFile(path, data, rate, 1);
}

bool AudioEngine::normalizePad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return false;
    float m = 0.0f;
    for (float v : s->data) { const float a = v < 0 ? -v : v; if (a > m) m = a; }
    if (m < 0.0001f) return false;
    const float k = 1.0f / m;
    for (float& v : s->data) v *= k;
    saveSampleToDir(dataDir, b, padIndex, s->data, static_cast<uint32_t>(s->sampleRate));
    return true;
}

bool AudioEngine::trimSilencePad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return false;
    const float th = 0.02f;
    size_t i0 = 0, i1 = s->data.size();
    while (i0 < i1) { const float a = s->data[i0] < 0 ? -s->data[i0] : s->data[i0]; if (a > th) break; i0++; }
    while (i1 > i0) { const float a = s->data[i1 - 1] < 0 ? -s->data[i1 - 1] : s->data[i1 - 1]; if (a > th) break; i1--; }
    if (i1 <= i0 || (i0 == 0 && i1 == s->data.size())) return false;
    std::vector<float> cut(s->data.begin() + i0, s->data.begin() + i1);
    auto dst = std::make_shared<Sample>();
    dst->sampleRate = s->sampleRate;
    dst->data = std::move(cut);
    samples[b][padIndex] = dst;
    saveSampleToDir(dataDir, b, padIndex, dst->data, static_cast<uint32_t>(dst->sampleRate));
    return true;
}

bool AudioEngine::makeMonoPad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    return samples[b][padIndex] != nullptr;
}

bool AudioEngine::bouncePad(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return false;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return false;
    float st = 0.0f;
    for (float& v : s->data) {
        st += 0.35f * (v - st);
        v = vintage(st);
    }
    saveSampleToDir(dataDir, b, padIndex, s->data, static_cast<uint32_t>(s->sampleRate));
    return true;
}

int AudioEngine::autoChop(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return 0;
    const int b = currentBank.load(std::memory_order_relaxed);
    std::shared_ptr<const Sample> src;
    {
        std::lock_guard<std::mutex> lock(sampleMutex);
        src = samples[b][padIndex];
        if (!src || src->data.empty()) return 0;
    }
    const size_t n = src->data.size();
    const int slices = 16;
    for (int p = 0; p < slices; ++p) {
        size_t a = n * static_cast<size_t>(p) / slices;
        size_t z = n * static_cast<size_t>(p + 1) / slices;
        if (z <= a) z = a + 1;
        auto dst = std::make_shared<Sample>();
        dst->sampleRate = src->sampleRate;
        dst->data.assign(src->data.begin() + a, src->data.begin() + z);
        {
            std::lock_guard<std::mutex> lock(sampleMutex);
            samples[b][p] = dst;
        }
        saveSampleToDir(dataDir, b, p, dst->data, static_cast<uint32_t>(dst->sampleRate));
    }
    return slices;
}

int AudioEngine::splitStems(int padIndex) {
    if (padIndex < 0 || padIndex >= kNumPads) return 0;
    const int b = currentBank.load(std::memory_order_relaxed);
    const int p2 = (padIndex + 1) % kNumPads;
    std::lock_guard<std::mutex> lock(sampleMutex);
    auto s = samples[b][padIndex];
    if (!s || s->data.empty()) return 0;
    std::vector<float> low(s->data.size()), high(s->data.size());
    float lp = 0.0f;
    const float k = 0.15f;
    for (size_t i = 0; i < s->data.size(); ++i) {
        lp += k * (s->data[i] - lp);
        low[i] = lp;
        high[i] = s->data[i] - lp;
    }
    auto dLow = std::make_shared<Sample>();
    dLow->sampleRate = s->sampleRate;
    dLow->data = std::move(low);
    auto dHigh = std::make_shared<Sample>();
    dHigh->sampleRate = s->sampleRate;
    dHigh->data = std::move(high);
    samples[b][padIndex] = dLow;
    samples[b][p2] = dHigh;
    saveSampleToDir(dataDir, b, padIndex, dLow->data, static_cast<uint32_t>(dLow->sampleRate));
    saveSampleToDir(dataDir, b, p2, dHigh->data, static_cast<uint32_t>(dHigh->sampleRate));
    return 2;
}""")

j("""JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadStretch(JNIEnv*, jobject, jint padIndex, jint steps) {
    if (engine != nullptr) {
        engine->setPadStretch(padIndex, static_cast<int>(steps));
    }
}""", """JNIEXPORT void JNICALL
Java_com_example_sp1200_MainActivity_nativeSetPadStretch(JNIEnv*, jobject, jint padIndex, jint steps) {
    if (engine != nullptr) {
        engine->setPadStretch(padIndex, static_cast<int>(steps));
    }
}

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeNormalizePad(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) return JNI_FALSE;
    return engine->normalizePad(padIndex) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeTrimSilencePad(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) return JNI_FALSE;
    return engine->trimSilencePad(padIndex) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeMakeMonoPad(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) return JNI_FALSE;
    return engine->makeMonoPad(padIndex) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jboolean JNICALL
Java_com_example_sp1200_MainActivity_nativeBouncePad(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) return JNI_FALSE;
    return engine->bouncePad(padIndex) ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT jint JNICALL
Java_com_example_sp1200_MainActivity_nativeAutoChop(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) return 0;
    return static_cast<jint>(engine->autoChop(padIndex));
}

JNIEXPORT jint JNICALL
Java_com_example_sp1200_MainActivity_nativeSplitStems(JNIEnv*, jobject, jint padIndex) {
    if (engine == nullptr) return 0;
    return static_cast<jint>(engine->splitStems(padIndex));
}""")

a("""    private external fun nativeSetPadStretch(padIndex: Int, steps: Int)""", """    private external fun nativeSetPadStretch(padIndex: Int, steps: Int)
    private external fun nativeNormalizePad(padIndex: Int): Boolean
    private external fun nativeTrimSilencePad(padIndex: Int): Boolean
    private external fun nativeMakeMonoPad(padIndex: Int): Boolean
    private external fun nativeBouncePad(padIndex: Int): Boolean
    private external fun nativeAutoChop(padIndex: Int): Int
    private external fun nativeSplitStems(padIndex: Int): Int""")

a("""    private var toneBanks by mutableStateOf(List(4) { List(16) { 50f } })""", """    private var toneBanks by mutableStateOf(List(4) { List(16) { 50f } })
    private var padLabels by mutableStateOf(List(4) { List(16) { "" } })""")

a("""                val toneArr = JSONArray()
                for (p in 0 until 16) {
                    toneArr.put(toneBanks[b][p])
                }
                bo.put("tone", toneArr)""", """                val toneArr = JSONArray()
                for (p in 0 until 16) {
                    toneArr.put(toneBanks[b][p])
                }
                bo.put("tone", toneArr)

                val labArr = JSONArray()
                for (p in 0 until 16) {
                    labArr.put(padLabels[b][p])
                }
                bo.put("labels", labArr)""")

a("""                bo.optJSONArray("tone")?.let { ta ->
                    val rows = toneBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ta.length())) {
                        rows[p] = ta.optDouble(p, 50.0).toFloat()
                    }
                    newTone[b] = rows
                }""", """                bo.optJSONArray("tone")?.let { ta ->
                    val rows = toneBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ta.length())) {
                        rows[p] = ta.optDouble(p, 50.0).toFloat()
                    }
                    newTone[b] = rows
                }

                bo.optJSONArray("labels")?.let { la2 ->
                    val rows = padLabels[b].toMutableList()
                    for (p in 0 until minOf(16, la2.length())) {
                        rows[p] = la2.optString(p, "")
                    }
                    newLabels[b] = rows
                }""")

a("""            val newTone = toneBanks.toMutableList()""", """            val newTone = toneBanks.toMutableList()
            val newLabels = padLabels.toMutableList()""")

a("""            toneBanks = newTone""", """            toneBanks = newTone
            padLabels = newLabels""")

a("""                        onTool = { name ->
                            Toast.makeText(this, "$name: soon", Toast.LENGTH_SHORT).show()
                        },""", """                        onTool = { name ->
                            when (name) {
                                "NORMALIZE" -> {
                                    nativeNormalizePad(selectedPad)
                                    peaks = nativeGetPeaks(selectedPad, 200)
                                    refreshPadPeaks()
                                }
                                "TRIM SILENCE" -> {
                                    nativeTrimSilencePad(selectedPad)
                                    peaks = nativeGetPeaks(selectedPad, 200)
                                    refreshPadPeaks()
                                }
                                "MAKE MONO" -> {
                                    nativeMakeMonoPad(selectedPad)
                                    Toast.makeText(this, "Mono OK", Toast.LENGTH_SHORT).show()
                                }
                                "BOUNCE" -> {
                                    nativeBouncePad(selectedPad)
                                    peaks = nativeGetPeaks(selectedPad, 200)
                                    refreshPadPeaks()
                                    Toast.makeText(this, "Bounced 12bit", Toast.LENGTH_SHORT).show()
                                }
                                "AUTO-CHOP" -> {
                                    val n = nativeAutoChop(selectedPad)
                                    if (n > 0) {
                                        loadedBanks = loadedBanks.toMutableList().also {
                                            it[bank] = (0 until 16).toSet()
                                        }
                                        refreshPadPeaks()
                                        Toast.makeText(this, "Chopped to 16 pads", Toast.LENGTH_SHORT).show()
                                    }
                                }
                                "SPLIT STEMS" -> {
                                    val n = nativeSplitStems(selectedPad)
                                    if (n > 0) {
                                        loadedBanks = loadedBanks.toMutableList().also {
                                            it[bank] = it[bank] + selectedPad + ((selectedPad + 1) % 16)
                                        }
                                        refreshPadPeaks()
                                        Toast.makeText(this, "Low/High split done", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            }
                        },
                        labels = padLabels[bank],
                        onLabel = { text ->
                            padLabels = padLabels.set2(bank, selectedPad, text)
                        },""")

a("""    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit
) {""", """    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit,
    labels: List<String>,
    onLabel: (String) -> Unit
) {""")

a("""                onTool = onTool,
                onPreviewPad = onPreviewPad""", """                onTool = onTool,
                onPreviewPad = onPreviewPad,
                labels = labels,
                onLabel = onLabel""")

a("""    var showTools by remember { mutableStateOf(false) }""", """    var showTools by remember { mutableStateOf(false) }
    var showLabel by remember { mutableStateOf(false) }""")

a("""    var zoom by remember { mutableStateOf(1f) }
    var center by remember { mutableStateOf(0.5f) }

    val viewW = 1f / zoom
    var viewStart = center - viewW / 2f
    if (viewStart < 0f) viewStart = 0f
    if (viewStart > 1f - viewW) viewStart = 1f - viewW

    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()
        val zoomRef = rememberUpdatedState(zoom)
        val centerRef = rememberUpdatedState(center)""", """    var zoom by remember { mutableStateOf(1f) }
    var viewStart by remember { mutableStateOf(0f) }

    val viewW = 1f / zoom

    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()
        val zoomRef = rememberUpdatedState(zoom)
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
                        viewStart = ns.coerceIn(0f, 1f - newVw)
                    }
                }""")

a("""                                    detectTapGestures(
                                        onPress = {
                                            onPadDown(index)
                                            tryAwaitRelease()
                                            onPadUp(index)
                                        }
                                    )""", """                                    detectTapGestures(
                                        onPress = {
                                            onSelectPad(index)
                                            onPadDown(index)
                                            tryAwaitRelease()
                                            onPadUp(index)
                                        }
                                    )""")

a("""                            Text(
                                text = "${index + 1}",
                                color = Color.White,
                                fontSize = 9.sp,
                                modifier = Modifier
                                    .align(Alignment.TopStart)
                                    .padding(4.dp)
                            )""", """                            Text(
                                text = labels[index].ifEmpty { "${index + 1}" },
                                color = Color.White,
                                fontSize = 9.sp,
                                maxLines = 1,
                                modifier = Modifier
                                    .align(Alignment.TopStart)
                                    .padding(4.dp)
                            )""")

a("""                        KBtn(item, false, {
                            showTools = false
                            when (item) {
                                "CROP" -> onTrim()
                                "EXPORT" -> onExport()
                                else -> onTool(item)
                            }
                        }, Modifier.fillMaxWidth().height(40.dp))""", """                        KBtn(item, false, {
                            showTools = false
                            when (item) {
                                "CROP" -> onTrim()
                                "EXPORT" -> onExport()
                                "LABEL" -> showLabel = true
                                else -> onTool(item)
                            }
                        }, Modifier.fillMaxWidth().height(40.dp))""")

a("""        if (showTools) {""", """        if (showLabel) {
            Dialog(onDismissRequest = { showLabel = false }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF3A1220))
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("LABEL", color = Color.White, fontWeight = FontWeight.Bold)
                    var txt by remember { mutableStateOf(labels[selectedPad]) }
                    TextField(
                        value = txt,
                        onValueChange = { txt = it },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    KBtn("OK", false, {
                        onLabel(txt)
                        showLabel = false
                    }, Modifier.fillMaxWidth().height(42.dp))
                }
            }
        }

        if (showTools) {""")

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
