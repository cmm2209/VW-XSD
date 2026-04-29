# sent_type_component.py
import srsly
from spacy.language import Language
from spacy.tokens import Token, Span

Token.set_extension("sent_type", default=None, force=True)
Span.set_extension("sent_type",  default=None, force=True)

SENT_TYPES = ["DE", "IE", "EE", "QE"]


@Language.factory("sent_type_detector")
def create_sent_type_detector(nlp, name):
    return SentTypeDetector(nlp.vocab)


class SentTypeDetector:
    """
    Classifies each sentence as DE / IE / EE / QE.
    Runs after tagger and morphologizer (Stage C) so that
    token.pos_ and token.morph_ are populated and available
    to the ConcatPOSMorphTagger architecture.
    S* tags are never used as classification targets.
    """

    def __init__(self, vocab):
        self.vocab  = vocab
        self.labels = SENT_TYPES

    def __call__(self, doc):
        trf_data = doc._.trf_data
        if trf_data is None:
            return doc

        for sent in doc.sents:
            sent_vec             = self._pool_sentence(trf_data, sent)
            label                = self._classify(sent_vec)
            sent._.sent_type     = label
            sent[-1]._.sent_type = label

        return doc

    def _pool_sentence(self, trf_data, sent):
        last_layer = trf_data.tensors[-1][0]
        return last_layer[sent.start:sent.end].mean(axis=0)

    def _classify(self, vector):
        raise NotImplementedError("Load trained weights via from_disk()")

    def to_disk(self, path, exclude=()):
        srsly.write_json(path / "cfg.json", {"labels": self.labels})

    def from_disk(self, path, exclude=()):
        cfg         = srsly.read_json(path / "cfg.json")
        self.labels = cfg["labels"]
        return self