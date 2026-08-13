import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""        LazyColumn(
            modifier = Modifier.fillMaxSize().weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            items(25) { r ->""", """        LazyColumn(
            modifier = Modifier.fillMaxSize().weight(1f),
            verticalArrangement = Arrangement.spacedBy(1.dp)
        ) {
            items(25) { r ->""")

a("""                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(2.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.width(26.dp).height(18.dp)""", """                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(1.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.width(26.dp).height(18.dp)""")

a("""                        val bg = when {
                            playing && step == playhead -> Color(0x33FFFFFF)
                            step % 4 == 0 -> Color(0x14FFFFFF)
                            else -> Color(0x00000000)
                        }
                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .clip(RoundedCornerShape(4.dp))""", """                        val bg = when {
                            playing && step == playhead -> Color(0x44FFFFFF)
                            step % 4 == 0 -> Color(0xFF24303B)
                            r % 2 == 0 -> Color(0xFF1B232C)
                            else -> Color(0xFF161D25)
                        }
                        Box(
                            modifier = Modifier.weight(1f).height(18.dp)
                                .clip(RoundedCornerShape(2.dp))""")

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
