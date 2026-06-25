"""Playwright-based meeting bot that joins meetings and captures audio."""

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import AsyncGenerator, Optional

from meeting_agent.core.config import settings
from meeting_agent.core.exceptions import BotJoinError, BotDisconnectedError

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - playwright is an optional dependency
    async_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment, misc]
    _PLAYWRIGHT_AVAILABLE = False

# Accessible names of the buttons shown once you are signed in and ready to
# enter a Google Meet call ("green room"). They only appear after auth.
_GOOGLE_MEET_JOIN_RE = re.compile(r"Ask to join|Join now", re.IGNORECASE)
_LEAVE_CALL_RE = re.compile(r"Leave call|End call", re.IGNORECASE)


def _chrome_user_agent(executable_path: Optional[str] = None) -> str:
    """Return a current ``Chrome/<major>`` user-agent matching the bundled engine.

    Google Meet rejects clients whose ``navigator.userAgent`` reports a Chrome
    major version outside its supported window ("Your browser version is no
    longer supported"). The version is therefore read from the Chromium binary
    Playwright actually ships rather than pinned to a hardcoded string that goes
    stale as the engine updates. The brand is ``Chrome`` (never
    ``HeadlessChrome``) so the same value works whether the bot runs headed or
    headless.
    """
    major = ""
    if executable_path:
        try:
            proc = subprocess.run(
                [executable_path, "--version"], capture_output=True, text=True, timeout=10
            )
            match = re.search(r"(\d+)\.", proc.stdout)
            if match:
                major = match.group(1)
        except Exception:
            logger.warning("Could not determine Chromium version; using fallback UA")
    major = major or "148"
    return (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
    )


class PlaywrightMeetingBot:
    """Joins meetings via browser automation using Playwright.

    Supports Google Meet, Zoom (web), and Microsoft Teams (web).
    """

    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._in_meeting = False
        self._participants: list[str] = []

    async def join(self, meeting_url: str, display_name: str = "Meeting Agent") -> None:
        """Join a meeting at the given URL."""
        if self._in_meeting:
            raise BotJoinError(meeting_url, "Already in a meeting")

        if not _PLAYWRIGHT_AVAILABLE:
            raise BotJoinError(
                meeting_url,
                "playwright not installed. Run: pip install playwright && playwright install chromium",
            )

        # A persistent profile keeps the Google session between runs, so the
        # "sign in once" workflow described in the testing guide actually holds.
        user_data_dir = Path(settings.bot_user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._pw = await async_playwright().start()
            user_agent = _chrome_user_agent(self._pw.chromium.executable_path)
            self._context = await self._pw.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=settings.bot_headless,
                viewport={"width": 1280, "height": 720},
                user_agent=user_agent,
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    # Make the automated Chromium look like a normal browser to
                    # Google Meet (hides the "controlled by automation" signal).
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            # A persistent context opens with one page already available.
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            self._page.set_default_timeout(settings.bot_browser_timeout * 1000)

            logger.info("Navigating to meeting: %s", meeting_url)
            await self._page.goto(meeting_url, wait_until="networkidle")

            # Platform-specific join flow
            platform = self._detect_platform(meeting_url)
            await self._handle_join(platform, display_name)

            self._in_meeting = True
            logger.info("Successfully joined meeting: %s", meeting_url)

        except BotJoinError:
            raise
        except Exception as e:
            await self.leave()
            raise BotJoinError(meeting_url, str(e))

    def _detect_platform(self, url: str) -> str:
        """Detect the meeting platform from the URL."""
        url_lower = url.lower()
        if "meet.google.com" in url_lower:
            return "google_meet"
        elif "zoom.us" in url_lower:
            return "zoom"
        elif "teams.microsoft.com" in url_lower:
            return "teams"
        return "other"

    async def _handle_join(self, platform: str, display_name: str) -> None:
        """Handle platform-specific join interactions."""
        if platform == "google_meet":
            await self._join_google_meet(display_name)
        elif platform == "zoom":
            await self._join_zoom(display_name)
        elif platform == "teams":
            await self._join_teams(display_name)
        else:
            logger.warning("Unknown platform — attempting generic join")

    async def _join_google_meet(self, display_name: str) -> None:
        """Handle Google Meet join flow.

        Requires an authenticated Google session. On the first run (or when the
        session has expired), run headed so you can sign in manually; the
        persistent profile remembers the session for subsequent runs.
        """
        join_btn = self._page.get_by_role("button", name=_GOOGLE_MEET_JOIN_RE)
        try:
            # Wait for the authenticated join screen, allowing time to sign in.
            await join_btn.wait_for(
                state="visible",
                timeout=settings.bot_login_timeout_seconds * 1000,
            )
        except PlaywrightTimeoutError as e:
            raise BotJoinError(
                "Google Meet",
                "The 'Ask to join' / 'Join now' screen never appeared. The bot is "
                "likely not signed in: set BOT_HEADLESS=false and complete the Google "
                "sign-in in the browser window (it is saved for future runs).",
            ) from e

        # Optional: avoid broadcasting the bot's own mic/camera.
        for label in ("Turn off microphone", "Turn off camera"):
            try:
                toggle = self._page.get_by_role("button", name=label)
                if await toggle.is_visible():
                    await toggle.click()
            except Exception:
                pass

        await join_btn.click()
        logger.info("Joined Google Meet as '%s'", display_name)

    async def _join_zoom(self, display_name: str) -> None:
        """Handle Zoom web client join flow."""
        try:
            await asyncio.sleep(2)
            # Click "Join from Your Browser" if available
            try:
                browser_join = self._page.get_by_text("Join from Your Browser")
                if await browser_join.is_visible():
                    await browser_join.click()
                    await asyncio.sleep(2)
            except Exception:
                pass

            # Enter name
            try:
                name_input = self._page.locator('input[name="inputname"]')
                if await name_input.is_visible():
                    await name_input.fill(display_name)
            except Exception:
                pass

            join_btn = self._page.get_by_role("button", name="Join")
            await join_btn.click()
            logger.info("Joined Zoom as '%s'", display_name)

        except Exception as e:
            raise BotJoinError("Zoom", f"Join flow failed: {e}")

    async def _join_teams(self, display_name: str) -> None:
        """Handle Microsoft Teams web join flow."""
        try:
            await asyncio.sleep(2)
            join_btn = self._page.get_by_role("button", name="Join now")
            await join_btn.click()
            logger.info("Joined Teams as '%s'", display_name)
        except Exception as e:
            raise BotJoinError("Teams", f"Join flow failed: {e}")

    async def leave(self) -> None:
        """Leave the current meeting and close browser."""
        if self._page:
            try:
                # Try to click leave/end call button
                leave_btn = self._page.get_by_role("button", name=_LEAVE_CALL_RE)
                if await leave_btn.is_visible():
                    await leave_btn.click()
            except Exception:
                pass

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass

        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass

        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._in_meeting = False
        logger.info("Left meeting and closed browser")

    async def get_live_captions(self) -> AsyncGenerator[str, None]:
        """Yield live caption text as it appears in the meeting UI."""
        if not self._in_meeting or not self._page:
            return

        seen = set()
        while self._in_meeting:
            try:
                # Try to find caption elements (platform-specific)
                captions = await self._page.locator("[aria-live='polite'], .caption-text").all_text_contents()
                for caption in captions:
                    text = caption.strip()
                    if text and text not in seen:
                        seen.add(text)
                        yield text
                await asyncio.sleep(1)
            except Exception:
                break

    async def is_in_meeting(self) -> bool:
        """Check if the bot is currently in a meeting."""
        return self._in_meeting

    async def get_participants(self) -> list[str]:
        """Get the list of current participant names."""
        if not self._in_meeting or not self._page:
            return []

        try:
            # Try to open participants panel
            participants_btn = self._page.get_by_role("button", name="Participants")
            if await participants_btn.is_visible():
                await participants_btn.click()
                await asyncio.sleep(1)
                names = await self._page.locator("[data-participant-id] .zWGUib").all_text_contents()
                return [n.strip() for n in names if n.strip()]
        except Exception:
            pass
        return self._participants
