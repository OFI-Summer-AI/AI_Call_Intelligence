# Sales Call Intelligence

AI-powered Sales Call Intelligence platform for processing MP4 meeting recordings and extracting structured business intelligence from conversations.

The system focuses on:

- Speech-to-text transcription with timestamps
- Speaker diarization (who spoke what)
- Client requirement extraction
- Client pain point identification
- Tech stack / platform extraction
- Risk report generation
- Timestamp-based traceability
- Future-ready video intelligence support

---

# Project Objective

Sales calls often contain critical business and technical information that is:
- undocumented
- misunderstood
- lost across teams
- difficult to trace later

This project converts raw meeting recordings into structured, searchable, and auditable sales intelligence.

---

# Current Scope (MVP)

## Audio Intelligence

### Features
- MP4 upload
- Audio extraction
- Timestamped speech-to-text
- Speaker diarization
- Transcript cleaning
- Sales field extraction
- Risk report generation
- Structured JSON output

---

# Planned Future Scope

## Video Intelligence
- Key frame extraction
- Dashboard/chart detection
- OCR from shared screens
- Timestamp-linked visual evidence

## Governance & Intelligence
- Human review workflows
- Confidence scoring
- Semantic validation
- Requirement drift detection

---

# High-Level Flow

```text
MP4 Upload
   ↓
Audio Extraction
   ↓
Speech-to-Text
   ↓
Speaker Diarization
   ↓
Transcript Cleaning
   ↓
Sales Field Extraction
   ↓
Risk Report Generation
   ↓
Structured Output
```

---

# Project Structure

```text
AI_Call_Intelligence/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── orchestrator/
│   │   └── pipeline.py
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── audio_extractor.py
│   │   ├── stt_service.py
│   │   ├── diarization_service.py
│   │   ├── transcript_cleaner.py
│   │   ├── field_extractor.py
│   │   ├── risk_report_service.py
│   │   ├── storage_service.py
│   │   └── job_service.py
│   ├── models/
│   │   └── db_models.py
│   └── utils/
│       ├── logger.py
│       └── file_utils.py
│
├── tests/
├── data/
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# Core Modules

## `pipeline.py`

Main orchestrator responsible for:

- coordinating the full workflow
- calling services in sequence
- managing processing flow

---

## `audio_extractor.py`

Responsible for:

- extracting audio from MP4
- audio conversion
- audio preprocessing

---

## `stt_service.py`

Responsible for:

- speech-to-text conversion
- timestamp generation
- transcript generation

---

## `diarization_service.py`

Responsible for:

- speaker segmentation
- speaker labeling
- identifying speaker timelines

---

## `transcript_cleaner.py`

Responsible for:

- transcript formatting
- punctuation cleanup
- transcript normalization

---

## `field_extractor.py`

Responsible for extracting:

- client name
- client problem
- strict requirements
- platforms/tech stack
- timelines
- dependencies
- action items

---

## `risk_report_service.py`

Responsible for generating:

- missing clarification points
- ambiguous requirements
- delivery risks
- commercial risks
- technical concerns

---

# Example Transcript Output

```json
[
  {
    "start": "00:01:12",
    "end": "00:01:18",
    "speaker": "Speaker_1",
    "text": "We need SAP integration in phase one."
  }
]
```

---

# Example Structured Output

```json
{
  "client_name": "ABC Corp",
  "client_problem": "Manual reporting delays",
  "strict_requirements": [
    "SAP integration",
    "15-minute dashboard refresh"
  ],
  "techstack_platform": [
    "SAP",
    "Power BI"
  ],
  "risk_report": [
    "Timeline not fully confirmed",
    "API ownership unclear"
  ]
}
```

---

# Technology Stack

| Component           | Technology     |
| ------------------- | -------------- |
| Backend API         | FastAPI (planned) |
| Speech-to-Text      | Whisper        |
| Speaker Diarization | Pyannote       |
| Database            | PostgreSQL (planned) |
| File Storage        | Local / S3 (planned) |
| Queue/Workers       | Celery + Redis (planned) |
| Deployment          | Docker         |

---

# Installation

## Clone Repository

```bash
git clone https://github.com/OFI-Summer-AI/AI_Call_Intelligence.git
cd AI_Call_Intelligence
```

---

## Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Application

For the current CLI-based MVP:

```bash
python -m app.main
```

This runs the offline pipeline on the sample MP4 at `data/uploads/client_call_01.mp4` and writes JSON outputs under `data/outputs/`.

An HTTP API (FastAPI + uvicorn) is planned for a later phase.

---

# Planned API Endpoints (Future)

## Upload MP4

```http
POST /upload
```

Uploads a meeting recording for processing.

---

## Check Job Status

```http
GET /job/{job_id}
```

Returns processing status.

---

## Fetch Final Result

```http
GET /job/{job_id}/result
```

Returns:

- transcript
- extracted fields
- risk report

---

# Processing Pipeline

## Step 1 — MP4 Upload

Store uploaded file and create job ID.

## Step 2 — Audio Extraction

Extract audio track from video.

## Step 3 — Speech-to-Text

Generate timestamped transcript.

## Step 4 — Speaker Diarization

Identify speaker segments.

## Step 5 — Transcript Cleaning

Normalize transcript structure.

## Step 6 — Sales Intelligence Extraction

Extract business-critical information.

## Step 7 — Risk Report Generation

Generate clarification and risk insights.

## Step 8 — Save Final Output

Store transcript and structured intelligence.

---

# Future Enhancements

## Audio Intelligence

- sentiment analysis
- confidence scoring
- semantic validation

## Video Intelligence

- frame summarization
- OCR extraction
- dashboard detection
- architecture diagram capture

## Governance

- human review workflows
- audit trails
- versioning
- requirement drift detection

---

# Design Principles

- Simple orchestrator architecture
- Modular services
- Production-ready structure
- Traceability via timestamps
- Extensible for multimodal AI
- Avoid overengineering in MVP

---

# Future Vision

The long-term goal is to build a multimodal conversational intelligence platform capable of understanding:

- sales calls
- client meetings
- project KT sessions
- internal discussions
- interview recordings

using:

- audio intelligence
- video intelligence
- semantic reasoning
- enterprise governance workflows

---

# License

Internal Research / Enterprise Use
