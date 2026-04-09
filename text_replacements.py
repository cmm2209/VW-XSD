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