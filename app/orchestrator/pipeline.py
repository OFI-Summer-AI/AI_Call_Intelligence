from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from app.config import (
    LLM_MODEL,
    OUTPUT_DIR,
    PIPELINE_RESUME,
    PIPELINE_VERSION,
    STT_BACKEND,
    WHISPER_MODEL_SIZE,
)
from app.services.audio_extractor import extract_audio
from app.services.stt_service import STTService
from app.services.openai_diarized_stt_service import OpenAIDiarizedSTTService
from app.services.transcript_cleaner import clean_segments
from app.services.speaker_mapper import assign_speakers_to_transcript
from app.services.field_extractor import FieldExtractor
from app.services.risk_report_service import RiskReportService
from app.services.storage_service import StorageService
from app.services.call_evaluation_template import DISCOVERY_QUESTIONS
from app.services.call_assessment_report_service import CallAssessmentReportService
from app.services.meeting_intel_service import (
    enrich_meeting_intel,
    meeting_intel_without_diarization,
)
from app.services.pipeline_artifacts import JobArtifactPaths, polished_to_markdown
from app.services.video_metadata import probe_video_metadata
from app.orchestrator.diarization import has_usable_diarization
from app.utils.log import configure_logging, get_logger, log_stage

# Terminal flow: one log line per completed stage (see ``log_stage``).
_FLOW_TOTAL = 8


class Pipeline:
    """Coordinates the full call-intelligence processing flow (artifact per stage)."""

    def __init__(self) -> None:
        if STT_BACKEND == "openai_diarize":
            self._stt = OpenAIDiarizedSTTService()
        else:
            self._stt = STTService(model_size=WHISPER_MODEL_SIZE)
        self.field_extractor = FieldExtractor()
        self.risk_service = RiskReportService()
        self.call_assessment = CallAssessmentReportService()
        self.storage_service = StorageService()

    def run(self, mp4_path: str, resume: bool | None = None) -> dict:
        configure_logging()
        log = get_logger(__name__)

        mp4_path = Path(mp4_path)
        job_name = mp4_path.stem
        paths = JobArtifactPaths(job_name)
        resume = PIPELINE_RESUME if resume is None else resume

        t0 = time.monotonic()
        pipeline_meta: Dict[str, Any] = {
            "meeting_id": job_name,
            "pipeline_version": PIPELINE_VERSION,
            "stt_backend": STT_BACKEND,
            "whisper_model_size": WHISPER_MODEL_SIZE,
            "llm_model": LLM_MODEL,
            "resume": resume,
            "stages_ms": {},
            "errors": [],
        }

        if resume and paths.final_report.exists():
            log.info(
                "flow | stage=resume | job=%s | artifact=%s",
                job_name,
                paths.rel(paths.final_report),
            )
            return self.storage_service.load_json(paths.final_report)

        # --- 1) Audio extract ---
        t_audio = time.monotonic()
        if not (resume and paths.wav.exists()):
            extract_audio(mp4_path, paths.wav)
        ms_audio = int((time.monotonic() - t_audio) * 1000)
        pipeline_meta["stages_ms"]["extract_audio"] = ms_audio
        log_stage(log, stage="audio_extractor", duration_ms=ms_audio, step=1, total=_FLOW_TOTAL)

        # --- 2–5) STT → raw transcript → diarization artifact → merged speaker transcript ---
        t_stt = time.monotonic()
        speaker_transcript: List[Dict[str, Any]]
        stt_result: Dict[str, Any]
        diarization_segments: List[Dict[str, Any]] = []

        if resume and paths.merged_transcript.exists():
            merged_doc = self.storage_service.load_json(paths.merged_transcript)
            speaker_transcript = merged_doc.get("segments") or []
            stt_result = {
                "language": merged_doc.get("language"),
                "text": merged_doc.get("full_text", ""),
                "segments": speaker_transcript,
            }
        elif resume and paths.raw_transcript.exists():
            raw_doc = self.storage_service.load_json(paths.raw_transcript)
            stt_result = {
                "language": raw_doc.get("language"),
                "text": raw_doc.get("full_text", ""),
                "segments": raw_doc.get("segments") or [],
            }
            ddoc = (
                self.storage_service.load_json(paths.diarization)
                if paths.diarization.exists()
                else {}
            )
            diarization_segments = (
                ddoc.get("segments", []) if isinstance(ddoc, dict) else []
            )
            whisper_segs = clean_segments(stt_result["segments"])
            if STT_BACKEND == "openai_diarize":
                speaker_transcript = whisper_segs
            else:
                speaker_transcript = assign_speakers_to_transcript(
                    whisper_segs,
                    diarization_segments,
                )
            self.storage_service.save_json(
                {
                    "meeting_id": job_name,
                    "stt_backend": STT_BACKEND,
                    "language": stt_result.get("language"),
                    "full_text": stt_result.get("text", ""),
                    "segments": speaker_transcript,
                },
                paths.merged_transcript,
            )
        else:
            stt_result = self._stt.transcribe(paths.wav)
            if STT_BACKEND == "openai_diarize":
                self.storage_service.save_json(
                    {"meeting_id": job_name, "segments": []},
                    paths.diarization,
                )
                whisper_like = clean_segments(stt_result["segments"])
                raw_segments = [dict(s) for s in whisper_like]
                speaker_transcript = whisper_like
            else:
                whisper_like = clean_segments(stt_result["segments"])
                raw_segments = [dict(s) for s in whisper_like]
                self.storage_service.save_json(
                    {"meeting_id": job_name, "segments": diarization_segments},
                    paths.diarization,
                )
                speaker_transcript = assign_speakers_to_transcript(
                    whisper_like,
                    diarization_segments,
                )

            self.storage_service.save_json(
                {
                    "meeting_id": job_name,
                    "stt_backend": STT_BACKEND,
                    "schema": "raw_transcript_v1",
                    "language": stt_result.get("language"),
                    "full_text": stt_result.get("text", ""),
                    "segments": raw_segments,
                },
                paths.raw_transcript,
            )
            self.storage_service.save_json(
                {
                    "meeting_id": job_name,
                    "stt_backend": STT_BACKEND,
                    "language": stt_result.get("language"),
                    "full_text": stt_result.get("text", ""),
                    "segments": speaker_transcript,
                },
                paths.merged_transcript,
            )

        ms_stt = int((time.monotonic() - t_stt) * 1000)
        pipeline_meta["stages_ms"]["stt_and_transcripts"] = ms_stt
        has_diarization = has_usable_diarization(paths, self.storage_service, STT_BACKEND)
        log_stage(
            log,
            stage="stt_transcripts",
            duration_ms=ms_stt,
            step=2,
            total=_FLOW_TOTAL,
            detail={
                "segments": len(speaker_transcript),
                "language": stt_result.get("language") or "—",
                "diarization": "yes" if has_diarization else "no",
            },
        )

        # --- 6) Extracted fields ---
        t_ex = time.monotonic()
        if resume and paths.extracted_fields.exists():
            extracted_fields = self.storage_service.load_json(paths.extracted_fields)
        else:
            extracted_fields = self.field_extractor.extract(speaker_transcript)
            self.storage_service.save_json(extracted_fields, paths.extracted_fields)
        ms_ex = int((time.monotonic() - t_ex) * 1000)
        pipeline_meta["stages_ms"]["extracted_fields"] = ms_ex
        log_stage(log, stage="field_extractor", duration_ms=ms_ex, step=3, total=_FLOW_TOTAL)

        # --- 7) Risk report ---
        t_risk = time.monotonic()
        if resume and paths.risk_report.exists():
            risk_report = self.storage_service.load_json(paths.risk_report)
        else:
            risk_report = self.risk_service.generate(extracted_fields, speaker_transcript)
            self.storage_service.save_json(risk_report, paths.risk_report)
        ms_risk = int((time.monotonic() - t_risk) * 1000)
        pipeline_meta["stages_ms"]["risk_report"] = ms_risk
        log_stage(log, stage="risk_report", duration_ms=ms_risk, step=4, total=_FLOW_TOTAL)

        # --- 8) Meeting intel + optional role-mapped transcript (only with diarization) ---
        t_intel = time.monotonic()
        meeting_intel: Dict[str, Any]
        if has_diarization and resume and paths.role_mapped_transcript.exists():
            role_doc = self.storage_service.load_json(paths.role_mapped_transcript)
            transcript_with_roles = role_doc.get("segments") or []
            summary = role_doc.get("summary") or ""
            speaker_map = role_doc.get("speaker_map") or {}
            meeting_intel = {
                "summary": summary,
                "speaker_map": speaker_map,
                "transcript_with_roles": transcript_with_roles,
                "role_method": role_doc.get("role_method"),
                "burst_count": role_doc.get("burst_count"),
            }
            for k in ("speaker_intel_note", "raw_meeting_intel_output"):
                if k in role_doc:
                    meeting_intel[k] = role_doc[k]
        elif has_diarization:
            meeting_intel = enrich_meeting_intel(speaker_transcript, extracted_fields)
            summary = meeting_intel.get("summary") or ""
            speaker_map = meeting_intel.get("speaker_map") or {}
            transcript_with_roles = (
                meeting_intel.get("transcript_with_roles") or speaker_transcript
            )
            role_payload = {
                "meeting_id": job_name,
                "summary": summary,
                "speaker_map": speaker_map,
                "role_method": meeting_intel.get("role_method"),
                "burst_count": meeting_intel.get("burst_count"),
                "segments": transcript_with_roles,
            }
            for k in ("speaker_intel_note", "raw_meeting_intel_output"):
                if k in meeting_intel:
                    role_payload[k] = meeting_intel[k]
            self.storage_service.save_json(role_payload, paths.role_mapped_transcript)
        else:
            meeting_intel = meeting_intel_without_diarization(
                speaker_transcript, extracted_fields
            )
            summary = meeting_intel.get("summary") or ""
            speaker_map = meeting_intel.get("speaker_map") or {}
            transcript_with_roles = (
                meeting_intel.get("transcript_with_roles") or speaker_transcript
            )
        ms_intel = int((time.monotonic() - t_intel) * 1000)
        pipeline_meta["stages_ms"]["meeting_intel"] = ms_intel
        log_stage(
            log,
            stage="meeting_intel",
            duration_ms=ms_intel,
            step=5,
            total=_FLOW_TOTAL,
            detail={
                "diarization": "yes" if has_diarization else "no",
                "role_method": meeting_intel.get("role_method") or "—",
            },
        )

        # --- 9) Assessment (polished + question coverage + call quality) ---
        t_as = time.monotonic()
        if (
            resume
            and paths.polished_json.exists()
            and paths.question_assessment.exists()
            and paths.call_quality_report.exists()
        ):
            polished_pkg = self.storage_service.load_json(paths.polished_json)
            qa_doc = self.storage_service.load_json(paths.question_assessment)
            assessment_pkg = {
                "polished_transcript": polished_pkg.get("polished_transcript") or {},
                "topic_wise_summary": polished_pkg.get("topic_wise_summary") or [],
                "question_coverage": qa_doc.get("question_coverage") or [],
                "call_quality_report": self.storage_service.load_json(
                    paths.call_quality_report
                ),
                "assessment_note": "",
            }
        else:
            assessment_pkg = self.call_assessment.build(
                transcript_with_roles, extracted_fields
            )
            polished_body = assessment_pkg["polished_transcript"]
            topics = assessment_pkg.get("topic_wise_summary") or []
            self.storage_service.save_json(
                {"polished_transcript": polished_body, "topic_wise_summary": topics},
                paths.polished_json,
            )
            cq = assessment_pkg["call_quality_report"]
            conf = cq.get("conformance") or {}
            self.storage_service.save_json(
                {
                    "meeting_id": job_name,
                    "discovery_question_template": [dict(q) for q in DISCOVERY_QUESTIONS],
                    "question_coverage": assessment_pkg["question_coverage"],
                    "conformance": conf,
                },
                paths.question_assessment,
            )
            self.storage_service.save_json(cq, paths.call_quality_report)
        ms_as = int((time.monotonic() - t_as) * 1000)
        pipeline_meta["stages_ms"]["assessment"] = ms_as
        cq_score = assessment_pkg["call_quality_report"].get("conformance_score_0_100")
        log_stage(
            log,
            stage="call_assessment",
            duration_ms=ms_as,
            step=6,
            total=_FLOW_TOTAL,
            detail={"conformance_0_100": cq_score if cq_score is not None else "—"},
        )

        polished_body = assessment_pkg["polished_transcript"]
        topics = assessment_pkg.get("topic_wise_summary") or []
        cq_final = assessment_pkg["call_quality_report"]
        paths.polished_md.write_text(
            polished_to_markdown(
                job_name,
                polished_body,
                topics,
                executive_summary=summary,
                call_quality_report=cq_final,
                question_coverage=assessment_pkg["question_coverage"],
                discovery_template=[dict(q) for q in DISCOVERY_QUESTIONS],
            ),
            encoding="utf-8",
        )

        t_vid = time.monotonic()
        video_metadata = probe_video_metadata(mp4_path)
        ms_vid = int((time.monotonic() - t_vid) * 1000)
        pipeline_meta["stages_ms"]["video_metadata"] = ms_vid
        vm_err = video_metadata.get("error") if isinstance(video_metadata, dict) else None
        log_stage(
            log,
            stage="video_metadata",
            duration_ms=ms_vid,
            step=7,
            total=_FLOW_TOTAL,
            detail={"ffprobe": "ok" if not vm_err else str(vm_err)},
        )

        artifact_paths: Dict[str, str] = {
            "wav": paths.rel(paths.wav),
            "raw_transcript": paths.rel(paths.raw_transcript),
            "diarization": paths.rel(paths.diarization),
            "merged_transcript": paths.rel(paths.merged_transcript),
            "extracted_fields": paths.rel(paths.extracted_fields),
            "question_assessment": paths.rel(paths.question_assessment),
            "risk_report": paths.rel(paths.risk_report),
            "polished_json": paths.rel(paths.polished_json),
            "polished_md": paths.rel(paths.polished_md),
            "call_quality_report": paths.rel(paths.call_quality_report),
            "final_report": paths.rel(paths.final_report),
            "metadata": paths.rel(paths.metadata),
        }
        if has_diarization:
            artifact_paths["role_mapped_transcript"] = paths.rel(paths.role_mapped_transcript)

        final_output: Dict[str, Any] = {
            "meeting_id": job_name,
            "job_id": job_name,
            "source_file": str(mp4_path),
            "audio_file": str(paths.wav),
            "stt_backend": STT_BACKEND,
            "output_schema_version": 3,
            "video_metadata": video_metadata,
            "pipeline": pipeline_meta,
            "has_diarization": has_diarization,
            "summary": summary,
            "speaker_map": speaker_map,
            "role_method": meeting_intel.get("role_method"),
            "burst_count": meeting_intel.get("burst_count"),
            "discovery_question_template": [dict(q) for q in DISCOVERY_QUESTIONS],
            "polished_transcript": assessment_pkg["polished_transcript"],
            "topic_wise_summary": assessment_pkg.get("topic_wise_summary") or [],
            "question_coverage": assessment_pkg["question_coverage"],
            "call_quality_report": assessment_pkg["call_quality_report"],
            "transcript": transcript_with_roles,
            "extracted_fields": extracted_fields,
            "risk_report": risk_report,
            "artifact_paths": artifact_paths,
        }
        if assessment_pkg.get("assessment_note"):
            final_output["assessment_note"] = assessment_pkg["assessment_note"]
        for k in ("speaker_intel_note", "raw_meeting_intel_output"):
            if k in meeting_intel:
                final_output[k] = meeting_intel[k]

        t_persist = time.monotonic()
        self.storage_service.save_json(
            {
                "meeting_id": job_name,
                "source_file": str(mp4_path),
                "video_metadata": video_metadata,
            },
            paths.metadata,
        )

        # Legacy: single transcript JSON under ``data/outputs/`` (no duplicate full ``_result``).
        legacy_transcript = OUTPUT_DIR / f"{job_name}_transcript.json"
        self.storage_service.save_json(
            {"language": stt_result.get("language"), "segments": transcript_with_roles},
            legacy_transcript,
        )

        pipeline_meta["stages_ms"]["persist"] = int((time.monotonic() - t_persist) * 1000)
        pipeline_meta["stages_ms"]["total"] = int((time.monotonic() - t0) * 1000)
        self.storage_service.save_json(final_output, paths.final_report)

        log_stage(
            log,
            stage="persist_outputs",
            duration_ms=pipeline_meta["stages_ms"]["persist"],
            step=8,
            total=_FLOW_TOTAL,
            detail={
                "final_report": paths.rel(paths.final_report),
                "total_ms": pipeline_meta["stages_ms"]["total"],
            },
        )

        return final_output
