# json_to_spacy.py
import json
import glob
import random
import unicodedata
import srsly
import sys
from pathlib import Path
from spacy.tokens import DocBin, Doc, Token, Span
import spacy

from text_replacements import load_replacements, apply_replacements_with_mapping

Token.set_extension("is_contraction_boundary", default=False, force=True)
Token.set_extension("sent_type",               default=None,  force=True)
Span.set_extension("sent_type",                default=None,  force=True)
Span.set_extension("word_form",                default=None,  force=True)
Span.set_extension("word_pos",                 default=None,  force=True)
Span.set_extension("word_morph",               default=None,  force=True)
Span.set_extension("word_lemma",               default=None,  force=True)
Span.set_extension("word_index",               default=None,  force=True)
Span.set_extension("surface_token_idx",        default=None,  force=True)

SENT_TYPES = {"DE", "IE", "EE", "QE"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def group_tokens_by_virttok(tokens):
    groups = {}
    order  = []
    for tok in tokens:
        vt = tok["virttok"]
        if vt not in groups:
            groups[vt] = []
            order.append(vt)
        groups[vt].append(tok)
    return order, groups


def is_contraction_group(group):
    return any("join" in t for t in group)


def get_surface_form(virttok_id, token_dipl_list):
    for td in token_dipl_list:
        if td["virttok"] == virttok_id:
            return td["form"]
    return None


def sort_group(group):
    order_map = {"MS1": 0, "MS2": 1, "MS3": 2}
    return sorted(
        group,
        key=lambda t: order_map.get(t.get("token_type", "MS1"), 0)
    )


def apply_replacements(text, replacements):
    replaced, _ = apply_replacements_with_mapping(text, replacements)
    return replaced


def nfc(text):
    """
    NFC normalisation only — preserves case.
    Applied BEFORE replacements so replacement rules see a
    consistent Unicode form. Case preserved for tagger training.
    """
    return unicodedata.normalize("NFC", text)


def normalise(text):
    """
    NFC normalisation + lowercase.
    Used for expansion table lookup keys only — never for
    word forms stored in training docs.
    Applied BEFORE replacements.
    """
    return unicodedata.normalize("NFC", text).lower()


# ---------------------------------------------------------------------------
# Build expansion dictionary
# ---------------------------------------------------------------------------

def make_analyses(parts_iter, replacements):
    """
    Build a list of analysis dicts from an iterable of
    (tok, raw_form) pairs.
    Each dict has keys: form, pos, morph, lemma.
    nfc() applied BEFORE replacements.
    """
    analyses = []
    for tok, raw_form in parts_iter:
        feats     = tok.get("feats_ud", {})
        morph_str = "|".join(
            f"{k}={v}" for k, v in sorted(feats.items())
        ) if feats else ""
        analyses.append({
            "form":  apply_replacements(nfc(raw_form), replacements),
            "pos":   tok.get("pos_upos", "X"),
            "morph": morph_str,
            "lemma": tok.get("lemma", raw_form),
        })
    return analyses


def build_expansions_from_json(json_files, replacements):
    """
    Build expansion dictionary from all JSON files.

    For each contraction, creates TWO entries:
      1. apply_replacements(normalise(form surface)) → form analyses
      2. apply_replacements(normalise(norm surface)) → norm analyses

    normalise() (NFC + lowercase) is applied BEFORE replacements
    so that replacement rules see a consistent Unicode form.
    """
    expansions = {}

    for path in json_files:
        data       = load_json_file(path)
        tokens     = data["token"]
        token_dipl = data.get("token_dipl", [])

        order, groups = group_tokens_by_virttok(tokens)

        for vt_id in order:
            group = groups[vt_id]
            if not is_contraction_group(group):
                continue

            sorted_group = sort_group(group)

            # ── Entry 1: form surface → form analyses ─────────────────
            surface_raw = get_surface_form(vt_id, token_dipl)
            if surface_raw is not None:
                key_orig   = apply_replacements(
                    normalise(surface_raw), replacements
                )
                analyses_1 = make_analyses(
                    ((t, t["form"]) for t in sorted_group),
                    replacements
                )
                if key_orig not in expansions:
                    expansions[key_orig] = analyses_1

            # ── Entry 2: norm surface → norm analyses ──────────────────
            norm_forms = [
                t.get("norm", t["form"]) for t in sorted_group
            ]
            key_norm   = apply_replacements(
                normalise("".join(norm_forms)), replacements
            )
            analyses_2 = make_analyses(
                zip(sorted_group, norm_forms),
                replacements
            )
            if key_norm not in expansions and key_norm != key_orig:
                expansions[key_norm] = analyses_2

    return expansions


# ---------------------------------------------------------------------------
# Build sentence type maps
# ---------------------------------------------------------------------------

def build_sent_type_map(sentences):
    sent_start_type = {}
    sent_end_type   = {}
    for sent in sentences:
        stype = sent.get("type", "")
        if stype not in SENT_TYPES:
            continue
        sent_start_type[sent["begin"]] = stype
        sent_end_type[sent["end"]]     = stype
    return sent_start_type, sent_end_type


# ---------------------------------------------------------------------------
# Convert JSON documents to spaCy Docs
# ---------------------------------------------------------------------------

def json_to_spacy_docs(json_files, nlp, replacements):
    """
    Convert JSON files to spaCy Doc objects.

    For each source document produces TWO docs:
      1. Using original 'form' values
      2. Using normalised 'norm' values

    Order of operations for word forms:
      nfc() first (NFC only, preserves case) → apply_replacements()

    Subword token stream left intact — no merging performed,
    mirroring the inference-time pipeline.
    """
    docs = []

    for path in json_files:
        data      = load_json_file(path)
        tokens    = data["token"]
        sentences = data.get("sentence", [])

        order, groups = group_tokens_by_virttok(tokens)

        virttok_to_pos = {
            vt: i + 1 for i, vt in enumerate(order)
        }
        sent_start_type, sent_end_type = build_sent_type_map(sentences)

        token_punc = {}
        for tok in tokens:
            punc = tok.get("punc", "")
            if punc in SENT_TYPES:
                token_punc[tok["virttok"]] = punc

        for use_norm in (False, True):

            words                   = []
            spaces                  = []
            pos_tags                = []
            morph_feats             = []
            is_contraction_boundary = []
            token_positions         = []
            word_punc               = []

            for i, vt_id in enumerate(order):
                group          = groups[vt_id]
                is_contraction = is_contraction_group(group)
                sorted_group   = sort_group(group) if is_contraction \
                                 else group

                for j, tok in enumerate(sorted_group):
                    raw  = (
                        tok.get("norm", tok["form"])
                        if use_norm else tok["form"]
                    )
                    # nfc() BEFORE apply_replacements()
                    word = apply_replacements(nfc(raw), replacements)

                    words.append(word)
                    pos_tags.append(tok.get("pos_upos", "X"))
                    morph_feats.append(tok.get("feats_ud", {}))
                    token_positions.append(vt_id)

                    token_type  = tok.get("token_type", "")
                    is_boundary = (
                        is_contraction and token_type in ("MS2", "MS3")
                    )
                    is_contraction_boundary.append(is_boundary)

                    if j == len(sorted_group) - 1:
                        punc = tok.get("punc", "")
                        word_punc.append(
                            punc if punc in SENT_TYPES else ""
                        )
                    else:
                        word_punc.append("")

                    if j < len(sorted_group) - 1:
                        spaces.append(False)
                    elif i < len(order) - 1:
                        spaces.append(True)
                    else:
                        spaces.append(False)

            if not words:
                continue
            
            for word_idx, word in enumerate(words):
                if word == "" or word.strip() == "":
                    vt_id   = token_positions[word_idx]
                    print(
                        f"\nEmpty word at index {word_idx} "
                        f"in file {path} "
                        f"(virttok={vt_id}, use_norm={use_norm})"
                    )
            doc = Doc(nlp.vocab, words=words, spaces=spaces)

            # ── Per-token attributes ───────────────────────────────────
            for token, pos, feats, is_boundary in zip(
                doc, pos_tags, morph_feats, is_contraction_boundary
            ):
                token.pos_                      = pos
                token._.is_contraction_boundary = is_boundary
                if feats:
                    morph_str    = "|".join(
                        f"{k}={v}" for k, v in sorted(feats.items())
                    )
                    token.set_morph(morph_str)

            # ── Sentence boundaries ────────────────────────────────────
            virttok_to_word_idx = {}
            for word_idx, vt_id in enumerate(token_positions):
                if vt_id not in virttok_to_word_idx:
                    virttok_to_word_idx[vt_id] = word_idx

            sent_start_word_idxs = set()
            if sentences:
                for sent in sentences:
                    begin_vtok = f"t{sent['begin']}"
                    if begin_vtok in virttok_to_word_idx:
                        sent_start_word_idxs.add(
                            virttok_to_word_idx[begin_vtok]
                        )

            for i, token in enumerate(doc):
                token.is_sent_start = (i in sent_start_word_idxs)

            # ── Sentence type labels ───────────────────────────────────
            word_idx_to_sent_end_type = {}
            for word_idx, vt_id in enumerate(token_positions):
                pos_1based = virttok_to_pos.get(vt_id)
                if pos_1based in sent_end_type:
                    word_idx_to_sent_end_type[word_idx] = \
                        sent_end_type[pos_1based]

            for word_idx, punc in enumerate(word_punc):
                if (punc in SENT_TYPES
                        and word_idx not in word_idx_to_sent_end_type):
                    word_idx_to_sent_end_type[word_idx] = punc

            for word_idx, stype in word_idx_to_sent_end_type.items():
                doc[word_idx]._.sent_type = stype

            for sent in doc.sents:
                for tok in reversed(list(sent)):
                    if tok._.sent_type is not None:
                        sent._.sent_type = tok._.sent_type
                        break

            # ── MWT word spans ─────────────────────────────────────────
            mwt_spans = []
            word_idx  = 0

            for vt_id in order:
                group          = groups[vt_id]
                is_contraction = is_contraction_group(group)
                sorted_group   = sort_group(group) if is_contraction \
                                 else group

                if is_contraction:
                    token      = doc[word_idx]
                    norm_forms = [
                        t.get("norm", t["form"])
                        for t in sorted_group
                    ]
                    parts = (
                        zip(sorted_group, norm_forms)
                        if use_norm
                        else (
                            (t, t["form"]) for t in sorted_group
                        )
                    )
                    analyses = make_analyses(parts, replacements)
                    for analysis_idx, analysis in enumerate(analyses):
                        span = doc[token.i : token.i + 1]
                        span._.word_form         = analysis["form"]
                        span._.word_pos          = analysis["pos"]
                        span._.word_morph        = analysis["morph"]
                        span._.word_lemma        = analysis["lemma"]
                        span._.word_index        = analysis_idx
                        span._.surface_token_idx = token.i
                        mwt_spans.append(span)

                word_idx += len(sorted_group)

            doc.spans["mwt_words"] = spacy.tokens.SpanGroup(
                doc,
                name  = "mwt_words",
                spans = mwt_spans,
            )

            docs.append(doc)

    return docs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    json_dir   = sys.argv[1] if len(sys.argv) > 1 else "."
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    json_files = sorted(glob.glob(f"{json_dir}/*.json"))
    print(f"Found {len(json_files)} JSON files.")

    if not json_files:
        print("No JSON files found. Check your path.")
        sys.exit(1)

    replacements = load_replacements("replacements.json")
    print("Loaded replacements.json.")

    expansions = build_expansions_from_json(json_files, replacements)
    srsly.write_json(output_dir / "expansions.json", expansions)
    print(f"Built expansion table with {len(expansions)} entries.")

    nlp  = spacy.blank("de")
    docs = json_to_spacy_docs(json_files, nlp, replacements)
    print(
        f"Converted {len(docs)} documents "
        f"({len(json_files)} source files × 2 variants)."
    )

    if not docs:
        print("No documents converted. Check JSON structure.")
        sys.exit(1)

    paired      = list(zip(docs[0::2], docs[1::2]))
    random.seed(42)
    random.shuffle(paired)
    split       = int(len(paired) * 0.9)
    train_pairs = paired[:split]
    dev_pairs   = paired[split:]

    train_docs = [d for pair in train_pairs for d in pair]
    dev_docs   = [d for pair in dev_pairs   for d in pair]

    train_db = DocBin(docs=train_docs, store_user_data=True)
    dev_db   = DocBin(docs=dev_docs,   store_user_data=True)
    train_db.to_disk(output_dir / "train.spacy")
    dev_db.to_disk(output_dir   / "dev.spacy")

    print(
        f"Saved {len(train_docs)} train docs "
        f"and {len(dev_docs)} dev docs."
    )
    print("Done. Files written to data/")


if __name__ == "__main__":
    main()