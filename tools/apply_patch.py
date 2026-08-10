import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
""", "")

a("""    val span = range.endInclusive - range.start
    val frac = ((value - range.start) / span).coerceIn(0f, 1f)

    Column(horizontalAlignment = Alignment.CenterHorizontally) {""", """    val span = range.endInclusive - range.start
    val frac = ((value - range.start) / span).coerceIn(0f, 1f)
    val valueNow = rememberUpdatedState(value)
    val knobStart = remember { mutableStateOf(0f) }
    val knobAcc = remember { mutableStateOf(0f) }

    Column(horizontalAlignment = Alignment.CenterHorizontally) {""")

a("""                .pointerInput(range.start, range.endInclusive) {
                    val cur2 = rememberUpdatedState(value)
                    val sv = remember { mutableStateOf(0f) }
                    val ac = remember { mutableStateOf(0f) }
                    detectDragGestures(
                        onDragStart = {
                            sv.value = cur2.value
                            ac.value = 0f
                        }
                    ) { change, drag ->
                        change.consume()
                        ac.value -= drag.y / 200f * span
                        onValueChange((sv.value + ac.value).coerceIn(range))
                    }
                },""", """                .pointerInput(range.start, range.endInclusive) {
                    detectDragGestures(
                        onDragStart = {
                            knobStart.value = valueNow.value
                            knobAcc.value = 0f
                        }
                    ) { change, drag ->
                        change.consume()
                        knobAcc.value -= drag.y / 200f * span
                        onValueChange((knobStart.value + knobAcc.value).coerceIn(range))
                    }
                },""")

a("""                        swing = swing,
                        onSwingChange = onSwingChange,
                        pollTick = pollTick,""", """                        swing = swing,
                        onSwingChange = onSwingChange,
                        stretch = stretchBanks[bank][selectedPad],
                        onStretch = { v ->
                            stretchBanks = stretchBanks.set2(bank, selectedPad, v)
                            nativeSetPadStretch(selectedPad, v)
                        },
                        pollTick = pollTick,""")

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
