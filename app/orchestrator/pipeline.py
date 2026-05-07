from pathlib import Path
from app.config import AUDIO_DIR, OUTPUT_DIR, WHISPER_MODEL_SIZE, ENABLE_DIARIZATION
from app.services.audio_extractor import extract_audio
from app.services.stt_service import STTService
from app.services.transcript_cleaner import clean_segments
from app.services.field_extractor import FieldExtractor
from app.services.risk_report_service import RiskReportService
from app.services.storage_service import StorageService


class Pipeline:
    def __init__(self):
        self.stt_service = STTService(model_size=WHISPER_MODEL_SIZE)
        self.field_extractor = FieldExtractor()
        self.risk_service = RiskReportService()
        self.storage_service = StorageService()

    def run(self, mp4_path: str) -> dict:
        mp4_path = Path(mp4_path)
        job_name = mp4_path.stem

        audio_path = AUDIO_DIR / f"{job_name}.wav"
        transcript_path = OUTPUT_DIR / f"{job_name}_transcript.json"
        result_path = OUTPUT_DIR / f"{job_name}_result.json"

        # Step 1: Extract audio
        extract_audio(mp4_path, audio_path)

        # Step 2: STT
        stt_result = self.stt_service.transcribe(audio_path)
        cleaned_segments = clean_segments(stt_result["segments"])

        # Step 3: Diarization (optional for cleaner/faster MVP runs)
        speaker_segments = []
        if ENABLE_DIARIZATION:
            try:
                from app.services.diarization_service import DiarizationService

                diarization_service = DiarizationService()
                speaker_segments = diarization_service.diarize(audio_path)
            except Exception:
                speaker_segments = []

        # Step 4: Sales field extraction
        extracted_fields = self.field_extractor.extract(cleaned_segments)

        # Step 5: Risk report
        risk_report = self.risk_service.generate(extracted_fields, cleaned_segments)

        # Step 6: Final output
        final_output = {
            "job_id": job_name,
            "source_file": str(mp4_path),
            "audio_file": str(audio_path),
            "transcript": cleaned_segments,
            "speaker_segments": speaker_segments,
            "extracted_fields": extracted_fields,
            "risk_report": risk_report,
        }

        self.storage_service.save_json(
            {"language": stt_result.get("language"), "segments": cleaned_segments},
            transcript_path,
        )
        self.storage_service.save_json(final_output, result_path)

        return final_output