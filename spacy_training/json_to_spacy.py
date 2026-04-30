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
from fingerprints import load_fingerprints

Token.set_extension("is_contraction_boundary", default=False, force=True)
Token.set_extension("sent_type",               default=None,  force=True)
Span.set_extension("sent_type",                default=None,  force=True)
Span.set_extension("word_form",                default=None,  force=True)
Span.set_extension("word_pos",                 default=None,  force=True)
Span.set_extension("word_morph",               default=None,  force=True)
Span.set_extension("word_lemma",               default=None,  force=True)
Span.set_extension("word_index",               default=None,  force=True)
Span.set_extension("surface_token_idx",        default=None,  force=True)
Doc.set_extension("provisional_splits",        default=None,  force=True)

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


def is_valid_field(value):
    return bool(value and value.strip())


def is_valid_contraction(sorted_group):
    if len(sorted_group) < 2:
        return False
    tokens_with_forms = [
        t for t in sorted_group
        if is_valid_field(t.get("form", ""))
    ]
    if len(tokens_with_forms) < 2:
        return False
    has_right = any(
        t.get("join") in ("right", "both") for t in sorted_group
    )
    has_left  = any(
        t.get("join") in ("left",  "both") for t in sorted_group
    )
    if not (has_right and has_left):
        return False
    final_pos = sorted_group[-1].get("pos_upos", "")
    if final_pos == "PUNCT":
        return False
    return True


def get_surface_form(virttok_id, token_dipl_list):
    for td in token_dipl_list:
        if td["virttok"] == virttok_id:
            form = td.get("form", "")
            return form if form and form.strip() else None
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
    """NFC normalisation only — preserves case."""
    return unicodedata.normalize("NFC", text)


def normalise(text):
    """NFC normalisation + lowercase. For lookup keys only."""
    return unicodedata.normalize("NFC", text).lower()


def normalise_pos(pos: str) -> str:
    """
    Ensures POS tag is uppercase as required by spaCy's UD validator.
    e.g. "adp" -> "ADP", "NOUN" -> "NOUN"
    """
    return pos.upper() if pos else "X"


def get_raw(tok, use_norm):
    if use_norm:
        norm = tok.get("norm", "")
        if is_valid_field(norm):
            return norm
        form = tok.get("form", "")
        return form if is_valid_field(form) else None
    else:
        form = tok.get("form", "")
        return form if is_valid_field(form) else None


# ---------------------------------------------------------------------------
# Build analyses list
# ---------------------------------------------------------------------------

def make_analyses(parts_iter, replacements):
    analyses = []
    for tok, raw_form in parts_iter:
        if not is_valid_field(raw_form):
            continue
        feats     = tok.get("feats_ud", {})
        morph_str = "|".join(
            f"{k}={v}" for k, v in sorted(feats.items())
        ) if feats else ""
        replaced_form = apply_replacements(nfc(raw_form), replacements)
        if not replaced_form:
            replaced_form = nfc(raw_form) if nfc(raw_form) else "□"
        analyses.append({
            "form":  replaced_form,
            "pos":   normalise_pos(tok.get("pos_upos", "X")),
            "morph": morph_str,
            "lemma": tok.get("lemma", raw_form),
        })
    return analyses


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

def json_to_spacy_docs(json_files, nlp, replacements, fingerprints):
    """
    Convert JSON files to spaCy Doc objects.

    Applies the same subword boundary correction that BertTokenizer
    applies at inference time, so that training docs reflect the
    token representations the MWT detector will actually see.

    For each source document produces TWO docs:
      1. Using original 'form' values
      2. Using normalised 'norm' values

    S* punc tags are ignored for sentence typing throughout.
    """
    # Build surface-level lookup from fingerprints once
    surface_lookup = {
        entry["surface"]: (fp, entry)
        for fp, entry in fingerprints.items()
    }

    docs = []

    for file_idx, path in enumerate(json_files):
        print(
            f"Converting docs: {file_idx + 1}/{len(json_files)}",
            end="\r", flush=True
        )

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

            # ── Build raw word list ────────────────────────────────────
            raw_words                   = []
            raw_spaces                  = []
            raw_pos_tags                = []
            raw_morph_feats             = []
            raw_is_contraction_boundary = []
            raw_token_positions         = []
            raw_word_punc               = []

            for i, vt_id in enumerate(order):
                group          = groups[vt_id]
                is_contraction = is_contraction_group(group)
                sorted_group   = sort_group(group) if is_contraction \
                                 else group

                if is_contraction and \
                        not is_valid_contraction(sorted_group):
                    is_contraction = False

                for j, tok in enumerate(sorted_group):
                    raw = get_raw(tok, use_norm)
                    if raw is None:
                        continue

                    nfc_raw = nfc(raw)
                    word    = apply_replacements(nfc_raw, replacements)
                    if not word:
                        word = nfc_raw if nfc_raw else "□"

                    raw_words.append(word)
                    raw_pos_tags.append(
                        normalise_pos(tok.get("pos_upos", "X"))
                    )
                    raw_morph_feats.append(tok.get("feats_ud", {}))
                    raw_token_positions.append(vt_id)

                    token_type  = tok.get("token_type", "")
                    is_boundary = (
                        is_contraction and token_type in ("MS2", "MS3")
                    )
                    raw_is_contraction_boundary.append(is_boundary)

                    if j == len(sorted_group) - 1:
                        punc = tok.get("punc", "")
                        raw_word_punc.append(
                            punc if punc in SENT_TYPES else ""
                        )
                    else:
                        raw_word_punc.append("")

                    if j < len(sorted_group) - 1:
                        raw_spaces.append(False)
                    elif i < len(order) - 1:
                        raw_spaces.append(True)
                    else:
                        raw_spaces.append(False)

            if not raw_words:
                continue

            # ── Apply subword override ─────────────────────────────────
            # Simulates BertTokenizer._override_subword_boundaries()
            # so training docs match inference-time token representations.
            words                   = []
            spaces_final            = []
            pos_tags                = []
            morph_feats             = []
            is_contraction_boundary = []
            token_positions         = []
            word_punc               = []
            provisional_info        = []

            word_idx = 0
            while word_idx < len(raw_words):
                word = raw_words[word_idx]
                key  = normalise(word)

                if key in surface_lookup:
                    fp, entry    = surface_lookup[key]
                    correct_subs = entry.get("correct_subwords")

                    if correct_subs is not None:
                        start_sub_idx = len(words)
                        provisional_info.append({
                            "start_idx": start_sub_idx,
                            "end_idx":   start_sub_idx + len(correct_subs),
                            "surface":   entry["surface"],
                            "analyses":  entry["analyses"],
                        })

                        for sub_idx, sub in enumerate(correct_subs):
                            words.append(sub)
                            pos_tags.append(raw_pos_tags[word_idx])
                            morph_feats.append(
                                raw_morph_feats[word_idx]
                            )
                            token_positions.append(
                                raw_token_positions[word_idx]
                            )
                            word_punc.append(
                                raw_word_punc[word_idx]
                                if sub_idx == len(correct_subs) - 1
                                else ""
                            )
                            is_boundary = (
                                raw_is_contraction_boundary[word_idx]
                                or sub_idx > 0
                            )
                            is_contraction_boundary.append(is_boundary)

                            if sub_idx < len(correct_subs) - 1:
                                spaces_final.append(False)
                            else:
                                spaces_final.append(
                                    raw_spaces[word_idx]
                                )

                        word_idx += 1
                        continue

                # No override — keep word as-is
                words.append(word)
                pos_tags.append(raw_pos_tags[word_idx])
                morph_feats.append(raw_morph_feats[word_idx])
                token_positions.append(raw_token_positions[word_idx])
                word_punc.append(raw_word_punc[word_idx])
                is_contraction_boundary.append(
                    raw_is_contraction_boundary[word_idx]
                )
                spaces_final.append(raw_spaces[word_idx])
                word_idx += 1

            if not words:
                continue

            doc = Doc(nlp.vocab, words=words, spaces=spaces_final)
            doc._.provisional_splits = provisional_info

            # ── Per-token attributes ───────────────────────────────────
            for token, pos, feats, is_boundary in zip(
                doc, pos_tags, morph_feats, is_contraction_boundary
            ):
                token.pos_                      = pos
                token._.is_contraction_boundary = is_boundary
                if feats:
                    morph_str = "|".join(
                        f"{k}={v}" for k, v in sorted(feats.items())
                    )
                    token.set_morph(morph_str)

            # ── Sentence boundaries ────────────────────────────────────
            virttok_to_word_idx = {}
            for w_idx, vt_id in enumerate(token_positions):
                if vt_id not in virttok_to_word_idx:
                    virttok_to_word_idx[vt_id] = w_idx

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
            for w_idx, vt_id in enumerate(token_positions):
                pos_1based = virttok_to_pos.get(vt_id)
                if pos_1based in sent_end_type:
                    word_idx_to_sent_end_type[w_idx] = \
                        sent_end_type[pos_1based]

            for w_idx, punc in enumerate(word_punc):
                if (punc in SENT_TYPES
                        and w_idx not in word_idx_to_sent_end_type):
                    word_idx_to_sent_end_type[w_idx] = punc

            for w_idx, stype in word_idx_to_sent_end_type.items():
                if w_idx < len(doc):
                    doc[w_idx]._.sent_type = stype

            for sent in doc.sents:
                for tok in reversed(list(sent)):
                    if tok._.sent_type is not None:
                        sent._.sent_type = tok._.sent_type
                        break

            # ── MWT word spans ─────────────────────────────────────────
            mwt_spans = []
            for split in provisional_info:
                start    = split["start_idx"]
                analyses = split["analyses"]
                if start < len(doc):
                    root_token = doc[start]
                    for analysis_idx, analysis in enumerate(analyses):
                        span = doc[root_token.i : root_token.i + 1]
                        span._.word_form         = analysis["form"]
                        span._.word_pos          = analysis["pos"]
                        span._.word_morph        = analysis["morph"]
                        span._.word_lemma        = analysis["lemma"]
                        span._.word_index        = analysis_idx
                        span._.surface_token_idx = root_token.i
                        mwt_spans.append(span)

            doc.spans["mwt_words"] = spacy.tokens.SpanGroup(
                doc,
                name  = "mwt_words",
                spans = mwt_spans,
            )

            docs.append(doc)

    print()
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

    # ── Load expansion table ───────────────────────────────────────────
    expansions_path = output_dir / "expansions.json"
    if not expansions_path.exists():
        print(
            f"ERROR: {expansions_path} not found.\n"
            f"expansions.json must already exist in data/."
        )
        sys.exit(1)

    print(f"Loading expansions from {expansions_path} ...")
    expansions = srsly.read_json(str(expansions_path))
    print(f"  Loaded {len(expansions)} expansion entries.")

    # ── Load fingerprints ──────────────────────────────────────────────
    fingerprints_path = output_dir / "fingerprints.json"
    if not fingerprints_path.exists():
        print(
            f"ERROR: {fingerprints_path} not found.\n"
            f"Run fingerprints.py first:\n"
            f"  python fingerprints.py \\\n"
            f"      --expansions {expansions_path} \\\n"
            f"      --tokenizer  BERTtokenizer.json \\\n"
            f"      --output     {fingerprints_path}"
        )
        sys.exit(1)

    fingerprints = load_fingerprints(str(fingerprints_path))

    # ── Convert to spaCy docs ──────────────────────────────────────────
    nlp  = spacy.blank("de")
    docs = json_to_spacy_docs(
        json_files, nlp, replacements, fingerprints
    )
    print(
        f"Converted {len(docs)} documents "
        f"({len(json_files)} source files × 2 variants)."
    )

    if not docs:
        print("No documents converted. Check JSON structure.")
        sys.exit(1)

    # Shuffle in pairs so form and norm variants of the same
    # source document always end up in the same split
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