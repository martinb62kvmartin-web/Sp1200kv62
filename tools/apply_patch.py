import io
import os
import sys

P = []
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))

c("""                    v.reverse = padRev[b][type].load(std::memory_order_relaxed);
                    v.pos = v.reverse ? static_cast<double>(v.sample->data.size() - 2) : 0.0;
                    if (v.pos < 0.0) v.pos = 0.0;
                    v.loopEnabled = loopOn[b][type].load(std::memory_order_relaxed);
                    const double sz = static_cast<double>(v.sample->data.size());
                    v.loopStart = loopStartFrac[b][type].load(std::memory_order_relaxed) * sz;
                    v.loopEnd = loopEndFrac[b][type].load(std::memory_order_relaxed) * sz;""", """                    v.reverse = padRev[b][type].load(std::memory_order_relaxed);
                    v.loopEnabled = loopOn[b][type].load(std::memory_order_relaxed);
                    const double sz = static_cast<double>(v.sample->data.size());
                    v.loopStart = loopStartFrac[b][type].load(std::memory_order_relaxed) * sz;
                    v.loopEnd = loopEndFrac[b][type].load(std::memory_order_relaxed) * sz;
                    if (v.loopEnd <= v.loopStart + 1.0) v.loopEnd = sz;
                    v.pos = v.reverse ? (v.loopEnd - 2.0 < 0.0 ? 0.0 : v.loopEnd - 2.0) : v.loopStart;""")

c("""            v.pos -= step;
            if (v.loopEnabled && v.loopEnd > v.loopStart + 1.0 && v.pos <= v.loopStart) {
                v.pos = v.loopEnd - 1.0;
            }
            return out * v.amp;""", """            v.pos -= step;
            if (v.pos <= v.loopStart) {
                if (v.loopEnabled) {
                    v.pos = v.loopEnd - 1.0;
                } else {
                    v.amp = 0.0;
                    return 0.0;
                }
            }
            return out * v.amp;""")

c("""        v.pos += step;

        if (v.loopEnabled && v.loopEnd > v.loopStart + 1.0 && v.pos >= v.loopEnd) {
            v.pos = v.loopStart;
        }

        return out * v.amp;""", """        v.pos += step;

        if (v.pos >= v.loopEnd) {
            if (v.loopEnabled) {
                v.pos = v.loopStart;
            } else {
                v.amp = 0.0;
                return 0.0;
            }
        }

        return out * v.amp;""")

c("""    if (gateMode.load(std::memory_order_relaxed) || loopHeld || sampleHeld) {
        voices[padIndex].gateClosed.store(true, std::memory_order_relaxed);
    }""", """    if (gateMode.load(std::memory_order_relaxed)) {
        voices[padIndex].gateClosed.store(true, std::memory_order_relaxed);
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
