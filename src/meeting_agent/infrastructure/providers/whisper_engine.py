"""Whisper-based speech-to-text transcription engine."""

import logging
import os
from typing import Optional

from meeting_agent.core.config import settings
from meeting_agent.core.domain_models import Transcript, TranscriptSegment
from meeting_agent.core.exceptions import TranscriptionError

logger = logging.getLogger(__name__)


class WhisperEngine:
    """Transcribes audio files using faster-whisper."""

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self._model_size = model_size or settings.whisper_model_size
        self._device = device or settings.whisper_device
        self._compute_type = compute_type or settings.whisper_compute_type
        self._model = None

    def _load_model(self):
        """Lazy-load the whisper model on first use."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info(
                    "Loading Whisper model '%s' on %s with %s compute...",
                    self._model_size,
                    self._device,
                    self._compute_type,
                )
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info("Whisper model loaded successfully")
            except ImportError:
                raise TranscriptionError(
                    "faster-whisper not installed. Run: pip install faster-whisper"
                )
            except Exception as e:
                raise TranscriptionError(f"Failed to load Whisper model: {e}")

    async def transcribe_file(self, audio_path: str) -> dict:
        """Transcribe an audio file and return transcript with segments."""
        if not os.path.exists(audio_path):
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        self._load_model()

        try:
            language = settings.whisper_language
            segments_generator, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            segments = []
            full_text_parts = []
            for i, segment in enumerate(segments_generator):
                seg = {
                    "text": segment.text.strip(),
                    "start_time": segment.start,
                    "end_time": segment.end,
                    "speaker": None,  # Speaker diarization can be added later
                    "confidence": segment.avg_logprob,
                    "segment_index": i,
                }
                segments.append(seg)
                full_text_parts.append(segment.text.strip())

            full_text = " ".join(full_text_parts)
            word_count = len(full_text.split()) if full_text else 0

            result = {
                "full_text": full_text,
                "language": info.language if info.language else "en",
                "duration_seconds": info.duration if info.duration else 0.0,
                "word_count": word_count,
                "segments": segments,
            }

            logger.info(
                "Transcribed %s: %d segments, %d words, %.1fs",
                audio_path,
                len(segments),
                word_count,
                result["duration_seconds"],
            )
            return result

        except TranscriptionError:
            raise
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {e}")

    async def transcribe_chunk(self, audio_bytes: bytes) -> list[dict]:
        """Transcribe a chunk of audio bytes (for real-time processing)."""
        import tempfile
        import soundfile as sf
        import numpy as np

        self._load_model()

        try:
            # Write bytes to a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                # Assume raw float32 PCM at configured sample rate
                audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
                sf.write(tmp_path, audio_array, settings.bot_audio_sample_rate)

            try:
                segments_generator, info = self._model.transcribe(
                    tmp_path,
                    language=settings.whisper_language,
                    beam_size=3,
                )
                segments = []
                for i, segment in enumerate(segments_generator):
                    segments.append({
                        "text": segment.text.strip(),
                        "start_time": segment.start,
                        "end_time": segment.end,
                        "confidence": segment.avg_logprob,
                        "segment_index": i,
                    })
                return segments
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            raise TranscriptionError(f"Chunk transcription failed: {e}")
