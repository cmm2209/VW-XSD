#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
line_tagger.py

Converts a hard-return-separated *.txt* file to an *.xml* file,
where each line is surrounded by a numbered <l> tag.

Usage (PowerShell, CMD, Bash, etc.):
    python line_tagger.py <base_name> <first line number>

Example:
    python line_tagger.py myfile 1  # reads myfile.txt, writes myfile.xml starting with line 1
"""

import sys
import pathlib      
import xml.etree.ElementTree as ET         

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
    root = ET.Element("div")

    # Build full input / output paths (same folder as the script is run from)
    txt_path = pathlib.Path(f"{base_name}.txt")
    xml_path = pathlib.Path(f"{base_name}orig.xml")

    if not txt_path.is_file():
        print(f"Error: '{txt_path}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file 
    # ------------------------------------------------------------------
    with txt_path.open('r', encoding='utf-8') as file:
        # 1. Read the original content.
        content = file.read()
    lines = content.split("\n")
    
    for line in lines:
        line_element = ET.SubElement(root, 'l')
        line_element.text = line
        if int(initial_line) % 5 == 0:
            line_element.set('n', f'{int(initial_line)}')
        initial_line=int(initial_line)+1

    # Create the XML tree
    tree = ET.ElementTree(root)

    # Save the XML tree to the output file
    tree.write(xml_path, encoding='utf-8')

if __name__ == '__main__':
    main()