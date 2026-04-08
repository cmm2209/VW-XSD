from datasets import load_dataset
from tokenizers import (
    decoders,
    models,
    pre_tokenizers,
    processors,
    trainers,
    Tokenizer,
)

dataset = load_dataset("text", data_files="MHDtexts.txt", encoding="utf-8", split="train")

def get_training_corpus():
    for i in range(0, len(dataset), 500):
        yield dataset[i : i + 500]["text"]

tokenizer = Tokenizer(models.BPE())
tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)

trainer = trainers.BpeTrainer(vocab_size=25000, special_tokens=["<unk>"])
tokenizer.train_from_iterator(get_training_corpus(), trainer=trainer)
tokenizer.post_processor = processors.ByteLevel(trim_offsets=False)
tokenizer.decoder = decoders.ByteLevel()
tokenizer.save("BPEtokenizer.json")
