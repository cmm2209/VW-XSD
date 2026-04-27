import sys
import pathlib


def remove_characters(file_path):
    # Characters to remove
    chars_to_remove = '.,?!;:<>«»'

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Remove specified characters using translate
    translator = str.maketrans('', '', chars_to_remove)
    content = content.translate(translator)

    # Save the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

    print(f"File '{file_path}' has been processed and saved successfully.")


def main():

    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <folder_path>", file=sys.stderr)
        sys.exit(1)

    folder_path = pathlib.Path(sys.argv[1])

    if not folder_path.is_dir():
        print(f"Error: '{folder_path}' is not a valid directory.", file=sys.stderr)
        sys.exit(2)

    txt_files = list(folder_path.glob('*.txt'))

    if not txt_files:
        print(f"No .txt files found in '{folder_path}'.")
        sys.exit(0)

    for txt_file in txt_files:
        remove_characters(txt_file)

    print(f"\nDone. {len(txt_files)} file(s) processed.")


if __name__ == '__main__':
    main()