import io

PATH = "app/src/main/java/com/example/sp1200/MainActivity.kt"

with io.open(PATH, "r", encoding="utf-8") as f:
    text = f.read()

old = """                            if (isStart) {
                                Box(
                                    modifier = Modifier.fillMaxHeight().width(3.dp)
                                        .background(Color.White)
                                )
                            }
                        }
                }"""

new = """                            if (isStart) {
                                Box(
                                    modifier = Modifier.fillMaxHeight().width(3.dp)
                                        .background(Color.White)
                                )
                            }
                        }
                    }
                }"""

if old in text:
    text = text.replace(old, new, 1)
    print("Patched: brace restored")
else:
    print("Skipped: brace anchor")

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Done")
