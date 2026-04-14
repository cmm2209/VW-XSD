import io                    

import pandas as pd
import numpy as np
from flashtext import KeywordProcessor

with open('tristan-tagged.txt', 'r', encoding='utf-8') as file:
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
pos_split = (
    df['pos']
        .str.split('|')
        .apply(lambda xs: list(
            map('|'.join, zip(*[x.split('.') for x in xs]))
        ))
        .apply(pd.Series)
        .fillna('*')
        .rename(columns={0:'A', 1:'B', 2:'C', 3:'D', 4:'E', 5:'F'})
)

dfexpan = df.join(pos_split)

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
        "VAPS":  "POS=ADJ|VerbForm=Part",
        "VMFIN": "POS=VERB|VerbForm=Fin",
        "VMIMP": "POS=VERB|VerbForm=Fin",
        "VMINF": "POS=VERB|VerbForm=Inf|VerbType=Mod",
        "VMPP":  "POS=VERB|VerbForm=Part|VerbType=Mod",
        "VMOS":  "POS=AUX|VerbForm=Part",
        "VVFIN": "POS=VERB|VerbForm=Fin",
        "VVIMP": "POS=VERB|VerbForm=Fin",
        "VVINF": "POS=VERB|VerbForm=Inf",
        "VVPP":  "POS=VERB|VerbForm=Part",
        "VVPS":  "POS=ADJ|VerbForm=Part",
        "ADJA":  "POS=ADJ",
        "ADJN": "POS=ADJ|Variant=Short",
        "ADJD": "POS=ADJ",
        "ADJS": "POS=ADJ",
        "AVD":  "POS=ADV",
        "APPR": "POS=ADP|AdpType=Prep",
        "APPO": "POS=ADP|AdpType=Post",
        "AVG": "POS=ADV|PronType=Gen,Rel",
        "AVW": "POS=ADV|PronType=Int",
        "AVNEG":  "POS=ADV",
        "PTKVZ": "POS=ADP|PartType=Vbp",

        "CARDA": "POS=NUM|NumType=Card",
        "CARDD": "POS=NUM|NumType=Card",
        "CARDS": "POS=NUM|NumType=Card",
        "DDART": "POS=DET|PronType=Art|Definite=Def",
        "DDA":   "POS=DET|PronType=Dem",
        "DDS":   "POS=PRON|PronType=Dem",
        "DRELS": "POS=PRON|PronType=Rel",
        "DPOSA": "POS=DET|PronType=Prs|Poss=Yes",
        "DPOSD": "POS=PRON|PronType=Prs|Poss=Yes",
        "DPOSS": "POS=NOUN|Poss=Yes",
        "DIART": "POS=DET|PronType=Art|Definite=Ind",
        "DIA": "POS=DET|PronType=Ind",
        "DIS": "POS=PRON|Definite=Ind",
        "PI": "POS=PRON|PronType=Ind",
        "PTKNEG": "POS=PART|Polarity=Neg",
        "DNEGA": "POS=ADJ|PronType=Ind,Tot,Neg",
        "DNEGN": "POS=ADJ|PronType=Ind,Tot,Neg",
        "DNEGS": "POS=NOUN|PronType=Ind,Tot,Neg",
        "PNEG":  "POS=NOUN|PronType=Ind,Tot,Neg",
        "DGA": "POS=DET|PronType=Int",
        "DGS": "POS=PRON|PronType=Int",
        "PG":  "POS=PRON|PronType=Gen",
        "DWA": "POS=DET|PronType=Int",
        "DWS": "POS=PRON|PronType=Int",
        "PW":  "POS=PRON|PronType=Int",
        "PPER": "POS=PRON|PronType=Prs",
        "PRF":  "POS=PRON|PronType=Prs|Reflex=Yes",
        "KON":   "POS=CCONJ",
        "KOUS":  "POS=SCONJ",
        "KO*":   "POS=SCONJ|ConjType=Amb",
        "KOKOM": "POS=CCONJ|ConjType=Comp",
        "NA": "POS=NOUN",
        "NE": "POS=PROPN",
        "PTKA":   "POS=PART",
        "PTKANT": "POS=PART|PartType=Res",
        "PTKNEG": "POS=PART|Polarity=Neg",
        "PTKVZ":  "POS=ADP|PartType=Vbp",
        "ITJ": "POS=INTJ",
        "FM": "Foreign=Yes",

        # Gender / Mood / Poss
        "Masc": "Gender=Masc",
        "Fem":  "Gender=Fem",
        "Neut": "Gender=Neut",
        "Ind":  "Mood=Ind",
        "Pos":  "Poss=Yes",
 
        # Case / Tense
        "Pres": "Tense=Pres",
        "Past": "Tense=Past",
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

        # Degree
        "Pos": "Degree=Pos",
        "Cmp": "Degree=Cmp",
        "Sup": "Degree=Sup",

        # Strong and Weak
        "st": "*",
        "wk": "*"
    }



kp.add_keywords_from_dict(
    {v: [k] for k, v in thesaurus.items()}
)

cols = ['A', 'B', 'C', 'D', 'E', 'F']

def split_pos_and_feats(row, cols):
    # Split each column into parallel analyses
    G_out = []
    H_out = []
    parts = [row[c].split('|') if isinstance(row[c], str) else ['*'] for c in cols]

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

dfexpan[cols] = dfexpan[cols].map(
    lambda x: replace_parallel(x, kp)
)

dfexpan[['G', 'H']] = dfexpan.apply(
    lambda row: split_pos_and_feats(row, cols),
    axis=1,
    result_type='expand'
)

dfexpan.to_xml(
        'tristan-tagged.xml',
        index=False,
        root_name='body',
        row_name='w',
        attr_cols=['G', 'H', 'norm', 'lemma'],
        elem_cols=['token'],
        na_rep=''
    )