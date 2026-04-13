from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import DATA_DIR


TOKEN_RE = re.compile(r"[A-Za-z0-9_./+-]+")


@dataclass
class KnowledgeChunk:
    chunk_id: str
    title: str
    source_type: str
    source_name: str
    source_path: str
    url: str | None
    text: str


class KnowledgeBase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DATA_DIR / "knowledge_base.json"
        self.chunks = self._load_chunks()
        self.doc_freq = self._build_doc_freq(self.chunks)
        self.doc_count = len(self.chunks)

    def _load_chunks(self) -> list[KnowledgeChunk]:
        payload = json.loads(self.path.read_text())
        return [KnowledgeChunk(**item) for item in payload["chunks"]]

    def _build_doc_freq(self, chunks: Iterable[KnowledgeChunk]) -> Counter[str]:
        freq: Counter[str] = Counter()
        for chunk in chunks:
            freq.update(set(self.tokenize(chunk.text)))
        return freq

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return [token.lower() for token in TOKEN_RE.findall(text)]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        query_tokens = self.tokenize(query)
        expansion = self._expand_query(query)
        query_tokens.extend(expansion)
        if not query_tokens:
            return []

        query_counts = Counter(query_tokens)
        scored: list[tuple[float, KnowledgeChunk]] = []
        for chunk in self.chunks:
            score = self._score_chunk(chunk, query_counts, query.lower(), expansion)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, chunk in scored[:limit]:
            results.append(
                {
                    "score": round(score, 4),
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.title,
                    "source_type": chunk.source_type,
                    "source_name": chunk.source_name,
                    "source_path": chunk.source_path,
                    "url": chunk.url,
                    "excerpt": self._excerpt(chunk.text, query_tokens),
                    "text": chunk.text,
                }
            )
        return results

    def _score_chunk(self, chunk: KnowledgeChunk, query_counts: Counter[str], raw_query: str, expansion: list[str]) -> float:
        chunk_tokens = self.tokenize(chunk.text)
        if not chunk_tokens:
            return 0.0
        counts = Counter(chunk_tokens)
        length = len(chunk_tokens)
        score = 0.0
        for token, weight in query_counts.items():
            tf = counts[token] / length
            if tf == 0:
                continue
            df = self.doc_freq.get(token, 0)
            idf = math.log(1 + (self.doc_count / (1 + df)))
            score += weight * tf * idf
        if chunk.source_type == "resume":
            score *= 1.2
        if any(term in raw_query for term in ["fit", "right person", "why you", "background"]) and chunk.source_type == "resume":
            score *= 2.4
        if any(term in raw_query for term in ["fit", "right person", "why you", "background"]) and "profile" in chunk.text.lower():
            score *= 1.6
        if expansion and any(token in chunk.text.lower() for token in expansion):
            score *= 1.15
        if any(token in chunk.title.lower() for token in query_counts):
            score *= 1.1
        return score

    @staticmethod
    def _expand_query(query: str) -> list[str]:
        lowered = query.lower()
        extras: list[str] = []
        if any(term in lowered for term in ["fit", "right person", "why you", "background"]):
            extras.extend(["experience", "skills", "projects", "rag", "machine", "learning"])
        if "github" in lowered or "repo" in lowered or "project" in lowered:
            extras.extend(["project", "built", "tech", "tradeoffs"])
        if "availability" in lowered or "book" in lowered or "schedule" in lowered:
            extras.extend(["availability", "calendar", "interview"])
        return extras

    @staticmethod
    def _excerpt(text: str, query_tokens: list[str], max_len: int = 280) -> str:
        lowered = text.lower()
        hit = -1
        for token in query_tokens:
            hit = lowered.find(token.lower())
            if hit >= 0:
                break
        if hit < 0:
            return text[:max_len].strip()
        start = max(0, hit - 80)
        end = min(len(text), hit + max_len - 80)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet
