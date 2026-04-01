"""
Train optimized CodeClassifier on large correct/incorrect JSON datasets.

Features: AdamW, gradient clipping, ReduceLROnPlateau, best-checkpoint by val acc,
optional early stopping, larger BiLSTM, DataLoader with pin_memory on CUDA.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# ai/model_arch.py lives in parent of training/
_AI_DIR = Path(__file__).resolve().parent.parent
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from model_arch import CodeClassifier  # noqa: E402

from tokenizer import CharTokenizer, load_json_codes

BASE = Path(__file__).resolve().parent
DATASETS = BASE.parent / "datasets"
MODELS = BASE.parent / "models"


class CodeDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer: CharTokenizer) -> None:
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        ids = self.tokenizer.encode(self.texts[idx])
        x = torch.tensor(ids, dtype=torch.long)
        y = torch.tensor(self.labels[idx], dtype=torch.long)
        return x, y


def split_data(
    texts: List[str], labels: List[int], val_ratio: float
) -> Tuple[List[str], List[int], List[str], List[int]]:
    combined = list(zip(texts, labels))
    random.shuffle(combined)
    n_val = max(1, int(len(combined) * val_ratio))
    val = combined[:n_val]
    train = combined[n_val:]
    tr_x, tr_y = zip(*train) if train else ([], [])
    va_x, va_y = zip(*val) if val else ([], [])
    return list(tr_x), list(tr_y), list(va_x), list(va_y)


def train_loop(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    max_grad_norm: float,
) -> float:
    model.train()
    total_loss = 0.0
    n = 0
    for xb, yb in loader:
        xb, yb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        logits = model(xb)
        loss = criterion(logits, yb)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()
        total_loss += loss.item() * xb.size(0)
        n += xb.size(0)
    return total_loss / max(n, 1)


@torch.no_grad()
def evaluate(
    model: nn.Module, loader: DataLoader, device: torch.device, criterion: nn.Module
) -> Tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    n = 0
    for xb, yb in loader:
        xb, yb = xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
        logits = model(xb)
        loss = criterion(logits, yb)
        total_loss += loss.item() * xb.size(0)
        pred = logits.argmax(dim=-1)
        correct += (pred == yb).sum().item()
        n += xb.size(0)
    return total_loss / max(n, 1), correct / max(n, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train language code classifier.")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--max-len", type=int, default=256)
    parser.add_argument("--embed-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.25)
    parser.add_argument("--no-bidirectional", action="store_true")
    parser.add_argument("--val-ratio", type=float, default=0.12)
    parser.add_argument("--patience", type=int, default=8, help="Early stopping patience (0=disabled).")
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    correct_path = DATASETS / "correct_programs.json"
    incorrect_path = DATASETS / "incorrect_programs.json"
    if not correct_path.is_file() or not incorrect_path.is_file():
        raise SystemExit("Run ai/datasets/generate_datasets.py first.")

    print("Loading JSON datasets…", flush=True)
    correct_texts = load_json_codes(correct_path)
    incorrect_texts = load_json_codes(incorrect_path)
    texts = correct_texts + incorrect_texts
    labels = [1] * len(correct_texts) + [0] * len(incorrect_texts)

    print(f"Building tokenizer over {len(texts)} samples…", flush=True)
    tokenizer = CharTokenizer.build_from_texts(texts, max_len=args.max_len)
    tr_x, tr_y, va_x, va_y = split_data(texts, labels, val_ratio=args.val_ratio)
    print(f"Train={len(tr_x)}  Val={len(va_x)}  (device will be CUDA if available)", flush=True)

    pin = torch.cuda.is_available()
    # Windows: num_workers>0 often adds multiprocessing overhead; keep 0 for stability.
    nw = 0 if sys.platform == "win32" else min(4, max(1, (os.cpu_count() or 4) // 2))
    print(f"DataLoader num_workers={nw}  pin_memory={pin}", flush=True)

    train_loader = DataLoader(
        CodeDataset(tr_x, tr_y, tokenizer),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=nw,
        pin_memory=pin,
        persistent_workers=nw > 0,
    )
    val_loader = DataLoader(
        CodeDataset(va_x, va_y, tokenizer),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=nw,
        pin_memory=pin,
        persistent_workers=nw > 0,
    )

    pad_idx = tokenizer.pad_idx
    vocab_size = len(tokenizer.char_to_idx)
    bidirectional = not args.no_bidirectional

    model = CodeClassifier(
        vocab_size=vocab_size,
        embed_dim=args.embed_dim,
        hidden_dim=args.hidden_dim,
        num_classes=2,
        padding_idx=pad_idx,
        num_layers=args.num_layers,
        dropout=args.dropout,
        bidirectional=bidirectional,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3
    )
    criterion = nn.CrossEntropyLoss()

    best_acc = 0.0
    best_state = None
    stale = 0
    history: List[dict] = []

    for epoch in range(1, args.epochs + 1):
        tr_loss = train_loop(
            model, train_loader, device, optimizer, criterion, args.max_grad_norm
        )
        va_loss, va_acc = evaluate(model, val_loader, device, criterion)
        scheduler.step(va_acc)
        history.append(
            {
                "epoch": epoch,
                "train_loss": tr_loss,
                "val_loss": va_loss,
                "val_acc": va_acc,
                "lr": optimizer.param_groups[0]["lr"],
            }
        )
        print(
            f"epoch {epoch:3d}  train_loss={tr_loss:.4f}  val_loss={va_loss:.4f}  "
            f"val_acc={va_acc:.4f}  lr={optimizer.param_groups[0]['lr']:.2e}"
        )

        if va_acc > best_acc:
            best_acc = va_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1

        if args.patience > 0 and stale >= args.patience:
            print(f"Early stopping at epoch {epoch} (no val improvement for {args.patience} epochs).")
            break

    if best_state is not None:
        model.load_state_dict(best_state)

    MODELS.mkdir(parents=True, exist_ok=True)
    ckpt_path = MODELS / "code_classifier.pt"
    config = {
        "vocab_size": vocab_size,
        "embed_dim": args.embed_dim,
        "hidden_dim": args.hidden_dim,
        "num_classes": 2,
        "max_len": args.max_len,
        "num_layers": args.num_layers,
        "dropout": args.dropout,
        "bidirectional": bidirectional,
        "arch": "CodeClassifier",
    }
    torch.save(
        {"model_state_dict": model.state_dict(), "config": config, "best_val_acc": best_acc},
        ckpt_path,
    )
    tokenizer.save(MODELS / "tokenizer.json")
    (MODELS / "training_history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")

    print(f"Saved best model (val_acc≈{best_acc:.4f}) to {ckpt_path}")


if __name__ == "__main__":
    main()
