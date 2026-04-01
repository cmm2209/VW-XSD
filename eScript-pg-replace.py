#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
line_tagger.py

Converts eScriptorium's page divisions to re-numbered lines beginning with #.

Usage (PowerShell, CMD, Bash, etc.):
    python eScript-pg-replace.py <base_name> <first page number>

Example:
    python eScript-pg-replace.py myfile 1  # reads myfile.txt, writes myfile-numbered.txt starting with page 1
"""

import sys
import pathlib
import re

def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename and first page number from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 3:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name> <first_page_number>", file=sys.stderr)
        sys.exit(1)

    base_name = sys.argv[1]
    initial_page = sys.argv[2]

    # Build full input / output paths (same folder as the script is run from)
    txt_path = pathlib.Path(f"{base_name}.txt")
    txt_num_path = pathlib.Path(f"{base_name}-numbered.txt")

    if not txt_path.is_file():
        print(f"Error: '{txt_path}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file 
    # ------------------------------------------------------------------
    with txt_path.open('r', encoding='utf-8') as file:
        content = file.read()
    
    # ------------------------------------------------------------------
    # 3️⃣  Process the content - replace page divisions with numbered markers
    # ------------------------------------------------------------------
    lines = content.split("\n")
    output_lines = []
    
    # Convert starting page number to integer
    current_page = int(initial_page)
    
    # Regex pattern to match page division lines
    # Matches lines with 15+ dashes containing "Element X"
    page_division_pattern = r'^-{15,}.*Element \d+.*$'
    
    for line in lines:
        # Check if this is a page division line
        if re.match(page_division_pattern, line):
            # Replace with page marker and increment
            output_lines.append(f"@#{current_page}")
            current_page += 1
        else:
            # Keep the line as-is
            output_lines.append(line)
    
    # ------------------------------------------------------------------
    # 4️⃣  Write the processed content to the output file
    # ------------------------------------------------------------------
    with txt_num_path.open('w', encoding='utf-8') as file:
        file.write("\n".join(output_lines))
    
    print(f"Successfully processed '{txt_path}' -> '{txt_num_path}'")
    print(f"Started at page {initial_page}, ended at page {current_page - 1}")

if __name__ == '__main__':
    main()