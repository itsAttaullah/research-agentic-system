"""Extractive summarizer (no LLM required).

Produces a concise summary by ranking sentences on term frequency overlap
with the document. An LLM-backed summarizer can replace this later behind
the same tool name if desired.
"""

from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel, Field

from sra.core.errors import ToolExecutionError
from sra.core.ports.tools import ToolContext
from sra.tools.base import BaseTool

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z0-9']+")


class SummarizerInput(BaseModel):
    text: str = Field(min_length=1)
    max_sentences: int = Field(default=5, ge=1, le=20)


class SummarizerOutput(BaseModel):
    summary: str
    sentence_count: int
    source_chars: int


class SummarizerTool(BaseTool):
    name = "summarizer"
    description = (
        "Summarize long text extractively into the top N sentences. "
        "Use after fetching a long page/PDF when only the key points are needed."
    )
    input_schema = SummarizerInput
    output_schema = SummarizerOutput
    tags = ["compute", "nlp"]

    async def execute(self, payload: BaseModel, ctx: ToolContext) -> BaseModel:
        assert isinstance(payload, SummarizerInput)
        text = payload.text.strip()
        if not text:
            raise ToolExecutionError("Summarizer received empty text")

        sentences = [part.strip() for part in _SENTENCE_SPLIT.split(text) if part.strip()]
        if not sentences:
            sentences = [text]

        if len(sentences) <= payload.max_sentences:
            selected = sentences
        else:
            selected = _rank_sentences(sentences, payload.max_sentences)

        return SummarizerOutput(
            summary=" ".join(selected),
            sentence_count=len(selected),
            source_chars=len(text),
        )


def _rank_sentences(sentences: list[str], limit: int) -> list[str]:
    doc_words = [_WORD.findall(sentence.casefold()) for sentence in sentences]
    frequencies: Counter[str] = Counter(word for words in doc_words for word in words)
    if not frequencies:
        return sentences[:limit]

    scored: list[tuple[float, int, str]] = []
    for index, (sentence, words) in enumerate(zip(sentences, doc_words, strict=True)):
        score = 0.0 if not words else sum(frequencies[word] for word in words) / len(words)
        scored.append((score, index, sentence))

    top = sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]
    top_sorted = sorted(top, key=lambda item: item[1])
    return [sentence for _, _, sentence in top_sorted]
