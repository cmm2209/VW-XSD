from text_replacements import load_replacements, apply_replacements 

import sys
import pathlib
import unicodedata


def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name>", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file
    # ------------------------------------------------------------------
    with open(sys.argv[1], 'r', encoding='utf-8') as file:
        original_lines = file.readlines()
        normed_lines = [unicodedata.normalize("NFC", line) for line in original_lines]
    

    # ------------------------------------------------------------------
    # 7️⃣  Clean up the text
    # ------------------------------------------------------------------
    cleaned_lines = []
    for line in normed_lines:
        cleaned_lines.append(line)
    
    # Replace special characters using custom replacements list
    replacements = load_replacements("replacements.json")
    cleaned_lines = [apply_replacements(line, replacements) for line in cleaned_lines]
    
    with open(sys.argv[1], 'w', encoding='utf-8') as file:
        file.write("".join(cleaned_lines))


if __name__ == '__main__':
    main()