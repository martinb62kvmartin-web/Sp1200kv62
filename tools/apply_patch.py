import io
import os
import sys

PATCHES = [
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        "color = Color(0xFF141428)",
        "color = Color(0xFF0C1416)"
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        colors = ButtonDefaults.buttonColors(
            containerColor = if (active) Color(0xFFE91E5A) else Color(0xFF262636)
        ),""",
        """        colors = ButtonDefaults.buttonColors(
            containerColor = if (active) Color(0xFF2DD4BF) else Color(0xFF152528)
        ),"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """        Text(
            text = label,
            color = Color.White,
            fontSize = 10.sp,
            maxLines = 1
        )""",
        """        Text(
            text = label,
            color = if (active) Color(0xFF06201D) else Color(0xFFBFE6E2),
            fontSize = 10.sp,
            maxLines = 1
        )"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            text = "SP-1200 v2",
            style = MaterialTheme.typography.titleLarge,
            color = Color(0xFF4FC3F7)""",
        """            text = "SP-1200 v2",
            style = MaterialTheme.typography.titleLarge,
            color = Color(0xFF2DD4BF)"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """fun padColor(index: Int): Color = when (index) {
    0 -> Color(0xFFE53935)
    1 -> Color(0xFFFB8C00)
    2 -> Color(0xFFFDD835)
    3 -> Color(0xFF43A047)
    4 -> Color(0xFF1E88E5)
    5 -> Color(0xFF8E24AA)
    6 -> Color(0xFF00ACC1)
    else -> Color(0xFF546E7A)
}""",
        """fun padColor(index: Int): Color = when (index) {
    0 -> Color(0xFF2DD4BF)
    1 -> Color(0xFF4CC3E0)
    2 -> Color(0xFF7FA8F0)
    3 -> Color(0xFFA78BFA)
    4 -> Color(0xFFE07FA0)
    5 -> Color(0xFFF0A45C)
    6 -> Color(0xFFB8E05C)
    7 -> Color(0xFF5EEAD4)
    8 -> Color(0xFF38BDF8)
    9 -> Color(0xFF818CF8)
    10 -> Color(0xFFC084FC)
    11 -> Color(0xFFF472B6)
    12 -> Color(0xFFFBBF24)
    13 -> Color(0xFFA3E635)
    14 -> Color(0xFF34D399)
    else -> Color(0xFF22D3EE)
}"""
    ),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFFE91E5A)", "Color(0xFF2DD4BF)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFFE91E5A)", "Color(0xFF2DD4BF)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFFE91E5A)", "Color(0xFF2DD4BF)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF262636)", "Color(0xFF152528)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF262636)", "Color(0xFF152528)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF262636)", "Color(0xFF152528)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF262636)", "Color(0xFF152528)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF2A2A2A)", "Color(0xFF101C1F)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF2A2A2A)", "Color(0xFF101C1F)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF2A2A2A)", "Color(0xFF101C1F)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF3A3A3A)", "Color(0xFF1B3236)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF3A3A3A)", "Color(0xFF1B3236)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF262626)", "Color(0xFF0F1B1E)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF262626)", "Color(0xFF0F1B1E)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF5A5A7A)", "Color(0xFF27464B)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF5A5A7A)", "Color(0xFF27464B)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF333333)", "Color(0xFF152528)"),
    ("app/src/main/java/com/example/sp1200/MainActivity.kt", "Color(0xFF333333)", "Color(0xFF152528)"),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        ".background(Color(0xFF1E1E1E))",
        ".background(Color(0xFF0F1B1E))"
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        ".background(Color(0xFF4FC3F7))",
        ".background(Color(0xFF2DD4BF))"
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                        color = Color(0xFF4FC3F7),
                        start = Offset""",
        """                        color = Color(0xFF2DD4BF),
                        start = Offset"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """                text = "MASTER",
                color = Color(0xFF4FC3F7),""",
        """                text = "MASTER",
                color = Color(0xFF2DD4BF),"""
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        "Color(0xFF1A1A2E)",
        "Color(0xFF0A1214)"
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        "Color(0xFFDDDDEE)",
        "Color(0xFFBFE6E2)"
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        "Color(0xFF3A3A5A)",
        "Color(0xFF1B3236)"
    ),
    (
        "app/src/main/java/com/example/sp1200/MainActivity.kt",
        """            Text(
                text = "PLAY (hold)",
                color = Color.Black,""",
        """            Text(
                text = "PLAY (hold)",
                color = Color(0xFF06201D),"""
    ),
]

def main():
    if not PATCHES:
        print("No patches to apply.")
        return

    for path, old, new in PATCHES:
        if not os.path.exists(path):
            print("ERROR: missing file", path)
            sys.exit(1)

        with io.open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if old not in text:
            print("ERROR: pattern not found in", path)
            print("PATTERN:", old[:120])
            sys.exit(1)

        text = text.replace(old, new, 1)

        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)

        print("Patched:", path)

main()
