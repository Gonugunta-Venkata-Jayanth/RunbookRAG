"""Load Markdown runbooks and split them into section-level chunks."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


@dataclass(frozen=True)
class Chunk:
    id: str  # "<doc>#<section-slug>"
    doc: str
    title: str
    section: str
    category: str
    tags: tuple[str, ...]
    text: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        return d

    @property
    def index_text(self) -> str:
        """Text that is indexed: title and section give every chunk its context."""
        return f"{self.title}. {self.section}. {' '.join(self.tags)}. {self.text}"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_runbook(doc_id: str, raw: str) -> list[Chunk]:
    match = FRONT_MATTER_RE.match(raw)
    if not match:
        raise ValueError(f"{doc_id}: missing front matter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    for required in ("title", "category"):
        if not meta.get(required):
            raise ValueError(f"{doc_id}: front matter needs '{required}'")
    tags = tuple(t.strip() for t in meta.get("tags", "").split(",") if t.strip())
    body = raw[match.end() :]
    chunks: list[Chunk] = []
    for block in re.split(r"^## ", body, flags=re.M):
        block = block.strip()
        if not block:
            continue
        heading, _, text = block.partition("\n")
        text = " ".join(text.split())
        if not text:
            continue
        chunks.append(
            Chunk(
                id=f"{doc_id}#{slugify(heading)}",
                doc=doc_id,
                title=meta["title"],
                section=heading.strip(),
                category=meta["category"],
                tags=tags,
                text=text,
            )
        )
    if not chunks:
        raise ValueError(f"{doc_id}: no '## ' sections found")
    return chunks


def load_corpus(directory: str | Path) -> list[Chunk]:
    paths = sorted(Path(directory).glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"no runbooks (*.md) in {directory}")
    chunks: list[Chunk] = []
    for path in paths:
        chunks.extend(parse_runbook(path.stem, path.read_text(encoding="utf-8")))
    ids = [c.id for c in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate chunk ids; section headings must be unique per runbook")
    return chunks
