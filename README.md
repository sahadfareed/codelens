# 🔍 CodeLens — AI-Powered Code Documentation Generator

CodeLens accepts source code (single files or a ZIP project), analyses its
structure with static analysis, and uses a Large Language Model (Google Gemini)
to generate structured technical documentation that can be viewed in the app
and downloaded as Markdown or Word.

## Features
- Upload individual source files or a multi-file `.zip` project
- Validation for unsupported types, empty files, corrupted ZIPs and oversized uploads
- Static analysis (Python AST + regex for JS/TS/Java/Go/C/C++): functions, classes,
  imports, entry points, internal file relationships, dependencies
- AI-generated documentation with 7 fixed sections
- In-app documentation panel with loading states, errors and **Regenerate**
- Download as **Markdown (.md)** or formatted **Word (.docx)**
- Retry with exponential backoff, timeout and optional fallback model for API failures

## Tech Stack
| Layer | Technology |
|---|---|
| UI | Streamlit |
| Language | Python 3 |
| LLM | Google Gemini (via `google-genai` SDK) |
| Static analysis | Python `ast`, regular expressions |
| Export | `python-docx` |
| Testing | `pytest` |

## Architecture
```
Upload (app.py)
   │
   ▼
core/ingest.py    → validates files, reads ZIPs in memory (never extracted or executed)
   │
   ▼
core/analyzer.py  → builds a "code map": file tree, functions, classes, imports,
   │                 relationships, dependencies, size budget/truncation notes
   ▼
core/llm.py       → system prompt + code map + source → Gemini → Markdown docs
   │
   ▼
app.py            → displays docs, Regenerate
   │
   ▼
core/exporter.py  → .md / .docx download
```

## Project Structure
```
codelens/
├── app.py                  # Streamlit UI (Panel A: upload, Panel B: docs)
├── core/
│   ├── ingest.py           # upload validation + safe ZIP reading
│   ├── analyzer.py         # static analysis / code map
│   ├── llm.py              # prompt building, Gemini call, retries
│   └── exporter.py         # Markdown → .md / .docx
├── prompts/system_prompt.txt
├── samples/                # test inputs + generated example output
└── tests/                  # pytest test suite (16 tests)
```

## Setup
```bash
git clone <repo-url> && cd codelens
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file (get a free key at https://aistudio.google.com):
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
# optional: GEMINI_FALLBACK_MODEL=another-model-name
```
Run the app:
```bash
streamlit run app.py
```
Run the tests:
```bash
pytest -v
```

## Design Decisions
1. **Static analysis before the LLM.** The code map gives the model verified facts
   (exact function names, imports, file relationships), which improves accuracy and
   reduces hallucination compared with sending raw code alone.
2. **Grounding rules in the prompt.** The system prompt forces the model to use only
   the provided code, reference exact file paths, and write
   *"Not determinable from the provided code"* instead of guessing.
3. **Fixed output structure.** Seven mandatory sections make the documentation
   consistent across projects and easy to export.
4. **Low temperature (0.2)** for factual, repeatable output.
5. **Uploaded code is untrusted.** Code is never executed; ZIPs are read in memory,
   path traversal (`../`) is blocked, junk folders (`node_modules`, `.git`, `__MACOSX`)
   are skipped, and size limits are enforced.
6. **Context budget.** Large projects are prioritised (code files first, shallow paths
   first) and truncated within a character budget; truncation is reported in the docs.
7. **Resilience.** Retries with exponential backoff on 429/5xx, a 90-second timeout,
   an optional fallback model, and clear user-facing error messages.
8. **Secrets.** The API key lives only in `.env` (git-ignored) and is used server-side.

## Testing
| Case | Expected result |
|---|---|
| Single Python file | Correct functions and entry point documented |
| Multi-file ZIP (`samples/todo_app.zip`) | File paths and relationships documented |
| Unsupported file (`.png`) | "Not a supported file type" error |
| Empty file (`samples/empty.py`) | "File is empty" error |
| Fake ZIP (`samples/fake.zip`) | "Corrupted or not a valid ZIP" error |
| Syntax error (`samples/broken_syntax.py`) | Analysed without crashing |
| Missing API key | "GEMINI_API_KEY is missing" error |
| Minimal code snippet | Docs state "Not determinable" instead of inventing details |

Automated: `pytest -v` → 16 tests covering ingestion, analysis and export.

## Example Output
See `samples/output/` for documentation generated from `samples/todo_app.zip`.

## Limitations
- Non-Python languages use regex analysis, which is less precise than a full parser.
- Very large projects are truncated to fit the model's context budget.
- Output quality depends on the LLM and may vary slightly between regenerations.
- Requires internet access and a valid Gemini API key.

## Author
Sahad Fareed — BCA (Cloud Computing), Yenepoya University
