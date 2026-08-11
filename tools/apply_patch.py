import io
import os
import sys

P = []
def a(old, new):
    P.append(("app/src/main/java/com/example/sp1200/MainActivity.kt", old, new))

a("""        LazyVerticalGrid(
            columns = GridCells.Fixed(4),
            modifier = Modifier.height(520.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            items(16) { index ->
                val has = loadedPads.contains(index)
                val flash = flashes[index]
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .background(
                            if (index == selectedPad) C_CYAN
                            else if (has) C_PINK.copy(alpha = 0.75f)
                            else C_PINK.copy(alpha = 0.45f)
                        )
                        .pointerInput(index) {
                            detectTapGestures(
                                onPress = {
                                    onPadDown(index)
                                    tryAwaitRelease()
                                    onPadUp(index)
                                },
                                onLongPress = { onPadLongPress(index) }
                            )
                        }
                ) {
                    if (has) {
                        Wave(
                            peaks = padPeaks[index],
                            bg = Color.Transparent,
                            line = if (index == selectedPad) Color(0xFF083A46) else Color(0x66101418),
                            shake = if (flash) pollTick else 0,
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(6.dp)
                        )
                    }
                    if (index == selectedPad) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color.Transparent)
                        )
                    }
                    Text(
                        text = "${index + 1}",
                        color = Color.White,
                        fontSize = 9.sp,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(4.dp)
                    )
                }
            }
        }""", """        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            for (row in 0 until 4) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    for (col in 0 until 4) {
                        val index = row * 4 + col
                        val has = loadedPads.contains(index)
                        val flash = flashes[index]
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .aspectRatio(1f)
                                .clip(RoundedCornerShape(12.dp))
                                .background(
                                    if (index == selectedPad) C_CYAN
                                    else if (has) C_PINK.copy(alpha = 0.75f)
                                    else C_PINK.copy(alpha = 0.45f)
                                )
                                .pointerInput(index) {
                                    detectTapGestures(
                                        onPress = {
                                            onPadDown(index)
                                            tryAwaitRelease()
                                            onPadUp(index)
                                        }
                                    )
                                }
                        ) {
                            if (has) {
                                Wave(
                                    peaks = padPeaks[index],
                                    bg = Color.Transparent,
                                    line = if (index == selectedPad) Color(0xFF083A46) else Color(0x66101418),
                                    shake = if (flash) pollTick else 0,
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .padding(6.dp)
                                )
                            }
                            Text(
                                text = "${index + 1}",
                                color = Color.White,
                                fontSize = 9.sp,
                                modifier = Modifier
                                    .align(Alignment.TopStart)
                                    .padding(4.dp)
                            )
                        }
                    }
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
