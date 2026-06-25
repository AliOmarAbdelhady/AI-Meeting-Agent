class MeetingAgentError(Exception):
    """Base exception for the AI Meeting Agent application."""

    def __init__(self, message: str = "An error occurred", code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class MeetingNotFoundError(MeetingAgentError):
    def __init__(self, meeting_id: str):
        super().__init__(f"Meeting {meeting_id} not found", "MEETING_NOT_FOUND")


class MeetingAlreadyStartedError(MeetingAgentError):
    def __init__(self, meeting_id: str):
        super().__init__(f"Meeting {meeting_id} is already in progress", "MEETING_ALREADY_STARTED")


class MeetingNotReadyError(MeetingAgentError):
    def __init__(self, meeting_id: str, status: str):
        super().__init__(f"Meeting {meeting_id} is in status '{status}' and cannot perform this action", "MEETING_NOT_READY")


class BotJoinError(MeetingAgentError):
    def __init__(self, meeting_url: str, detail: str = ""):
        msg = f"Failed to join meeting: {meeting_url}"
        if detail:
            msg += f" - {detail}"
        super().__init__(msg, "BOT_JOIN_ERROR")


class BotDisconnectedError(MeetingAgentError):
    def __init__(self, meeting_id: str):
        super().__init__(f"Bot disconnected from meeting {meeting_id}", "BOT_DISCONNECTED")


class TranscriptionError(MeetingAgentError):
    def __init__(self, detail: str = ""):
        super().__init__(f"Transcription failed: {detail}", "TRANSCRIPTION_ERROR")


class LLMError(MeetingAgentError):
    def __init__(self, detail: str = ""):
        super().__init__(f"LLM request failed: {detail}", "LLM_ERROR")


class EmailSendError(MeetingAgentError):
    def __init__(self, detail: str = ""):
        super().__init__(f"Failed to send email: {detail}", "EMAIL_SEND_ERROR")


class AudioCaptureError(MeetingAgentError):
    def __init__(self, detail: str = ""):
        super().__init__(f"Audio capture failed: {detail}", "AUDIO_CAPTURE_ERROR")


class ConfigurationError(MeetingAgentError):
    def __init__(self, detail: str = ""):
        super().__init__(f"Configuration error: {detail}", "CONFIGURATION_ERROR")


class SummaryNotFoundError(MeetingAgentError):
    def __init__(self, meeting_id: str):
        super().__init__(f"Summary for meeting {meeting_id} not found", "SUMMARY_NOT_FOUND")


class TaskNotFoundError(MeetingAgentError):
    def __init__(self, task_id: str):
        super().__init__(f"Task {task_id} not found", "TASK_NOT_FOUND")
