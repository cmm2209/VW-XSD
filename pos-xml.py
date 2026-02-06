#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pos-xml.py

Converts a whitespace‑separated *.txt* file to an *.xml* file using pandas
and lxml.

Usage (PowerShell, CMD, Bash, etc.):
    python pos-xml.py <base_name>

Example:
    python pos-xml.py myfile   # reads myfile.txt, writes myfile.xml
"""

import sys
import pathlib
import io                    

import pandas as pd



def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name>", file=sys.stderr)
        sys.exit(1)

    base_name = sys.argv[1]

    # Build full input / output paths (same folder as the script is run from)
    txt_path = pathlib.Path(f"{base_name}.txt")
    xml_path = pathlib.Path(f"{base_name}.xml")

    if not txt_path.is_file():
        print(f"Error: '{txt_path}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file 
    # (which has its columns separated by variable amounts of white space)
    # ------------------------------------------------------------------
    with txt_path.open('r', encoding='utf-8') as file:
        # 1. Read the original content.
        original_text = file.read()
        # 2. Prepend a header line (followed by a newline).
        header = "token   pos     norm    lemma\n"
        # 3. Create a StringIO object that pandas can read from as if it were a file.
        text_with_header = io.StringIO(header + original_text)
        # 4. Read the resulting file as a space-separated table.
        df = pd.read_table(text_with_header, sep=' +', engine='python')

    # ------------------------------------------------------------------
    # 3️⃣  Write the DataFrame to .xml with custom options & stylesheet
    # ------------------------------------------------------------------
    df.to_xml(
        xml_path,
        index=False,
        root_name='body',
        row_name='w',
        attr_cols=['pos', 'norm', 'lemma'],
        elem_cols=['token'],
        na_rep='',
        stylesheet='https://raw.githubusercontent.com/cmm2209/VW-XSD/refs/heads/main/pos-to-xml-cleaner.xsl'
    )

    print(f"✅  Converted '{txt_path}' → '{xml_path}'")


if __name__ == '__main__':
    main()