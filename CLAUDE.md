\# Project: Audit Anomaly Detection Agent



A self-service tool that uses classical ML (isolation forest + XGBoost + ensemble) to detect anomalous financial transactions, and a RAG-powered LLM agent to explain each flagged anomaly in natural language. Shipped as a Streamlit app.



\## Stack

\- Python 3.11+

\- ML: scikit-learn, xgboost, pandas, numpy

\- LLM: anthropic Python SDK, claude-sonnet-4 for explanations

\- RAG: chromadb (vector store), sentence-transformers (embeddings)

\- App: streamlit

\- Env: python-dotenv for API keys



\## Folder Layout

\- `data/` — raw CSVs + processed parquet (gitignored)

\- `models/` — trained model .pkl files (gitignored)

\- `policies/` — markdown policy documents for RAG retrieval (committed)

\- `notebooks/` — Colab ML training notebook (committed)

\- `src/` — all production Python: data loading, RAG, explanation, audit logging

\- `app.py` — Streamlit entry point at repo root



\## Environment

\- Windows 11, PowerShell

\- API key in `.env` as `ANTHROPIC\_API\_KEY` — load via python-dotenv

\- All file paths must work cross-platform (use `pathlib`, not string concat)



\## Code Style

\- Use type hints on all function signatures

\- Use pathlib for paths, never hardcoded strings

\- Keep functions under 40 lines; split if longer

\- Module-level docstrings, function docstrings for non-obvious behavior

\- No global state in src/ modules



\## Testing \& Verification

\- Each src/ module gets a smoke test in `src/test\_\*.py`

\- Run `python -m pytest src/` after any change

\- For the Streamlit app, verify by running `streamlit run app.py` and checking the three tabs load



\## Constraints That Save Tokens

\- Do NOT load the raw CSVs into your context. They're 500MB. Reference them by path.

\- Do NOT read the trained model files. Reference them as artifacts.

\- When making changes to multiple files, prefer one comprehensive plan in plan mode over iterative edits

\- After completing a phase, suggest `/clear` before starting the next phase



\## Workflow Rules

\- Always use plan mode for changes touching more than one file

\- Run smoke tests after changes

\- For Streamlit, check that the app boots locally before claiming a feature is done

\- Commit after each phase: scaffolding, RAG, Streamlit, polish

