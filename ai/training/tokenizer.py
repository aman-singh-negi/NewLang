"""
Purpose:
- Turn raw language source strings into fixed-length integer tensors for PyTorch.
- Character-level vocabulary keeps the model small and avoids external NLP deps.

Why char-level:
- Compiler-like snippets are short; a char vocab covers braces, keywords, digits.
- Training stays reproducible without downloading pretrained tokenizers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple


PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"


class CharTokenizer:
    """Maps characters to indices; pads or truncates to max_len."""

    def __init__(self, char_to_idx: Dict[str, int], max_len: int) -> None:
        self.char_to_idx = dict(char_to_idx)
        self.idx_to_char = {i: c for c, i in self.char_to_idx.items()}
        self.max_len = max_len
        self.pad_idx = self.char_to_idx[PAD_TOKEN]
        self.unk_idx = self.char_to_idx[UNK_TOKEN]

    @classmethod
    def build_from_texts(cls, texts: List[str], max_len: int) -> CharTokenizer:
        """Build vocabulary from corpus (special tokens first)."""
        chars = sorted(set("".join(texts)))
        char_to_idx: Dict[str, int] = {PAD_TOKEN: 0, UNK_TOKEN: 1}
        offset = len(char_to_idx)
        for i, ch in enumerate(chars):
            char_to_idx[ch] = i + offset
        return cls(char_to_idx=char_to_idx, max_len=max_len)

    def encode(self, text: str) -> List[int]:
        """Encode one string to a list of token ids (length == max_len after pad/trunc)."""
        ids: List[int] = []
        for ch in text[: self.max_len]:
            ids.append(self.char_to_idx.get(ch, self.unk_idx))
        while len(ids) < self.max_len:
            ids.append(self.pad_idx)
        return ids[: self.max_len]

    def save(self, path: Path) -> None:
        payload = {
            "char_to_idx": self.char_to_idx,
            "max_len": self.max_len,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> CharTokenizer:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(char_to_idx=payload["char_to_idx"], max_len=int(payload["max_len"]))


def load_json_codes(path: Path) -> List[str]:
    """Load `code` field from dataset JSON (correct or incorrect lists)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [item["code"] for item in data]
