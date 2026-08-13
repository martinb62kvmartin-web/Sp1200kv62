import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(1.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.width(26.dp).height(18.dp)""", """                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(0.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.width(26.dp).height(18.dp)""")

a("""                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .clip(RoundedCornerShape(2.dp))
                                .background(
                                    if (isNote) C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)) else bg
                                )""", """                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .then(
                                    if (isNote) Modifier else Modifier.padding(horizontal = 0.5.dp)
                                )
                                .clip(
                                    RoundedCornerShape(
                                        topStart = if (isStart) 4.dp else 0.dp,
                                        bottomStart = if (isStart) 4.dp else 0.dp,
                                        topEnd = if (isEnd) 4.dp else 0.dp,
                                        bottomEnd = if (isEnd) 4.dp else 0.dp
                                    )
                                )
                                .background(
                                    if (isNote) C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)) else bg
                                )""")

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
