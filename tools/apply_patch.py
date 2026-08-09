import io
import os
import sys

# Каждый патч = (путь к файлу, старый текст, новый текст).
# Скрипт ищет старый текст в файле и заменяет на новый.
PATCHES = [
    # Пример (не удаляй, это проверка):
    # ("app/src/main/cpp/audio_engine.h", "старый_текст", "новый_текст"),
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
