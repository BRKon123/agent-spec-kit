"""Provider-routed structured LLM calls (shared by criteria judges and fuzz/shrink)."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, TypeAdapter

from agent_spec_kit.judges.router import parse_model_route

T = TypeVar("T", bound=BaseModel)


async def call_structured(
    *,
    model: str,
    system: str,
    user: str,
    response_model: type[T],
    temperature: float | None = None,
    timeout_s: float | None = None,
) -> T:
    """Call an LLM with structured output parsed into ``response_model``.

    ``model`` must be provider-prefixed, e.g. ``openai:gpt-4.1-mini`` or ``anthropic:claude-3-5-sonnet-20241022``.
    """
    provider, model_name = parse_model_route(model)
    if provider == "openai":
        return await _openai_structured(
            model_name=model_name,
            model_route=model,
            system=system,
            user=user,
            response_model=response_model,
            temperature=temperature,
            timeout_s=timeout_s,
        )
    if provider == "anthropic":
        return await _anthropic_structured(
            model_name=model_name,
            model_route=model,
            system=system,
            user=user,
            response_model=response_model,
            temperature=temperature,
            timeout_s=timeout_s,
        )
    raise ValueError(f"unsupported model provider {provider!r} in {model!r}")


async def _openai_structured(
    *,
    model_name: str,
    model_route: str,
    system: str,
    user: str,
    response_model: type[T],
    temperature: float | None,
    timeout_s: float | None,
) -> T:
    try:
        from openai import AsyncOpenAI, BadRequestError
    except ImportError as e:  # pragma: no cover - import guard
        raise RuntimeError("openai package is required for openai:* model routing") from e

    client = AsyncOpenAI(timeout=timeout_s)
    kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": response_model,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    try:
        completion = await client.beta.chat.completions.parse(**kwargs)
    except BadRequestError as e:
        msg = str(e).lower()
        if "temperature" not in msg or temperature is None:
            raise
        kwargs.pop("temperature", None)
        completion = await client.beta.chat.completions.parse(**kwargs)

    message = completion.choices[0].message
    parsed = message.parsed
    if parsed is None:
        raise RuntimeError(
            f"OpenAI structured call returned no parsed response (model={model_route!r})"
        )
    return parsed


async def _anthropic_structured(
    *,
    model_name: str,
    model_route: str,
    system: str,
    user: str,
    response_model: type[T],
    temperature: float | None,
    timeout_s: float | None,
) -> T:
    import json

    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:  # pragma: no cover - import guard
        raise RuntimeError("anthropic package is required for anthropic:* model routing") from e

    schema = TypeAdapter(response_model).json_schema()
    schema_hint = json.dumps(schema, ensure_ascii=True)
    augmented_user = (
        f"{user}\n\nReturn JSON only that validates against this JSON Schema:\n{schema_hint}"
    )

    client = AsyncAnthropic(timeout=timeout_s)
    request_kwargs: dict[str, object] = {
        "model": model_name,
        "max_tokens": 4096,
        "system": system + " Return JSON only, no markdown fences.",
    }
    if temperature is not None:
        request_kwargs["temperature"] = temperature

    response = await client.messages.create(
        **request_kwargs,
        messages=[{"role": "user", "content": augmented_user}],
    )
    text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
    if not text_blocks:
        raise RuntimeError(f"Anthropic structured call returned no text (model={model_route!r})")
    raw = text_blocks[0].strip()
    try:
        return TypeAdapter(response_model).validate_json(raw.encode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            f"Anthropic structured JSON parse failed (model={model_route!r}): {e}"
        ) from e


__all__ = ["call_structured"]
