"""
Transcription Engine — WhisperX (preferred) + Pyannote diarization,
faster-whisper as the always-installed fallback.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    def __init__(self, model_size: str = "base", device: str = "auto", language: str | None = None):
        self.model_size = model_size
        self.language = language
        self.device = self._detect_device() if device == "auto" else device
        self._model = None
        self._diarizer = None
        self._is_fw = False

    def _detect_device(self) -> str:
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except Exception:
            pass
        return "cpu"

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            import whisperx  # type: ignore

            ct = "float16" if self.device == "cuda" else "int8"
            self._model = whisperx.load_model(
                self.model_size, self.device, compute_type=ct, language=self.language
            )
            self._is_fw = False
            logger.info("WhisperX loaded: %s on %s", self.model_size, self.device)
        except Exception:
            from faster_whisper import WhisperModel

            # faster-whisper expects a CPU-friendly device label
            fw_device = "cpu" if self.device in {"mps", "auto"} else self.device
            self._model = WhisperModel(self.model_size, device=fw_device, compute_type="int8")
            self._is_fw = True
            logger.info("faster-whisper loaded: %s on %s", self.model_size, fw_device)

    def _load_diarizer(self):
        if self._diarizer is not None:
            return self._diarizer
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            logger.warning("HUGGINGFACE_TOKEN not set — speaker diarization disabled")
            return None
        try:
            import torch  # type: ignore
            from pyannote.audio import Pipeline  # type: ignore

            self._diarizer = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1", use_auth_token=hf_token
            )
            dev = torch.device("cpu" if self.device == "mps" else self.device)
            self._diarizer.to(dev)
        except Exception as e:
            logger.error("Diarization load failed: %s", e)
        return self._diarizer

    async def transcribe_call(self, call_id: str, audio_path: str, db: AsyncSession) -> list[dict]:
        await db.execute(
            text("UPDATE calls SET transcription_status='processing' WHERE id=:id"),
            {"id": call_id},
        )
        await db.commit()
        try:
            self._load_model()
            if self._is_fw:
                segments = self._fw_transcribe(audio_path)
            else:
                segments = self._wx_transcribe(audio_path)

            for seg in segments:
                await db.execute(
                    text(
                        """
                        INSERT INTO call_transcripts
                            (call_id, speaker, text, start_time, end_time, confidence)
                        VALUES(:cid, :spk, :txt, :start, :end, :conf)
                        """
                    ),
                    {
                        "cid": call_id,
                        "spk": seg.get("speaker", "UNKNOWN"),
                        "txt": (seg.get("text") or "").strip(),
                        "start": seg.get("start"),
                        "end": seg.get("end"),
                        "conf": seg.get("confidence"),
                    },
                )
            await db.commit()
            await db.execute(
                text("UPDATE calls SET transcription_status='completed' WHERE id=:id"),
                {"id": call_id},
            )
            await db.commit()
            logger.info("Transcribed %s: %d segments", call_id, len(segments))
            return segments
        except Exception as e:
            logger.error("Transcription failed %s: %s", call_id, e)
            await db.execute(
                text("UPDATE calls SET transcription_status='failed' WHERE id=:id"),
                {"id": call_id},
            )
            await db.commit()
            return []

    def _wx_transcribe(self, audio_path: str) -> list[dict]:
        import whisperx  # type: ignore

        audio = whisperx.load_audio(audio_path)
        result = self._model.transcribe(audio, batch_size=16)
        lang = result.get("language", self.language or "tr")
        try:
            model_a, meta = whisperx.load_align_model(language_code=lang, device=self.device)
            result = whisperx.align(
                result["segments"],
                model_a,
                meta,
                audio,
                self.device,
                return_char_alignments=False,
            )
        except Exception as e:
            logger.warning("Alignment failed: %s", e)
        diarizer = self._load_diarizer()
        if diarizer:
            try:
                dr = diarizer(
                    {"waveform": None, "sample_rate": 16000}, min_speakers=2, max_speakers=4
                )
                result = whisperx.assign_word_speakers(dr, result)
            except Exception as e:
                logger.warning("Diarization failed: %s", e)
        return [
            {
                "speaker": s.get("speaker", "SPEAKER_0"),
                "text": s.get("text", ""),
                "start": s.get("start"),
                "end": s.get("end"),
            }
            for s in result.get("segments", [])
        ]

    def _fw_transcribe(self, audio_path: str) -> list[dict]:
        segs, _ = self._model.transcribe(
            audio_path, language=self.language, beam_size=5, word_timestamps=True
        )
        return [
            {"speaker": "SPEAKER_0", "text": s.text, "start": s.start, "end": s.end} for s in segs
        ]
