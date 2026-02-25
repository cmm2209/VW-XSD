#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pos-UD-xml.py

Converts a whitespace‑separated *.txt* file to an *.xml* file using pandas
and lxml, converting the HiTS POS tags to the Universal Dependencies format.

Usage (PowerShell, CMD, Bash, etc.):
    python pos-UD-xml.py <base_name>

Example:
    python pos-UD-xml.py myfile   # reads myfile.txt, writes myfile.xml
"""

import sys
import pathlib
import io                    

import pandas as pd
import numpy as np
from flashtext import KeywordProcessor


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
    # 3️⃣  Convert the POS tagging
    # ------------------------------------------------------------------
    # Define punctuation classes
    PUNC = {",", ".", "!", "?", ":", ";", '#', '(', ')', '[', ']', '{', '}', '"'}

    #Split pos analysis to individual columns
    dfexpan = df.join(
    df['pos']
    .str.split('|')
    .apply(lambda xs: list(map('|'.join, zip(*[x.split('.') for x in xs]))))
    .apply(pd.Series)
    .fillna('*')
    .rename(columns={0:'A', 1:'B', 2:'C', 3:'D', 4:'E', 5:'F'})
    )

    # Boolean masks
    is_punc = dfexpan['token'].isin(PUNC)

    # If punctuation, Set column A to PUNCT, remaining to *
    dfexpan.loc[is_punc, 'A'] = "POS=PUNCT"
    cols_BF = ['B', 'C', 'D', 'E', 'F']
    dfexpan.loc[is_punc, cols_BF] = '*'


    kp = KeywordProcessor()

    thesaurus = {
        # POS / VerbForm
        "VAFIN": "POS=AUX|VerbForm=Fin",
        "VAIMP": "POS=AUX|VerbForm=Fin",
        "VAINF": "POS=AUX|VerbForm=Inf",
        "VAPP":  "POS=AUX|VerbForm=Part",
        "VAPS":  "POS=AUX|VerbForm=Part",
        "VMFIN": "POS=AUX|VerbForm=Fin",
        "VMIMP": "POS=AUX|VerbForm=Fin",
        "VMINF": "POS=AUX|VerbForm=Inf",
        "VMPP":  "POS=AUX|VerbForm=Part",
        "VMOS":  "POS=AUX|VerbForm=Part",
        "VVFIN": "POS=VERB|VerbForm=Fin",
        "VVIMP": "POS=VERB|VerbForm=Fin",
        "VVINF": "POS=VERB|VerbForm=Inf",
        "VVPP":  "POS=VERB|VerbForm=Part",
        "VVPS":  "POS=VERB|VerbForm=Part",

        # Gender / Mood / Poss
        "Masc": "Gender=Masc",
        "Fem":  "Gender=Fem",
        "Neut": "Gender=Neut",
        "Ind":  "Mood=Ind",
        "Pos":  "Poss=Yes",

        # Case / Tense
        "Pres": "Tense=Pres",
        "Past": "Tense=Past'",
        "Nom":  "Case=Nom",
        "Akk":  "Case=Acc",
        "Gen":  "Case=Gen",
        "Dat":  "Case=Dat",

        # Number
        "Sg": "Number=Sing",
        "Pl": "Number=Plur",

        # Person
        "1": "Person=1",
        "2": "Person=2",
        "3": "Person=3",

        # Strong and Weak
        "st": "*",
        "wk": "*"
    }

    kp.add_keywords_from_dict(
        {v: [k] for k, v in thesaurus.items()}
    )

    def split_pos_and_feats(row, cols_AF):
        # Split each column into parallel analyses
        parts = [
            row[c].split('|') if isinstance(row[c], str) else ['*']
            for c in cols_AF
        ]

        G_out = []
        H_out = []

        for slot in zip(*parts):
            pos_val = '*'
            feats = []

            for val in slot:
                if val == '*' or not val:
                    continue
                for feat in val.split('|'):
                    if feat.startswith('POS='):
                        pos_val = feat
                    else:
                        feats.append(feat)

            # Deduplicate and sort features by attribute name (left of '=')
            feats = sorted(
                set(feats),
                key=lambda x: x.split('=', 1)[0]
            )

            G_out.append(pos_val)
            H_out.append('|'.join(feats) if feats else '*')

        # NOTE: G uses |, H uses ||
        return (
            '|'.join(G_out),
            '||'.join(H_out)
        )

    def replace_parallel(text, kp):
        if not isinstance(text, str):
            return text
        return '|'.join(
            kp.replace_keywords(part) for part in text.split('|')
        )

    cols = ['A', 'B', 'C', 'D', 'E', 'F']
    dfexpan[cols] = dfexpan[cols].applymap(
        lambda x: replace_parallel(x, kp)
    )

    dfexpan[['G', 'H']] = dfexpan.apply(
        lambda row: split_pos_and_feats(row, cols),
        axis=1,
        result_type='expand'
    )

    # ------------------------------------------------------------------
    # 4  Write the DataFrame to .xml with custom options & stylesheet
    # ------------------------------------------------------------------
    df.to_xml(
        xml_path,
        index=False,
        root_name='body',
        row_name='w',
        attr_cols=['G', 'H', 'norm', 'lemma'],
        elem_cols=['token'],
        na_rep='',
        stylesheet='https://raw.githubusercontent.com/cmm2209/VW-XSD/refs/heads/main/pos-to-xml-cleaner.xsl'
    )

    print(f"✅  Converted '{txt_path}' → '{xml_path}'")


if __name__ == '__main__':
    main()