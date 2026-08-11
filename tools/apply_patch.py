import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))

c("""    if (m < 0.0001f) return false;
    const float k = 1.0f / m;
    for (float& v : s->data) v *= k;
    saveSampleToDir(dataDir, b, padIndex, s->data, static_cast<uint32_t>(s->sampleRate));
    return true;""", """    if (m < 0.0001f) return false;
    const float k = 1.0f / m;
    auto dst = std::make_shared<Sample>();
    dst->sampleRate = s->sampleRate;
    dst->data = s->data;
    for (float& v : dst->data) v *= k;
    samples[b][padIndex] = dst;
    saveSampleToDir(dataDir, b, padIndex, dst->data, static_cast<uint32_t>(dst->sampleRate));
    return true;""")

c("""    float st = 0.0f;
    for (float& v : s->data) {
        st += 0.35f * (v - st);
        v = vintage(st);
    }
    saveSampleToDir(dataDir, b, padIndex, s->data, static_cast<uint32_t>(s->sampleRate));
    return true;""", """    auto dst = std::make_shared<Sample>();
    dst->sampleRate = s->sampleRate;
    dst->data = s->data;
    float st = 0.0f;
    for (float& v : dst->data) {
        st += 0.35f * (v - st);
        v = vintage(st);
    }
    samples[b][padIndex] = dst;
    saveSampleToDir(dataDir, b, padIndex, dst->data, static_cast<uint32_t>(dst->sampleRate));
    return true;""")

a("""    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()

        Canvas(""", """    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()
        val vsRef = rememberUpdatedState(viewStart)

        Canvas(""")

a("""                .pointerInput(zoom) {
                    detectTransformGestures { _, pan, zoomChange, _ ->
                        zoom = (zoom * zoomChange).coerceIn(1f, 32f)
                        val vw = 1f / zoom
                        center = (center - pan.x / w * vw).coerceIn(vw / 2f, 1f - vw / 2f)
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
                        center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                    }
                }""")

a("""        val w = constraints.maxWidth.toFloat()

        Canvas(""", """        val w = constraints.maxWidth.toFloat()
        val zoomRef = rememberUpdatedState(zoom)

        Canvas(""")

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
