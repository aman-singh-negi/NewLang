"""
Shared PyTorch classifier architecture for training and server inference.

Kept in ai/ so both training/ and backend/compiler_service can import the same
forward pass and layer shapes (avoids duplicated class definitions drifting).
"""

from __future__ import annotations

import torch
import torch.nn as nn


class CodeClassifier(nn.Module):
    """
    Optimized sequence classifier: embedding → BiLSTM stack → dropout → linear.

    Uses the last timestep of LSTM outputs (includes both directions when
    bidirectional=True), which matches common text-classification practice.
    """

    def __init__(
        self,
        vocab_size: int,
        embed_dim: int,
        hidden_dim: int,
        num_classes: int,
        padding_idx: int = 0,
        num_layers: int = 2,
        dropout: float = 0.25,
        bidirectional: bool = True,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)
        self.lstm = nn.LSTM(
            embed_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )
        out_dim = hidden_dim * (2 if bidirectional else 1)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(out_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.dropout(self.embedding(x))
        out, _ = self.lstm(emb)
        last = out[:, -1, :]
        return self.head(self.dropout(last))


def build_model_from_config(cfg: dict, padding_idx: int) -> CodeClassifier:
    """Rebuild model from checkpoint `config` dict."""
    return CodeClassifier(
        vocab_size=int(cfg["vocab_size"]),
        embed_dim=int(cfg["embed_dim"]),
        hidden_dim=int(cfg["hidden_dim"]),
        num_classes=int(cfg["num_classes"]),
        padding_idx=padding_idx,
        num_layers=int(cfg.get("num_layers", 2)),
        dropout=float(cfg.get("dropout", 0.25)),
        bidirectional=bool(cfg.get("bidirectional", True)),
    )
