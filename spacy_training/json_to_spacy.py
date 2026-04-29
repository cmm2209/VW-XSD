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
            form = td.get("form", "")
            # Treat empty form as absent
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
    Tokens with empty form fields are skipped.
    """
    analyses = []
    for tok, raw_form in parts_iter:

        # Skip empty form fields
        if not raw_form or not raw_form.strip():
            continue

        feats     = tok.get("feats_ud", {})
        morph_str = "|".join(
            f"{k}={v}" for k, v in sorted(feats.items())
        ) if feats else ""

        replaced_form = apply_replacements(nfc(raw_form), replacements)

        # Guard against empty string after replacements
        if not replaced_form:
            replaced_form = nfc(raw_form) if nfc(raw_form) else "□"

        analyses.append({
            "form":  replaced_form,
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
    Tokens and surface forms with empty fields are skipped.
    """
    expansions = {}

    for file_idx, path in enumerate(json_files):
        print(
            f"Building expansions: {file_idx + 1}/{len(json_files)}",
            end="\r", flush=True
        )

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

                # Skip empty surface forms
                if not surface_raw or not surface_raw.strip():
                    continue

                key_orig = apply_replacements(
                    normalise(surface_raw), replacements
                )
                if not key_orig:
                    key_orig = normalise(surface_raw)

                analyses_1 = make_analyses(
                    ((t, t["form"]) for t in sorted_group),
                    replacements
                )
                if key_orig not in expansions and analyses_1:
                    expansions[key_orig] = analyses_1

            # ── Entry 2: norm surface → norm analyses ──────────────────
            norm_forms = [
                t.get("norm", t["form"]) for t in sorted_group
            ]

            # Skip if all norm forms are empty
            norm_forms = [f for f in norm_forms if f and f.strip()]
            if not norm_forms:
                continue

            key_norm = apply_replacements(
                normalise("".join(norm_forms)), replacements
            )
            if not key_norm:
                key_norm = normalise("".join(norm_forms))

            analyses_2 = make_analyses(
                zip(sorted_group, norm_forms),
                replacements
            )
            if (key_norm not in expansions
                    and key_norm != key_orig
                    and analyses_2):
                expansions[key_norm] = analyses_2

    print()  # newline after progress line
    return expansions


# ---------------------------------------------------------------------------
# Build sentence type maps
# ---------------------------------------------------------------------------

def build_sent_type_map(sentences):
    """
    Returns two dicts keyed by 1-based virtual token index:
      sent_start_type[i] = type for sentence beginning at token i
      sent_end_type[i]   = type for sentence ending at token i

    Only DE, IE, EE, QE types are recorded.
    S* and all other values are ignored.
    """
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

    Tokens with empty form fields are skipped entirely.
    Subword token stream left intact — no merging performed,
    mirroring the inference-time pipeline.

    S* punc tags are ignored for sentence typing throughout.
    """
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

        # Token-level punc map: virttok_id → SENT_TYPES value only
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
                    raw = (
                        tok.get("norm", tok["form"])
                        if use_norm else tok["form"]
                    )

                    # Skip tokens with empty form fields
                    if not raw or not raw.strip():
                        continue

                    # nfc() BEFORE apply_replacements()
                    nfc_raw = nfc(raw)
                    word    = apply_replacements(nfc_raw, replacements)

                    # Guard against empty string after replacements
                    if not word:
                        word = nfc_raw if nfc_raw else "□"

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

            doc = Doc(nlp.vocab, words=words, spaces=spaces)

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

                if is_contraction and word_idx < len(doc):
                    token      = doc[word_idx]
                    norm_forms = [
                        t.get("norm", t["form"])
                        for t in sorted_group
                        if t.get("norm", t["form"])
                        and t.get("norm", t["form"]).strip()
                    ]
                    if norm_forms:
                        parts = (
                            zip(sorted_group, norm_forms)
                            if use_norm
                            else (
                                (t, t["form"])
                                for t in sorted_group
                                if t["form"] and t["form"].strip()
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

                # Advance word_idx by the number of non-empty tokens
                # in this group that were actually added to words[]
                for tok in sorted_group:
                    raw_check = (
                        tok.get("norm", tok["form"])
                        if use_norm else tok["form"]
                    )
                    if raw_check and raw_check.strip():
                        word_idx += 1

            doc.spans["mwt_words"] = spacy.tokens.SpanGroup(
                doc,
                name  = "mwt_words",
                spans = mwt_spans,
            )

            docs.append(doc)

    print()  # newline after progress line
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