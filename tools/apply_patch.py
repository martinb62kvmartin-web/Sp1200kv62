import io

PATH = "app/src/main/java/com/example/sp1200/MainActivity.kt"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

if "val noteColor = C_PINK" not in text:
    text = text.replace(
        """                val velRow = vels[selectedPad]""",
        """                val velRow = vels[selectedPad]
                val noteColor = C_PINK""",
        1
    )
    print("Patched: noteColor captured")

text = text.replace(
    "color = C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)),",
    "color = noteColor.copy(alpha = (0.3f + 0.7f * vel / 150f)),",
    1
)
print("Patched: draw uses noteColor")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Done")
