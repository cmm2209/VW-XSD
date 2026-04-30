# mwt_component.py
import unicodedata
import srsly
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token, Span

# ---------------------------------------------------------------------------
# Token extensions
# ---------------------------------------------------------------------------
Token.set_extension("is_contraction_boundary", default=False, force=True)
Token.set_extension("line_number",             default=None,  force=True)
Token.set_extension("page_number",             default=None,  force=True)
Token.set_extension("paragraph_number",        default=None,  force=True)
Token.set_extension("book_number",             default=None,  force=True)
Token.set_extension("direct_speech",           default=None,  force=True)
Token.set_extension("original_form",           default=None,  force=True)

# Doc-level extension: records which token ranges were provisionally
# resegmented by BertTokenizer._override_subword_boundaries().
# Each entry is a dict:
#   {
#     "start_idx": int,   first token index of the resegmented span
#     "end_idx":   int,   one past the last token index
#     "surface":   str,   original surface form e.g. "ander"
#     "analyses":  list,  expansion table analyses
#   }
Doc.set_extension("provisional_splits", default=None, force=True)

# ---------------------------------------------------------------------------
# Span extensions for MWT syntactic words
# ---------------------------------------------------------------------------
Span.set_extension("word_form",         default=None, force=True)
Span.set_extension("word_pos",          default=None, force=True)
Span.set_extension("word_morph",        default=None, force=True)
Span.set_extension("word_lemma",        default=None, force=True)
Span.set_extension("word_index",        default=None, force=True)
Span.set_extension("surface_token_idx", default=None, force=True)


# ---------------------------------------------------------------------------
# MWT Detector
# ---------------------------------------------------------------------------

@Language.factory("mwt_detector")
def create_mwt_detector(nlp, name):
    return MWTDetector(nlp.vocab)


class MWTDetector:
    """
    Decides, for each provisionally resegmented token span, whether
    it is a genuine contraction (True) or a single word that happened
    to match a contraction fingerprint (False).

    Operates on doc._.provisional_splits set by BertTokenizer.
    Uses GHisBERT contextual embeddings (averaged over the span)
    as input to a learned binary classification head.

    Sets token._.is_contraction_boundary = True on the second (and
    third, for three-way contractions) token of confirmed splits.

    The transformer has already seen the corrected subword boundaries,
    so its embeddings reflect the linguistic context of each component
    word rather than arbitrary WordPiece cuts.
    """

    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, doc):
        trf_data = doc._.trf_data
        splits   = doc._.provisional_splits

        if trf_data is None or not splits:
            return doc

        for split in splits:
            start    = split["start_idx"]
            end      = split["end_idx"]
            vec      = self._pool_span(trf_data, start, end)
            is_contr = self._classify(vec)

            if is_contr:
                for boundary_idx in range(start + 1, end):
                    if boundary_idx < len(doc):
                        doc[boundary_idx]._.is_contraction_boundary \
                            = True

        return doc

    def _pool_span(self, trf_data, start, end):
        last_layer = trf_data.tensors[-1][0]
        span_vecs  = last_layer[start:end]
        return span_vecs.mean(axis=0)

    def _classify(self, vector):
        raise NotImplementedError("Load trained weights via from_disk()")

    def to_disk(self, path, exclude=()):
        srsly.write_json(path / "cfg.json", {})

    def from_disk(self, path, exclude=()):
        return self


# ---------------------------------------------------------------------------
# MWT Annotator
# ---------------------------------------------------------------------------

@Language.factory("mwt_annotator")
def create_mwt_annotator(nlp, name):
    return MWTAnnotator(nlp.vocab)


class MWTAnnotator:
    """
    For each confirmed contraction (where is_contraction_boundary
    has been set by MWTDetector), creates Span entries in
    doc.spans["mwt_words"] carrying form/pos/morph/lemma for each
    syntactic word.

    Uses doc._.provisional_splits to find confirmed contractions.
    A split is confirmed if any token in its range has
    is_contraction_boundary = True.

    The subword token stream is left completely intact.
    """

    def __init__(self, vocab, expansions=None):
        self.vocab      = vocab
        self.expansions = expansions or {}

    def __call__(self, doc):
        splits    = doc._.provisional_splits
        mwt_spans = []

        if splits:
            for split in splits:
                start    = split["start_idx"]
                end      = split["end_idx"]
                analyses = split["analyses"]

                is_confirmed = any(
                    doc[idx]._.is_contraction_boundary
                    for idx in range(start + 1, end)
                    if idx < len(doc)
                )

                if not is_confirmed:
                    continue

                root_token = doc[start]
                for word_idx, analysis in enumerate(analyses):
                    span = doc[root_token.i : root_token.i + 1]
                    span._.word_form         = analysis.get("form",  "")
                    span._.word_pos          = analysis.get("pos",   "X")
                    span._.word_morph        = analysis.get("morph", "")
                    span._.word_lemma        = analysis.get("lemma", "")
                    span._.word_index        = word_idx
                    span._.surface_token_idx = root_token.i
                    mwt_spans.append(span)

        doc.spans["mwt_words"] = spacy.tokens.SpanGroup(
            doc,
            name  = "mwt_words",
            spans = mwt_spans,
        )

        return doc

    def to_disk(self, path, exclude=()):
        srsly.write_json(path / "expansions.json", self.expansions)

    def from_disk(self, path, exclude=()):
        self.expansions = srsly.read_json(path / "expansions.json")
        return self