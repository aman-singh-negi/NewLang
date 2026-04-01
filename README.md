# language

**language** is a small educational language with a **compiler pipeline** (lexer → parser → semantic analysis → IR → optimizer → bytecode → stack VM), a **FastAPI backend** for the IDE, and a **React + Monaco** web UI. Optional **PyTorch** datasets and training support a lightweight **code-validity classifier** for the AI panel.

---

## Architecture (high level)

```
┌─────────────────────────────────────────────────────────────────┐
│                 frontend/ (React + Vite + Monaco)                │
│  Editor · Compile / Run / AI suggest → JSON in side panels     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP JSON (CORS)
┌────────────────────────────▼────────────────────────────────────┐
│                 backend/ (FastAPI)                               │
│  /compile  /run  /ai-suggest  + compiler_service pipeline      │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   lexer/ parser/   semantic/   ir/ optimizer/ codegen/ vm/
   tokens.py         analyzer   ir_generator   bytecode    StackVM
```

- **Source code** is tokenized, parsed to an AST-shaped dict, checked semantically, lowered to IR, optimized, then converted to bytecode and optionally executed on the VM.
- **Frontend** calls the same endpoints you would use from curl or another client; `VITE_API_URL` points at the backend.

---

## Repository layout

| Path | Role |
|------|------|
| `backend/main.py` | FastAPI app, CORS, routes `/compile`, `/run`, `/ai-suggest` |
| `backend/compiler_service.py` | End-to-end compile/run + optional AI inference |
| `backend/lexer/` | Lexer + token definitions |
| `backend/ast_parse/` | Recursive descent parser (named to avoid Python stdlib `parser`) |
| `backend/ast/` | AST node classes (dataclasses) |
| `backend/semantic/` | Symbol table + analyzer |
| `backend/ir/` | IR (3-address style) generation |
| `backend/optimizer/` | Constant folding + dead temp removal |
| `backend/codegen/` | IR → bytecode |
| `backend/vm/` | Stack VM (`PUSH`, `ADD`, `STORE`, `PRINT`, plus codegen opcodes) |
| `frontend/` | Vite + React + `@monaco-editor/react` IDE |
| `ai/datasets/` | JSON generators + `generate_datasets.py` |
| `ai/training/` | `tokenizer.py`, `train.py` (PyTorch) |
| `ai/models/` | Saved `code_classifier.pt`, `tokenizer.json` (after training) |

---

## Backend API

Base URL defaults to `http://127.0.0.1:8000` (see `backend/config.py`).

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `GET` | `/` | — | Health JSON |
| `POST` | `/compile` | `{ "code": "..." }` | Lex → parse → semantic → IR → optimized IR → bytecode |
| `POST` | `/run` | `{ "code": "..." }` | Same pipeline + VM; returns `stdout` (variables + VM print output) |
| `POST` | `/ai-suggest` | `{ "code": "..." }` | If `ai/models/` has weights, runs char-LSTM classifier; else placeholder |

**CORS** is enabled for `http://localhost:5173` and `http://127.0.0.1:5173` (Vite default).

### Running the backend

```bash
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Interactive docs: `http://127.0.0.1:8000/docs`.

---

## Frontend (IDE)

- **Stack:** Vite 5, React 18, TypeScript, **Monaco** with a **Frost** (Nord-inspired) dark theme (`frost-language`) and keyword highlighting for the `language` editor mode.
- **Layout:** **VS Code–like** UI: title bar (File / Edit / …), **activity bar**, **Explorer** sidebar, tab row + toolbar, resizable **panel** (`react-resizable-panels`), **blue status bar** (branch, backend, API URL).
- **Tabs:** **Terminal** (VM stdout), **Compiler** (stats, IR, bytecode, semantic warnings), **AI** (classifier + confidence).
- **Shortcuts:** **Ctrl+Enter** (or Cmd+Enter) → Run, **Ctrl+B** → Compile.
- **Features:** Compile / Run / AI; toasts; copy JSON; production build splits chunks (`react`, `monaco`, `panels`).

### Run the dev server

```bash
cd frontend
npm install
copy .env.example .env   # optional; edit VITE_API_URL if backend is elsewhere
npm run dev
```

Open `http://localhost:5173`. Ensure the backend is running on the URL shown in the status bar.

### Production build

```bash
cd frontend
npm run build
npm run preview
```

Serve `frontend/dist/` with any static host; configure CORS for your origin in `backend/main.py` if needed.

---

## Language subset (current)

Keywords include `var`, `when`, `otherwise`, `loop`, `func`, `show` (lexer). The **parser** implemented in this project focuses on:

- `var name = expression;`
- `when condition { ... } otherwise { ... }` (optional `otherwise`)
- Expressions with `+ - * /`, comparisons, parentheses, numbers, identifiers.

Extend `parser/parser.py` and `semantic/analyzer.py` as you add grammar.

---

## AI: datasets and training

1. **Generate data**

   ```bash
   cd ai/datasets
   python generate_datasets.py --count 8000
   ```

   Default is **8000 samples per category** (compact JSON). Use `--pretty` for readable JSON (much larger files). Produces `correct_programs.json`, `incorrect_programs.json`, `optimized_pairs.json`.

2. **Train**

   ```bash
   cd ai/training
   pip install -r ../../requirements.txt
   python train.py --epochs 30 --patience 8 --batch-size 128
   ```

   Uses a **BiLSTM** classifier (`ai/model_arch.py`): AdamW, gradient clipping, LR schedule, early stopping, best checkpoint by validation accuracy. On CPU, full runs can take many minutes; use `--epochs 10` for a quick smoke test.

   Writes `ai/models/code_classifier.pt`, `tokenizer.json`, `training_history.json`. Older checkpoints (single-layer LSTM) still load in the API via a legacy fallback in `compiler_service.py`.

3. **Use in the app**

   Restart the backend. `/ai-suggest` loads the checkpoint if present and returns a predicted label and confidence; otherwise it returns a friendly placeholder.

The model is a **binary classifier** (correct vs incorrect snippets) using character embeddings and a small LSTM; it is **not** a full program synthesizer.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| Frontend cannot reach API | Backend running, firewall, `VITE_API_URL` matches backend URL |
| CORS errors | `allow_origins` in `main.py` includes your dev origin |
| `/ai-suggest` always placeholder | Run `train.py`; confirm `ai/models/*.pt` exists |
| `ModuleNotFoundError` for backend | Run commands from `backend/` or set `PYTHONPATH` |

---

## Development notes

- Python imports assume execution with the **working directory** `backend/` (e.g. `uvicorn main:app`).
- The **AST** in `ast/nodes.py` is available for future parser refactors; the current parser emits **dict-shaped** trees for a single pipeline path.
- **VM** supports both minimal opcodes (`PUSH`, `ADD`, `STORE`, `PRINT`) and opcodes emitted by `codegen`.

---

## License

Educational / project use; adjust as needed for your course or organization.
