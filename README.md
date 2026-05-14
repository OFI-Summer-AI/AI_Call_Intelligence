# AI Call Intelligence

Offline pipeline that turns **meeting recordings (video or audio)** into **auditable JSON artifacts** and a **polished business narrative** (timeline, budget signals, technical vs non-technical discussion, conclusions). A **Streamlit** app explores runs and exports shareable PDFs.

This repository is intentionally small: one orchestrator, a handful of services, and no unused API layers.

---

## Contents

- [Tech stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup (first run)](#setup-first-run)
- [Commands](#commands)
- [Environment variables](#environment-variables)
- [What it does (pipeline stages)](#what-it-does-pipeline-stages)
- [`data/` layout (artifacts)](#data-layout-artifacts)
- [Processing flow](#processing-flow-high-level)
- [Repository map](#repository-map-handover)
- [Customization](#customization-for-production)
- [Operations](#operations-notes)
- [Troubleshooting](#troubleshooting)
- [License / support](#license--support)

---

## Tech stack

| Area | Technology | Notes |
|------|-------------|--------|
| Language | **Python 3.10+** | Use the same major/minor as your `venv` / any CI. |
| UI | **Streamlit** 1.57+ | Multipage app under `app/frontend/`; config in `.streamlit/config.toml`. |
| LLM / API STT | **OpenAI** (`openai` SDK) | Chat for extraction, meeting intel, assessment; optional **diarized transcription** when `STT_BACKEND=openai_diarize`. |
| Local STT | **OpenAI Whisper** (`openai-whisper`) | Default `STT_BACKEND=whisper`; model sizes via `WHISPER_MODEL_SIZE`. |
| Audio prep | **FFmpeg** + **ffmpeg-python** | WAV extraction; set `FFMPEG_PATH` if `ffmpeg` is not on `PATH`. |
| Config | **python-dotenv** | Loads `.env` from the **repository root** when `app.core.config` (or `app.config`) is imported. |
| Charts / PDF | **matplotlib**, **numpy**, **fpdf2** | Figures embedded in meeting PDFs. |
| Word export | **python-docx** | Optional DOCX paths in the UI layer. |
| Diarization (optional) | **pyannote** / **torch** / **torchaudio** | Heavy stack in `requirements.txt`; pipeline wiring may still be partial—see `ENABLE_DIARIZATION`. |

Dependency versions are pinned in **`requirements.txt`** (freeze-style list). Install with `pip install -r requirements.txt` from an activated virtual environment.

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | 64-bit recommended for Whisper/torch wheels. |
| **FFmpeg** | On `PATH`, or set `FFMPEG_PATH` to `ffmpeg` / `ffmpeg.exe`. |
| **OpenAI API key** | Required for LLM stages (field extraction, meeting intel, assessment). Required for STT if `STT_BACKEND=openai_diarize`. |
| **Disk** | Whisper/torch checkpoints and uploaded media; allow several GB if you use larger Whisper models or full `requirements.txt`. |
| **GPU** | Optional; local Whisper uses CPU-friendly settings in this project. |

---

## Setup (first run)

Run these from the **repository root** (the folder that contains `app/`, `data/`, and `streamlit_app.py`).

### 1. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
cd path\to\AI_Call_Intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
cd path/to/AI_Call_Intelligence
python3 -m venv .venv
source .venv/bin/activate
```

If execution policy blocks activation on Windows, run once (current user):  
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install FFmpeg (if needed)

- **Windows:** Install FFmpeg and add its `bin` folder to **PATH**, or set **`FFMPEG_PATH`** in `.env` to the full path of `ffmpeg.exe`.
- **macOS:** e.g. `brew install ffmpeg`
- **Linux:** use your distro package (`ffmpeg`).

### 4. Create `.env` at the repository root

Copy the block below into a new file named **`.env`** (same folder as `README.md`). **Do not commit `.env`**; it should stay gitignored.

```env
# Required for LLM (and for OpenAI STT if you use it)
OPENAI_API_KEY=

# Optional overrides
LLM_MODEL=gpt-4o-mini
STT_BACKEND=whisper
WHISPER_MODEL_SIZE=base
OPENAI_TRANSCRIBE_MODEL=gpt-4o-transcribe-diarize

# Pipeline
PIPELINE_RESUME=false
PIPELINE_VERSION=2.1

# Optional paths / tuning
# FFMPEG_PATH=
# LOG_LEVEL=INFO
# CONFIDENCE_THRESHOLD=0.80
# STREAMLIT_MAX_UPLOAD_MB=8192

# Diarization (experimental / reserved)
ENABLE_DIARIZATION=false
# DIARIZATION_HF_TOKEN=
```

### 5. Smoke-check the CLI

```powershell
python -m app.main --help
```

You should see argparse help with `--upload-dir`, `--latest`, `--all`, and `--resume` / `--no-resume`.

---

## Commands

Always **`cd`** to the repository root first (so imports and `data/` paths resolve correctly).

### Pipeline (batch / headless)

| Command | What it does |
|---------|----------------|
| `python -m app.main` | Run the pipeline on **one** input: explicit path, or env `PIPELINE_INPUT` / `VIDEO_PATH` / `CALL_MEDIA_PATH`, or else the **newest** supported file in `data/uploads/`. |
| `python -m app.main "C:\path\to\recording.mp4"` | Run on a specific file. |
| `python -m app.main --latest` | Same as default when no path/env: newest supported file in default upload dir. |
| `python -m app.main --upload-dir "D:\media\inbox"` | Scan a different folder for `--latest` / default pick. |
| `python -m app.main --all` | Process **every** supported file in `--upload-dir` (newest first); continues on errors; exit non-zero if any job failed. |
| `python -m app.main --resume` | Resume from existing artifacts where possible (also controlled by env `PIPELINE_RESUME`). |
| `python -m app.main --no-resume` | Force a fresh run for that invocation (overrides env default). |

**Input discovery (no positional path):** the CLI checks, in order, `PIPELINE_INPUT`, `VIDEO_PATH`, then `CALL_MEDIA_PATH` (see `app/core/media_inputs.py`). Relative paths are resolved under `--upload-dir`.

### Dashboard (Streamlit)

| Command | What it does |
|---------|----------------|
| `streamlit run streamlit_app.py` | **Recommended:** root launcher re-execs Streamlit on `app/frontend/streamlit_app.py` (keeps `pages/` next to the real entry script). |
| `streamlit run app/frontend/streamlit_app.py` | Direct entry; equivalent once cwd is the repo root. |

**Upload size:** large recordings need a high server limit. This repo sets **`[server] maxUploadSize = 8192`** (MB) in `.streamlit/config.toml`. You can override at launch, e.g.  
`streamlit run streamlit_app.py --server.maxUploadSize 8192`  
or set env **`STREAMLIT_SERVER_MAX_UPLOAD_SIZE`** (Streamlit’s own knob). The app also reads **`STREAMLIT_MAX_UPLOAD_MB`** for UI-side limits—keep it in sync with Streamlit’s max upload to avoid confusing failures.

### Where outputs go

- Primary dashboard input: **`data/reports/final/*_final_report.json`**
- Legacy fallback: **`data/outputs/*_result.json`**

---

## Environment variables

Loaded by **`python-dotenv`** when **`app/core/config.py`** is imported (same values via **`app.config`**).

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | LLM + optional OpenAI STT | _(empty; required for LLM steps)_ |
| `LLM_MODEL` | Chat model for extraction / reports | `gpt-4o-mini` |
| `STT_BACKEND` | `whisper` or `openai_diarize` | `whisper` |
| `WHISPER_MODEL_SIZE` | Whisper checkpoint size (e.g. `tiny`, `base`, `small`) | `base` |
| `OPENAI_TRANSCRIBE_MODEL` | OpenAI audio model when `STT_BACKEND=openai_diarize` | `gpt-4o-transcribe-diarize` |
| `FFMPEG_PATH` | Full path to `ffmpeg` / `ffmpeg.exe` if not on `PATH` | _(optional)_ |
| `PIPELINE_RESUME` | `true` / `1` / `yes` to reuse on-disk artifacts and skip completed stages | `false` |
| `PIPELINE_VERSION` | Logged in metadata | `2.1` |
| `PIPELINE_INPUT` | Media path for CLI when no positional arg (also `VIDEO_PATH`, `CALL_MEDIA_PATH`) | _(optional)_ |
| `ENABLE_DIARIZATION` | Reserved / future pyannote wiring | `false` |
| `DIARIZATION_HF_TOKEN` | Hugging Face token for pyannote models | _(optional)_ |
| `STREAMLIT_MAX_UPLOAD_MB` | App-side upload cap (MB); align with Streamlit server limit | `8192` |
| `CONFIDENCE_THRESHOLD` | Float in `[0, 1]` for downstream scoring hooks | `0.80` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |

**Streamlit (not read by `app.core.config`):** `STREAMLIT_SERVER_MAX_UPLOAD_SIZE` and CLI flags such as `--server.maxUploadSize` control the **server** upload ceiling.

---

## What it does (pipeline stages)

1. **Extract** mono 16 kHz WAV from container formats (FFmpeg).
2. **Transcribe** with **local Whisper** (`STT_BACKEND=whisper`) or **OpenAI diarized STT** (`STT_BACKEND=openai_diarize`).
3. **Merge** speaker labels when diarization is active; with Whisper-only, expect a single `Unknown` speaker unless OpenAI diarize provides labels.
4. **Extract** structured sales fields (LLM).
5. **Governance risk** checklist (rule-based).
6. **Meeting intel**: executive summary (burst role labeling may be on hold until diarization quality improves).
7. **Assessment report** (LLM): polished sections, topic summary, discovery checklist coverage, conformance score, call-level assessment, insights, next actions, recommendation.

Each stage writes **traceable artifacts** under `data/` (see below). With **`PIPELINE_RESUME=true`**, existing files short-circuit expensive steps (`app/orchestrator/pipeline.py`).

---

## `data/` layout (artifacts)

| Path | Content |
|------|---------|
| `data/uploads/` | Source media (do not modify in pipeline). |
| `data/audio/` | Extracted WAV. |
| `data/transcripts/raw/` | Raw STT segments + language. |
| `data/diarization/` | Speaker segments (may be empty until diarization is enabled and wired). |
| `data/transcripts/merged/` | Transcript + speaker label per segment. |
| `data/transcripts/role_mapped/` | Intel payload (summary, map, segments with optional roles). |
| `data/extracted/` | `*_extracted_fields.json`, `*_question_assessment.json`. |
| `data/polished/` | `*_polished.json`, `*_polished.md`. |
| `data/reports/` | `*_risk_report.json`, `*_call_quality_report.json`. |
| `data/reports/final/` | **`{job}_final_report.json`** — primary dashboard input. |
| `data/metadata/` | Timing / version metadata per job. |
| `data/outputs/` | **Legacy** mirror (`*_result.json`, `*_transcript.json`) for older tooling. |
| `data/ui/` | Small UI-side JSON (e.g. meeting registry) used by Streamlit. |

---

## Processing flow (high level)

```text
MP4 → WAV → STT → raw transcript JSON → diarization JSON → merged transcript
     → extracted fields JSON → risk report JSON → role-mapped JSON
     → assessment (polished + checklist + call quality) → final report JSON
     (+ legacy outputs/)
```

---

## Repository map (handover)

| Path | Responsibility |
|------|----------------|
| `streamlit_app.py` (root) | Thin launcher: `streamlit run streamlit_app.py` → `app/frontend/streamlit_app.py`. |
| `app/frontend/streamlit_app.py` + `app/frontend/pages/` | Streamlit multipage app (entry + routes). |
| `app/frontend/` | UI: theme, nav, meeting views, charts, PDF/DOCX helpers; imports `app.*` for config, storage, and pipeline where needed. |
| `app/main.py` | `python -m app.main` → batch pipeline CLI (`app/orchestrator/cli.py`). |
| `app/core/config.py` | Paths, env validation, artifact directory bootstrap (`app/config.py` re-exports). |
| `app/core/media_inputs.py` | Upload discovery + env path resolution (`app/media_inputs.py` re-exports). |
| `app/orchestrator/cli.py` | Argparse CLI for single-file / `--all` / `--latest` runs. |
| `app/utils/log.py` | Pipeline + CLI logging (`configure_logging`, `get_logger`). |
| `app/orchestrator/pipeline.py` | End-to-end orchestration + artifact writes + resume. |
| `app/services/*.py` | FFmpeg extract, STT, cleaning, mapping, LLM extraction, risk, intel, assessment, artifacts, storage. |

---

## Customization for production

1. **Discovery questions** — `app/services/call_evaluation_template.py` (`DISCOVERY_QUESTIONS`).
2. **Extracted CRM fields** — prompt + schema in `app/services/field_extractor.py`.
3. **Risk rules** — `app/services/risk_report_service.py`.
4. **Report tone / sections** — JSON schema and instructions in `app/services/call_assessment_report_service.py`.
5. **Inputs** — CLI path, `PIPELINE_INPUT` / `VIDEO_PATH` / `CALL_MEDIA_PATH`, or files under `data/uploads/`.

---

## Operations notes

- **Costs:** OpenAI bills for chat and (if used) diarized audio per your account policy. Local Whisper avoids OpenAI STT charges but uses CPU/GPU time.
- **Performance:** Whisper loads on first transcription; keep `FFMPEG_PATH` explicit on Windows if `PATH` is huge.
- **Secrets:** Never commit `.env`. In production, inject env vars from a secret manager rather than copying files onto servers.
- **Git:** Keep virtual environments (`venv/`, `.venv/`) and `data/uploads/` out of version control via `.gitignore` (verify before pushing).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Blank Streamlit page or URL never forwards to the real app | The repo-root `streamlit_app.py` launcher must **not** use `if __name__ == "__main__"` (Streamlit’s script runner uses a synthetic `__main__`). This repo calls `_run()` unconditionally so `streamlit run streamlit_app.py` re-execs `app/frontend/streamlit_app.py`. |
| Browser says “can’t connect” on `http://localhost:8501` | Open **`http://127.0.0.1:8501`** instead (Windows often resolves `localhost` to IPv6 `::1` while the server listens on IPv4). This project sets `server.address` and `browser.serverAddress` to `127.0.0.1` in `.streamlit/config.toml`. |
| No browser tab opens | With `--server.headless true` Streamlit does not launch a browser; copy the **URL** from the terminal. |
| `ffmpeg executable not found` | Install FFmpeg and/or set `FFMPEG_PATH`. |
| `ModuleNotFoundError` (e.g. `streamlit`) | Activate the same `venv` you used for `pip install -r requirements.txt`. |
| `STT_BACKEND` / `LOG_LEVEL` errors at import | Fix typos in `.env`; allowed values are validated in `app/core/config.py`. |
| Empty LLM fields | `OPENAI_API_KEY`, `LLM_MODEL`, and JSON parse errors in saved assessment / intel fields. |
| Dashboard empty | Run the pipeline first; confirm `data/reports/final/` or legacy `data/outputs/` contains JSON. |
| Upload fails in UI | Raise Streamlit `maxUploadSize` and/or `STREAMLIT_SERVER_MAX_UPLOAD_SIZE`; align `STREAMLIT_MAX_UPLOAD_MB`. |
| Resume odd results | Delete intermediate artifacts for that job stem or set `PIPELINE_RESUME=false`. |

---

## License / support

Add your organization’s license and support contacts when you fork for internal use.
