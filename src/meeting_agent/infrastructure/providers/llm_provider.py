"""OpenAI-based LLM provider for text generation and structured output."""

import json
import logging
from typing import Optional

from meeting_agent.core.config import settings
from meeting_agent.core.exceptions import LLMError

logger = logging.getLogger(__name__)


class OpenAILLMProvider:
    """LLM provider using the OpenAI API (GPT-4o / GPT-4o-mini etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key or settings.get_openai_api_key()
        self.model_name = model or settings.openai_model
        self._max_tokens = max_tokens or settings.openai_max_tokens
        self._temperature = temperature or settings.openai_temperature
        self._base_url = base_url or settings.openai_base_url or None
        self._client = None

    def _get_client(self):
        """Lazy-initialize the OpenAI client."""
        if self._client is None:
            if not self._api_key:
                raise LLMError("OpenAI API key not configured")
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
                logger.info(
                    "OpenAI client initialized (model: %s, base_url: %s)",
                    self.model_name,
                    self._base_url or "default (OpenAI)",
                )
            except ImportError:
                raise LLMError("openai package not installed. Run: pip install openai")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate plain text from a prompt."""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            content = response.choices[0].message.content
            logger.debug(
                "LLM response: %d chars, tokens: prompt=%s completion=%s",
                len(content) if content else 0,
                response.usage.prompt_tokens if response.usage else "?",
                response.usage.completion_tokens if response.usage else "?",
            )
            return content or ""
        except Exception as e:
            raise LLMError(f"OpenAI API error: {e}")

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Generate a JSON response from a prompt.

        Tries response_format=json_object first, falls back to parsing text.
        """
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content

            if not content:
                raise LLMError("Empty response from LLM")

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1).strip())
                raise LLMError(f"LLM returned invalid JSON: {content[:200]}")

        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"OpenAI API error: {e}")
