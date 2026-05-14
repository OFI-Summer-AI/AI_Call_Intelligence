"""
Backward-compatible entry: ``python -m app.main`` runs the batch pipeline CLI.

Orchestration lives in ``Pipeline`` (single linear flow with resume checkpoints).
The Streamlit UI is a separate entrypoint (see ``app/frontend/streamlit_app.py``).
"""

from app.orchestrator.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
