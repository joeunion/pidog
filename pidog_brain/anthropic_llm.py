"""Anthropic/Claude API adapter for PiDog

This module provides Claude API support for the PiDog voice assistant framework.

Example:
    >>> from pidog.anthropic_llm import Anthropic as LLM
    >>> import os
    >>> llm = LLM(
    ...     api_key=os.environ.get("ANTHROPIC_API_KEY"),
    ...     model="claude-sonnet-4-20250514"
    ... )
    >>> llm.set_instructions("You are a helpful assistant.")
    >>> response = llm.prompt("Hello!", stream=True)
    >>> for word in response:
    ...     print(word, end="", flush=True)
"""

import logging
import requests
import json
import base64
from sunfounder_voice_assistant.llm.llm import LLM

logger = logging.getLogger(__name__)


# JSON Schema for structured outputs - guarantees valid JSON responses
# Note: Only supported on Claude Sonnet 4.5 and Opus 4.1+ (not Haiku yet)
# Note: params is a JSON string because strict mode requires additionalProperties:false on all objects
PIDOG_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "speech": {
                "type": "string",
                "description": "What PiDog says out loud"
            },
            "actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Physical actions to perform"
            },
            "tools": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "params": {
                            "type": "string",
                            "description": "JSON-encoded parameters object"
                        }
                    },
                    "required": ["name", "params"],
                    "additionalProperties": False
                },
                "description": "Tools to execute"
            }
        },
        "required": ["speech", "actions", "tools"],
        "additionalProperties": False
    }
}

# Models that support structured outputs
STRUCTURED_OUTPUT_MODELS = [
    "claude-sonnet-4-5-20250514",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250410",
    "claude-opus-4-5-20251101",
]


class Anthropic(LLM):
    """Anthropic/Claude API adapter for PiDog

    Args:
        api_key (str): Anthropic API key
        model (str, optional): Model name. Defaults to "claude-sonnet-4-20250514"
        max_tokens (int, optional): Max tokens in response. Defaults to 1024
        **kwargs: Additional arguments passed to base LLM class
    """

    def __init__(self, api_key=None, model="claude-haiku-4-5-20251001", max_tokens=1024, **kwargs):
        # Do not pass url/base_url to parent - we handle it differently
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.url = "https://api.anthropic.com/v1/messages"
        self.system_prompt = None
        self.max_tokens = max_tokens

    def add_message(self, role, content, image_path=None):
        """Add message to conversation history

        Handles Anthropic different message format:
        - System messages are stored separately (not in messages array)
        - Images use base64 source format instead of URL format
        - Text content must be non-empty

        Args:
            role (str): Message role ("system", "user", or "assistant")
            content (str): Message content
            image_path (str, optional): Path to image file. Defaults to None.
        """
        # Handle system message separately (Anthropic format)
        if role == "system":
            self.system_prompt = content
            return

        # Ensure content is a non-empty string (Anthropic requirement)
        if isinstance(content, str):
            content = content.strip()
        if not content:
            content = "Hello"  # Default for empty messages

        # Build content with optional image
        if image_path is not None:
            base64_img = self.get_base64_from_image(image_path)
            img_type = image_path.split(".")[-1].lower()
            # Map common extensions to media types
            media_type_map = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif",
                "webp": "image/webp",
            }
            media_type = media_type_map.get(img_type, "image/" + img_type)

            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_img,
                    },
                },
                {"type": "text", "text": content},
            ]

        self.messages.append({"role": role, "content": content})

        # Trim messages if over limit
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def chat(self, stream=False, output_format=None, **kwargs):
        """Send chat request to Anthropic API

        Args:
            stream (bool, optional): Enable streaming response. Defaults to False.
            output_format (dict, optional): Structured output format schema. Defaults to None.
            **kwargs: Additional parameters for the API

        Returns:
            requests.Response: API response object

        Raises:
            ValueError: If model or API key not set
        """
        if not self.model:
            raise ValueError("Model not set")

        if not self.api_key:
            raise ValueError("API key not set")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Add beta header for structured outputs if output_format is specified
        if output_format is not None:
            headers["anthropic-beta"] = "structured-outputs-2025-11-13"

        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": self.messages,
            "stream": stream,
        }

        # Add system prompt if set
        if self.system_prompt:
            data["system"] = self.system_prompt

        # Add structured output format if specified
        if output_format is not None:
            data["output_format"] = output_format

        # Add any extra parameters
        data.update(kwargs)
        for name, value in self.params.items():
            data[name] = value

        return requests.post(
            self.url, headers=headers, data=json.dumps(data), stream=stream
        )

    def decode_stream_response(self, line):
        """Decode Anthropic SSE stream response line

        Anthropic uses Server-Sent Events format with content_block_delta events.

        Args:
            line (str): SSE line to decode

        Returns:
            str: Decoded text content, or None if not a content event
        """
        if not line.startswith("data: "):
            return None

        chunk_str = line[6:]  # Remove "data: " prefix

        if chunk_str == "[DONE]":
            return None

        try:
            chunk = json.loads(chunk_str)
        except json.JSONDecodeError:
            return None

        # Handle content_block_delta events
        if chunk.get("type") == "content_block_delta":
            delta = chunk.get("delta", {})
            if delta.get("type") == "text_delta":
                return delta.get("text", "")

        # Handle error events
        if chunk.get("type") == "error":
            error = chunk.get("error", {})
            raise Exception("Anthropic API error: " + error.get("message", "Unknown error"))

        return None

    def _non_stream_response(self, response):
        """Parse non-streaming Anthropic API response

        Args:
            response (requests.Response): API response

        Returns:
            str: Response text content

        Raises:
            Exception: If API returns an error
        """
        if not response.ok:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            raise Exception(f"Anthropic API error ({response.status_code}): {error_msg}")

        data = response.json()

        # Check for errors
        if "error" in data:
            raise Exception("Anthropic API error: " + data["error"].get("message", "Unknown error"))

        # Handle stop_reason for structured outputs
        stop_reason = data.get("stop_reason")
        if stop_reason == "refusal":
            logger.warning("Claude refused the request for safety reasons")
            return '{"speech": "", "actions": [], "tools": []}'
        if stop_reason == "max_tokens":
            logger.warning("Response truncated due to max_tokens - may have invalid JSON")

        # Extract text from content blocks
        content = data.get("content", [])
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "".join(text_parts)
