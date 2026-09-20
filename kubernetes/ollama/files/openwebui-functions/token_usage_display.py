"""
title: Token rate display
author: homelab
version: 1.0.0
required_open_webui_version: 0.9.0
"""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


class Filter:
    class Valves(BaseModel):
        priority: int = Field(default=10)

    def __init__(self) -> None:
        self.valves = self.Valves()

    async def outlet(
        self,
        body: dict[str, Any],
        *,
        __event_emitter__: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        messages = body.get("messages", [])
        assistant = next(
            (
                message
                for message in reversed(messages)
                if isinstance(message, dict) and message.get("role") == "assistant"
            ),
            None,
        )
        usage = assistant.get("usage", {}) if assistant else {}
        output_tokens = usage.get("eval_count")
        duration_ns = usage.get("eval_duration")

        if (
            __event_emitter__
            and isinstance(output_tokens, (int, float))
            and not isinstance(output_tokens, bool)
            and isinstance(duration_ns, (int, float))
            and not isinstance(duration_ns, bool)
            and duration_ns > 0
        ):
            tokens_per_second = output_tokens / (duration_ns / 1_000_000_000)
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"⚡ {tokens_per_second:.1f} t/s",
                        "done": True,
                    },
                }
            )

        return body
