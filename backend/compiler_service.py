"""
Purpose:
- Glue lexer → parser → semantic → IR → optimizer → codegen → VM for API routes.
- Centralizes error handling so FastAPI handlers stay thin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_AI_ROOT = Path(__file__).resolve().parent.parent / "ai"
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

from codegen.codegen import generate_bytecode
from ir.ir_generator import generate_ir
from lexer.lexer import LexerError, tokenize
from lexer.tokens import Token
from optimizer.optimizer import optimize_ir
from ast_parse.parser import ParserError, parse_tokens
from semantic.analyzer import analyze_ast
from vm.vm import run_bytecode


def _token_to_dict(t: Token) -> Dict[str, Any]:
    return {
        "type": t.token_type,
        "value": t.value,
        "line": t.line,
        "position": t.position,
    }


def compile_source(code: str) -> Dict[str, Any]:
    """
    Run compilation stages up to bytecode; return structured result or error.
    """
    try:
        tokens = tokenize(code)
    except LexerError as exc:
        return {"ok": False, "stage": "lexer", "error": str(exc)}

    try:
        ast = parse_tokens(tokens)
    except ParserError as exc:
        return {"ok": False, "stage": "parser", "error": str(exc)}

    semantic = analyze_ast(ast)
    ir = generate_ir(ast)
    ir_opt = optimize_ir(ir)
    bytecode = generate_bytecode(ir_opt)

    return {
        "ok": True,
        "tokens": [_token_to_dict(t) for t in tokens if t.token_type != "EOF"],
        "ast": ast,
        "semantic": semantic,
        "ir": ir,
        "ir_optimized": ir_opt,
        "bytecode": bytecode,
    }


def run_source(code: str) -> Dict[str, Any]:
    """Compile then execute bytecode on the stack VM."""
    compiled = compile_source(code)
    if not compiled.get("ok"):
        return compiled

    semantic = compiled["semantic"]
    if not semantic.get("success"):
        return {
            "ok": False,
            "stage": "semantic",
            "error": "; ".join(semantic.get("errors", [])),
            "semantic": semantic,
        }

    try:
        result = run_bytecode(compiled["bytecode"])
    except Exception as exc:  # VMError or runtime
        return {"ok": False, "stage": "vm", "error": str(exc)}

    variables = result.get("variables", {})
    output_lines = result.get("output", [])
    stdout = json.dumps(variables, indent=2)
    if output_lines:
        stdout += "\n--- print output ---\n" + "\n".join(output_lines)

    return {
        "ok": True,
        "stdout": stdout,
        "stderr": "",
        "exit_code": 0,
        "variables": variables,
        "print_output": output_lines,
    }


def _default_ai_suggest() -> Dict[str, Any]:
    return {
        "status": "placeholder",
        "suggestions": [
            "Train the classifier (ai/training/train.py) and restart the server "
            "to enable live suggestions."
        ],
        "confidence": 0.0,
        "label": None,
    }


def ai_suggest(code: str) -> Dict[str, Any]:
    """
    If a trained model exists under ai/models/, run inference; else placeholder.
    """
    models_dir = Path(__file__).resolve().parent.parent / "ai" / "models"
    ckpt = models_dir / "code_classifier.pt"
    tok_path = models_dir / "tokenizer.json"

    if not ckpt.is_file() or not tok_path.is_file():
        out = _default_ai_suggest()
        out["status"] = "no_model"
        return out

    try:
        import torch
    except ImportError:
        out = _default_ai_suggest()
        out["status"] = "torch_missing"
        return out

    from model_arch import build_model_from_config  # noqa: PLC0415 — only when model exists

    try:
        meta = torch.load(ckpt, map_location="cpu", weights_only=False)
    except TypeError:
        meta = torch.load(ckpt, map_location="cpu")
    cfg = meta["config"]
    max_len = int(cfg["max_len"])

    raw = json.loads(tok_path.read_text(encoding="utf-8"))
    char_to_idx = raw["char_to_idx"]
    pad_idx = char_to_idx.get("<pad>", 0)
    unk_idx = char_to_idx.get("<unk>", 1)

    def encode(text: str) -> List[int]:
        ids: List[int] = []
        for ch in text[:max_len]:
            ids.append(char_to_idx.get(ch, unk_idx))
        while len(ids) < max_len:
            ids.append(pad_idx)
        return ids[:max_len]

    state = meta["model_state_dict"]
    try:
        model = build_model_from_config(cfg, padding_idx=pad_idx)
        model.load_state_dict(state)
    except (RuntimeError, KeyError, TypeError):
        # Legacy checkpoint (single-layer uni LSTM, smaller head input).
        import torch.nn as nn

        vocab_size = int(cfg["vocab_size"])
        embed_dim = int(cfg["embed_dim"])
        hidden_dim = int(cfg["hidden_dim"])
        num_classes = int(cfg["num_classes"])

        class LegacyClassifier(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=pad_idx)
                self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, num_layers=1)
                self.head = nn.Linear(hidden_dim, num_classes)

            def forward(self, x: "torch.Tensor") -> "torch.Tensor":
                emb = self.embedding(x)
                _, (h_n, _) = self.lstm(emb)
                return self.head(h_n[-1])

        model = LegacyClassifier()
        model.load_state_dict(state)

    model.eval()

    x = torch.tensor([encode(code)], dtype=torch.long)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=-1)[0]
        pred = int(logits.argmax(dim=-1).item())
        confidence = float(probs[pred].item())

    label_name = "likely_valid" if pred == 1 else "likely_invalid"
    suggestions = [
        f"Model prediction: {label_name} (class {pred}).",
        "This is a heuristic from the char-LSTM; fix syntax errors if the lexer fails.",
    ]
    return {
        "status": "model",
        "suggestions": suggestions,
        "confidence": confidence,
        "label": label_name,
        "class_id": pred,
    }
