# AI Training

Purpose:
- Tokenize dataset JSON, train a small classifier, save checkpoints under `../models/`.

## Prerequisites
- Generate datasets first: `python ../datasets/generate_datasets.py`
- Install deps from repo root: `pip install -r ../../requirements.txt`

## Train
From this directory:

```
python train.py --epochs 15 --batch-size 16
```

Outputs:
- `../models/code_classifier.pt` — model weights and config
- `../models/tokenizer.json` — char vocabulary and `max_len`
- `../models/training_history.json` — per-epoch loss and validation accuracy

## What the model does
A character-level LSTM reads padded source snippets and predicts **correct vs incorrect** (binary). This is a compact baseline for later integration with `/ai-suggest`.
