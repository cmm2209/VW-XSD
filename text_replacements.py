import json
import pathlib

def load_replacements(path="replacements.json"):
    filepath = pathlib.Path(path)
    if not filepath.is_file():
        raise FileNotFoundError(f"Replacement file '{filepath}' not found.")
    with filepath.open("r", encoding="utf-8") as f:
        replacements = json.load(f)
    return replacements


def apply_replacements(text, replacements):
    for old in sorted(replacements, key=len, reverse=True):
        text = text.replace(old, replacements[old])
    return text

def apply_replacements_with_mapping(text, replacements):
    pairs = sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True)

    chars = [(ch, i) for i, ch in enumerate(text)]

    for old, new in pairs:  # iterate over pairs, not replacements directly
        old_len = len(old)
        i = 0
        new_chars = []
        while i < len(chars):
            segment = ''.join(c for c, _ in chars[i:i+old_len])
            if segment == old:
                original_pos = chars[i][1]
                for new_ch in new:
                    new_chars.append((new_ch, original_pos))
                i += old_len
            else:
                new_chars.append(chars[i])
                i += 1
        chars = new_chars

    replaced_text = ''.join(c for c, _ in chars)
    mapping = [pos for _, pos in chars]
    return replaced_text, mapping