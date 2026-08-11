import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""        val zoomRef = rememberUpdatedState(zoom)""", """        val zoomRef = rememberUpdatedState(zoom)
        val lineColor = C_CYAN""")

a("""                    drawLine(C_CYAN, Offset(x, h / 2 - p + off), Offset(x, h / 2 + p + off), width / bars)""", """                    drawLine(lineColor, Offset(x, h / 2 - p + off), Offset(x, h / 2 + p + off), width / bars)""")

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
