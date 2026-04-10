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


def main():
    # Load replacements
    print("Loading replacements from replacements.json...")
    replacements = load_replacements()
    print(f"Loaded {len(replacements)} replacement rules.")
    
    # Read the input file
    print("Reading MHDtexts.txt...")
    with open("MHDtexts.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    print(f"File size: {len(text):,} characters")
    
    # Apply replacements
    print("Applying replacements...")
    modified_text = apply_replacements(text, replacements)
    
    # Write the output
    print("Writing to MHDtexts.txt...")
    with open("MHDtexts.txt", "w", encoding="utf-8") as f:
        f.write(modified_text)
    
    print(f"Done! Modified file size: {len(modified_text):,} characters")
    print(f"Size change: {len(modified_text) - len(text):+,} characters")


if __name__ == "__main__":
    main()