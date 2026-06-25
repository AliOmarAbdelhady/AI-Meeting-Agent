"""Audio recorder using sounddevice for capturing meeting audio."""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

from meeting_agent.core.config import settings
from meeting_agent.core.exceptions import AudioCaptureError

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the default input device to WAV files."""

    def __init__(self):
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._start_time: float = 0
        self._output_path: Optional[str] = None
        self._stream = None
        self._lock = threading.Lock()

    async def start_recording(self, output_filename: str) -> None:
        """Start recording audio to the specified file."""
        if self._recording:
            raise AudioCaptureError("Already recording")

        try:
            import sounddevice as sd
        except ImportError:
            raise AudioCaptureError("sounddevice not installed. Run: pip install sounddevice")

        output_dir = Path(settings.audio_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._output_path = str(output_dir / output_filename)

        self._frames = []
        self._recording = True
        self._start_time = time.time()

        sample_rate = settings.bot_audio_sample_rate
        channels = settings.bot_audio_channels

        try:
            self._stream = sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Audio recording started → %s", self._output_path)
        except Exception as e:
            self._recording = False
            raise AudioCaptureError(f"Failed to start audio stream: {e}") from e

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback for sounddevice to collect audio frames."""
        if status:
            logger.warning("Audio status: %s", status)
        if self._recording:
            self._frames.append(indata.copy())

    async def stop_recording(self) -> str:
        """Stop recording and save to WAV file. Returns the file path."""
        if not self._recording:
            raise AudioCaptureError("Not currently recording")

        self._recording = False

        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if not self._frames:
                raise AudioCaptureError("No audio data captured")

            try:
                import soundfile as sf
            except ImportError:
                raise AudioCaptureError("soundfile not installed. Run: pip install soundfile")

            audio_data = np.concatenate(self._frames, axis=0)
            sample_rate = settings.bot_audio_sample_rate

            sf.write(self._output_path, audio_data, sample_rate)
            duration = time.time() - self._start_time
            logger.info(
                "Audio saved → %s (%.1fs, %d samples)",
                self._output_path,
                duration,
                len(audio_data),
            )
            return self._output_path
        except AudioCaptureError:
            raise
        except Exception as e:
            raise AudioCaptureError(f"Failed to save audio: {e}") from e

    async def get_duration(self) -> float:
        """Get the current recording duration in seconds."""
        if not self._recording:
            return 0.0
        return time.time() - self._start_time

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
