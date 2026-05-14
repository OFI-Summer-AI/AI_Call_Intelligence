# AI Call Intelligence

Offline pipeline that turns **meeting recordings (MP4)** into **auditable JSON artifacts** and a **polished business narrative** (timeline, budget signals, technical vs non-technical discussion, conclusions). A **Streamlit** app visualizes the latest run.

This repository is intentionally small: one orchestrator, a handful of services, and no unused API layers.

---

## What it does

1. **Extract** mono 16 kHz WAV from MP4 (FFmpeg).
2. **Transcribe** with **local Whisper** (`STT_BACKEND=whisper`) or **OpenAI diarized STT** (`STT_BACKEND=openai_diarize`).
3. **Merge** speaker labels when pyannote-style diarization is wired in; today Whisper runs with a single `Unknown` label unless OpenAI diarize is used.
4. **Extract** structured sales fields (LLM).
5. **Governance risk** checklist (rule-based).
6. **Meeting intel**: short executive summary without per-line “vendor/client” roles when speakers are unknown (burst role LLM is **on hold** until better diarization).
7. **Assessment report** (LLM): polished sections, topic summary, discovery checklist coverage, conformance score, call-level assessment, insights, next actions, recommendation.

Each stage writes **one artifact** under `data/` so runs are traceable and optionally resumable.

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Python 3.10+** | Match your `venv` / CI. |
| **FFmpeg** | On `PATH`, or set `FFMPEG_PATH` to `ffmpeg.exe`. |
| **OpenAI API key** | Required for field extraction, meeting summary, assessment report. |
| **GPU optional** | Whisper runs on CPU with `fp16=False`. |

Heavy ML stacks (pyannote, torch) remain in `requirements.txt` for environments that re-enable diarization later; the default path does **not** import a standalone diarization module in this repo.

---

## Quick start

```powershell
cd AI_Call_Intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` in the project root (see table below). Never commit secrets.

**Default input:** `data/uploads/client_call_01.mp4` (change path in `app/main.py` if needed).

**Run pipeline:**

```powershell
python -m app.main
```

**Run dashboard:**

```powershell
streamlit run streamlit_app.py
```

The UI prefers `data/reports/final/*_final_report.json` and falls back to legacy `data/outputs/*_result.json`.

---

## Environment variables (`.env`)

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | LLM + optional OpenAI STT | _(required for LLM steps)_ |
| `LLM_MODEL` | Chat model for extraction / reports | `gpt-4o-mini` |
| `STT_BACKEND` | `whisper` or `openai_diarize` | `whisper` |
| `WHISPER_MODEL_SIZE` | Whisper checkpoint size | `base` |
| `OPENAI_TRANSCRIBE_MODEL` | Used only if `openai_diarize` | `gpt-4o-transcribe-diarize` |
| `FFMPEG_PATH` | Full path to `ffmpeg` if not on PATH | _(optional)_ |
| `PIPELINE_RESUME` | `true` / `1` to reuse on-disk artifacts and skip completed stages | `false` |
| `PIPELINE_VERSION` | Logged in metadata | `2.1` |
| `ENABLE_DIARIZATION` | Reserved for future pyannote wiring in pipeline | `false` |
| `DIARIZATION_HF_TOKEN` | Reserved for Hugging Face pyannote | _(optional)_ |

Load order: `python-dotenv` reads `.env` in `app/config.py`.

---

## `data/` layout (artifacts)

| Path | Content |
|------|---------|
| `data/uploads/` | Source MP4 (do not modify in pipeline). |
| `data/audio/` | Extracted WAV. |
| `data/transcripts/raw/` | Raw STT segments + language. |
| `data/diarization/` | Speaker segments (empty list until diarization is enabled). |
| `data/transcripts/merged/` | Transcript + speaker label per segment. |
| `data/transcripts/role_mapped/` | Intel payload (summary, map, segments with optional roles). |
| `data/extracted/` | `*_extracted_fields.json`, `*_question_assessment.json`. |
| `data/polished/` | `*_polished.json`, `*_polished.md`. |
| `data/reports/` | `*_risk_report.json`, `*_call_quality_report.json`. |
| `data/reports/final/` | **`{job}_final_report.json`** — primary dashboard input. |
| `data/metadata/` | Timing / version metadata per job. |
| `data/logs/` | Reserved for future structured logs. |
| `data/outputs/` | **Legacy** mirror (`*_result.json`, `*_transcript.json`) for older tooling. |

---

## Processing flow (high level)

```text
MP4 → WAV → STT → raw transcript JSON → diarization JSON → merged transcript
     → extracted fields JSON → risk report JSON → role-mapped JSON
     → assessment (polished + checklist + call quality) → final report JSON
     (+ legacy outputs/)
```

With `PIPELINE_RESUME=true`, existing files under `data/` short-circuit expensive steps (see `app/orchestrator/pipeline.py`).

---

## Repository map (handover)

| Path | Responsibility |
|------|----------------|
| `app/main.py` | CLI entry: default MP4 path, runs `Pipeline`. |
| `app/config.py` | Paths, env, directory bootstrap. |
| `app/orchestrator/pipeline.py` | End-to-end orchestration + artifact writes + resume. |
| `app/services/audio_extractor.py` | FFmpeg WAV extract; cached binary resolution. |
| `app/services/stt_service.py` | Local Whisper (lazy model load). |
| `app/services/openai_diarized_stt_service.py` | OpenAI diarized transcription. |
| `app/services/transcript_cleaner.py` | Trim segments; preserve STT confidence fields when present. |
| `app/services/speaker_mapper.py` | Overlap-based speaker assignment from diarization segments. |
| `app/services/field_extractor.py` | LLM JSON extraction schema (edit prompt + schema here). |
| `app/services/risk_report_service.py` | Rule-based governance flags. |
| `app/services/meeting_intel_service.py` | Executive summary; burst role block commented for future use. |
| `app/services/call_evaluation_template.py` | **Sales discovery checklist** IDs and prompts. |
| `app/services/call_assessment_report_service.py` | Polished narrative + checklist + conformance + report JSON. |
| `app/services/pipeline_artifacts.py` | Per-job paths + Markdown export helper. |
| `app/services/storage_service.py` | UTF-8 JSON read/write. |
| `streamlit_app.py` | Dashboard: charts + expanders for reports. |

---

## Customization for production

1. **Discovery questions** — edit `app/services/call_evaluation_template.py` (`DISCOVERY_QUESTIONS`).
2. **Extracted CRM fields** — edit prompt + fallback dict in `app/services/field_extractor.py`.
3. **Risk rules** — edit `app/services/risk_report_service.py`.
4. **Polished report tone / sections** — edit the JSON schema instructions in `app/services/call_assessment_report_service.py`.
5. **Input file** — change `mp4_file` in `app/main.py` or add your own CLI (small follow-up).

---

## Operations notes

- **Costs:** OpenAI is used for extraction, meeting summary, and assessment. Local Whisper has no OpenAI STT cost; `openai_diarize` bills per OpenAI audio policy.
- **Performance:** Whisper model loads on first `transcribe()` call (lazy). Set `FFMPEG_PATH` on large Windows PATH environments.
- **Secrets:** `.env` is gitignored; use host secret stores in production.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `ffmpeg executable not found` | Install FFmpeg and/or set `FFMPEG_PATH`. |
| Empty LLM fields | `OPENAI_API_KEY`, model name, and JSON parse errors in saved `assessment_note` / `raw_meeting_intel_output`. |
| Dashboard empty | Run pipeline first; confirm `data/reports/final/` or `data/outputs/` contains JSON. |
| Resume odd results | Delete intermediate artifacts for that job stem or set `PIPELINE_RESUME=false`. |

---

## License / support

Add your org’s license and support contacts here when you fork for internal use.
