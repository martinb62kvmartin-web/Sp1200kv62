import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))
def c(old, new):
    P.append(("app/src/main/cpp/audio_engine.cpp", old, new))

a("""                    pushPadParams(selectedPad)
                }
            )""", """                    pushPadParams(selectedPad)
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
            )""")

a("""                    pushPadParams(selectedPad)
                },
                padVol = volBanks[selectedPad],""", """                    pushPadParams(selectedPad)
                },
                padVol = volBanks[selectedPad],""")

c("""            capBuf.insert(capBuf.end(), output, output + numFrames);""", """            capBuf.insert(capBuf.end(), output, output + numFrames * 2);""")

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
