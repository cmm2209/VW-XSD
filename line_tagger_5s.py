#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
line_tagger.py

Appends line numbers every fifth line to a hard-return-separated *.txt* file.

Usage (PowerShell, CMD, Bash, etc.):
    python line_tagger.py <base_name> <first line number>

Example:
    python line_tagger.py myfile 1  # reads myfile.txt, writes myfile-numbered.txt starting with line 1
"""

import sys
import pathlib      


def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename and first line number from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 3:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name>", file=sys.stderr)
        sys.exit(1)

    base_name = sys.argv[1]
    initial_line = sys.argv[2]
    

    # Build full input / output paths (same folder as the script is run from)
    txt_path = pathlib.Path(f"{base_name}.txt")
    saved_path = pathlib.Path(f"{base_name}-numbered.txt")

    if not txt_path.is_file():
        print(f"Error: '{txt_path}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file 
    # ------------------------------------------------------------------
    with txt_path.open('r', encoding='utf-8') as file:
        content = file.read()
        lines = content.split("\n")
    
    printed_lines = []

    for line in lines:
        if int(initial_line) % 5 != 0:
            printed_lines.append(line)
        if int(initial_line) % 5 == 0:
            printed_lines.append(f'{initial_line} {line}')
        initial_line=int(initial_line)+1

    # Save the annotated lines to the output file
    with open(saved_path, 'w', encoding='utf-8') as file:
        for line in printed_lines:
            file.write(line + '\n')

if __name__ == '__main__':
    main()