#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
line_tagger_30s.py

Appends line numbers every fifth line, restarting every 30 lines, to a hard-return-separated *.txt* file.

Usage (PowerShell, CMD, Bash, etc.):
    python line_tagger.py <base_name>

Example:
    python line_tagger_30s.py myfile # reads myfile.txt, writes myfile-numbered.txt
"""

import sys
import pathlib      


def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename and first line number from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name>", file=sys.stderr)
        sys.exit(1)

    base_name = sys.argv[1]
        

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
    initial_page = 2
    initial_line = 1

    for line in lines:
        if int(initial_line) % 5 != 0:
            printed_lines.append(line)
            initial_line=int(initial_line)+1
        elif int(initial_line) % 30 == 0:
            printed_lines.append(f'30 {line} \n@#{initial_page}')    
            initial_line = 1
            initial_page = initial_page +1
        elif int(initial_line) % 5 == 0:
            printed_lines.append(f'{initial_line} {line}')
            initial_line=int(initial_line)+1

    # Save the annotated lines to the output file
    with open(saved_path, 'w', encoding='utf-8') as file:
        for line in printed_lines:
            file.write(line + '\n')

if __name__ == '__main__':
    main()