import sys

def parse_fs(fs_string):
    fs = {}
    if not fs_string or fs_string == "_":
        return fs
    for item in fs_string.split("|"):
        if "=" in item:
            k, v = item.split("=", 1)
            fs[k] = v
    return fs


def it_pos_to_ud(fs, lemma):
    pos = fs.get("pos")
    verbform = fs.get("verbform")

    if pos == "noun":
        return "NOUN"
    if pos == "verb" and verbform == "fin":
        return "VERB"
    if pos == "verb" and lemma in ("sum", "possum"):
        return "AUX"
    if pos == "adj":
        return "ADJ"
    if pos == "adv":
        return "ADV"
    if pos == "adp":
        return "ADP"
    if pos == "num":
        return "NUM"
    if pos == "part":
        return "PART"
    if pos == "int":
        return "INTJ"
    if pos == "punc":
        return "PUNCT"

    return "X"


def it_feats_to_ud(fs):
    feats = []

    def add(k, v):
        feats.append(f"{k}={v}")

    if "case" in fs:
        add("Case", fs["case"].capitalize())

    if "number" in fs:
        add("Number", fs["number"].capitalize())

    if "gender" in fs:
        add("Gender", fs["gender"].capitalize())

    if "person" in fs:
        add("Person", fs["person"])

    tense_map = {
        "pres": "Pres",
        "past": "Past",
        "fut": "Fut",
        "imp": "Imp",
        "pqp": "Pqp",
    }
    if fs.get("tense") in tense_map:
        add("Tense", tense_map[fs["tense"]])

    mood_map = {
        "ind": "Ind",
        "sub": "Sub",
        "imp": "Imp",
    }
    if fs.get("mood") in mood_map:
        add("Mood", mood_map[fs["mood"]])

    voice_map = {
        "act": "Act",
        "pass": "Pass",
    }
    if fs.get("voice") in voice_map:
        add("Voice", voice_map[fs["voice"]])

    vf_map = {
        "fin": "Fin",
        "inf": "Inf",
        "part": "Part",
        "ger": "Ger",
        "gdv": "Gdv",
        "sup": "Sup",
    }
    if fs.get("verbform") in vf_map:
        add("VerbForm", vf_map[fs["verbform"]])

    deg_map = {
        "pos": "Pos",
        "cmp": "Cmp",
        "sup": "Sup",
    }
    if fs.get("degree") in deg_map:
        add("Degree", deg_map[fs["degree"]])

    return feats


for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue

    form, lemma, fs_string = line.split("\t", 2)
    fs = parse_fs(fs_string)

    upos = it_pos_to_ud(fs, lemma)
    feats = it_feats_to_ud(fs)
    feat_str = "|".join(sorted(feats)) if feats else "_"

    print(form, lemma, upos, feat_str, sep="\t")