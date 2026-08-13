import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""                            .pointerInput(on) {
                                if (!on) {
                                    detectTapGestures(onTap = { onToggleStep(pad, step) })
                                } else {
                                    var moved = false
                                    detectDragGestures(
                                        onDragStart = { moved = false },
                                        onDragEnd = { if (!moved) onToggleStep(pad, step) }
                                    ) { change, drag ->
                                        change.consume()
                                        moved = true
                                        onVel(pad, step, -drag.y / 2f)
                                    }
                                }
                            }""", """                            .pointerInput(on) {
                                detectTapGestures(onTap = { onToggleStep(pad, step) })
                            }
                            .pointerInput(on) {
                                if (on) {
                                    detectDragGestures { change, drag ->
                                        change.consume()
                                        onVel(pad, step, -drag.y / 2f)
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
