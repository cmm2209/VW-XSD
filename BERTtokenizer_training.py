from datasets import load_dataset
from tokenizers import (
    decoders,
    models,
    normalizers,
    pre_tokenizers,
    processors,
    trainers,
    Tokenizer,
)

dataset = load_dataset("text", data_files="MHDtexts.txt", encoding="utf-8", split="train")

def get_training_corpus():
    for i in range(0, len(dataset), 500):
        yield dataset[i : i + 500]["text"]

tokenizer = Tokenizer(models.WordPiece(unk_token="[UNK]"))
tokenizer.normalizer = normalizers.Sequence([normalizers.NFD(), normalizers.Lowercase()])
tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)

special_tokens = ["[UNK]", "[PAD]", "[CLS]", "[SEP]", "[MASK]"]
trainer = trainers.WordPieceTrainer(vocab_size=25000, special_tokens=special_tokens)
tokenizer.train_from_iterator(get_training_corpus(), trainer=trainer)

cls_token_id = tokenizer.token_to_id("[CLS]")
sep_token_id = tokenizer.token_to_id("[SEP]")
tokenizer.post_processor = processors.TemplateProcessing(
    single=f"[CLS]:0 $A:0 [SEP]:0",
    pair=f"[CLS]:0 $A:0 [SEP]:0 $B:1 [SEP]:1",
    special_tokens=[("[CLS]", cls_token_id), ("[SEP]", sep_token_id)],
)
tokenizer.decoder = decoders.WordPiece(prefix="##")
tokenizer.save("BERTtokenizer.json")
