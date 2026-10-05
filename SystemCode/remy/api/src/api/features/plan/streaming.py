import asyncio
import json
import logging
import re
from collections.abc import Iterable, Iterator

from api.core.errors import ErrorDetail, error_envelope
from api.core.exceptions import AppError
from .narrative import plan_text

logger = logging.getLogger(__name__)

KEEP_ALIVE_SECONDS = 10.0
KEEP_ALIVE = ": keep-alive\n\n"
FLUSH_WORDS = 100
WORD = re.compile(r"\S+")
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
STAGES = (
    ("loading", "Loading recipes"),
    ("selecting", "Choosing recipes that fit"),
    ("solving", "Balancing your days"),
)


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def progress(step: int) -> str:
    stage, message = STAGES[step - 1]
    return sse("progress", {"stage": stage, "message": message, "step": step, "total": len(STAGES)})


async def keep_alive_until_done(task: asyncio.Task, interval: float):
    while not task.done():
        await asyncio.wait({task}, timeout=interval)
        if not task.done():
            yield KEEP_ALIVE


def in_thread(fn, *args) -> asyncio.Task:
    return asyncio.create_task(asyncio.to_thread(fn, *args))


def _end_of_word(text: str, n: int) -> int | None:
    for count, match in enumerate(WORD.finditer(text), 1):
        if count == n:
            # A word that touches the end of the buffer may continue in the next piece.
            return match.end() if match.end() < len(text) else None
    return None


def word_chunks(pieces: Iterable[str], size: int = FLUSH_WORDS) -> Iterator[str]:
    """Buffer text until it holds `size` words, then flush them. The last chunk may be shorter."""
    buffer = ""
    for piece in pieces:
        buffer += piece
        while (cut := _end_of_word(buffer, size)) is not None:
            yield buffer[:cut]
            buffer = buffer[cut:]
    if buffer.strip():
        yield buffer


async def stream_plan(request, service, keep_alive_seconds: float = KEEP_ALIVE_SECONDS):
    try:
        yield progress(1)
        task = in_thread(service.fetch_candidates)
        async for ping in keep_alive_until_done(task, keep_alive_seconds):
            yield ping
        recipes = task.result()

        yield progress(2)
        task = in_thread(service.select_candidates, recipes, request)
        async for ping in keep_alive_until_done(task, keep_alive_seconds):
            yield ping
        candidates = task.result()

        yield progress(3)
        task = in_thread(service.solve, candidates, request)
        async for ping in keep_alive_until_done(task, keep_alive_seconds):
            yield ping
        days, relaxations = task.result()

        plan = service.build_response(days, relaxations, request)
        for chunk in word_chunks(plan_text(plan)):
            yield sse("text", {"text": chunk})
        yield sse("plan", plan.model_dump(mode="json"))
    except AppError as exc:
        details = [ErrorDetail(**item) for item in exc.details]
        yield sse("error", error_envelope(exc.code, exc.message, details))
    except Exception:
        logger.exception("Plan stream failed")
        yield sse("error", error_envelope("INTERNAL_ERROR", "An unexpected error occurred"))
