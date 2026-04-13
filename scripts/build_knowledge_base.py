from __future__ import annotations

import json
import re
import zlib
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

RESUME_PATH = Path("/Users/adarsh/Downloads/AdarshResNew.pdf")
SOURCES = [
    {
        "type": "resume",
        "name": "Adarsh Resume",
        "path": RESUME_PATH,
        "url": None,
    },
    {
        "type": "github_repo",
        "name": "Computer-Vision-Powered-Search-Application",
        "path": Path("/Users/adarsh/Documents/Yolo CV/readme.md"),
        "url": "https://github.com/AdarshSinghTomar768/Computer-Vision-Powered-Search-Application",
    },
    {
        "type": "github_repo",
        "name": "Meta-Hackathon",
        "path": Path("/Users/adarsh/Documents/Meta_Hackathon/README.md"),
        "url": "https://github.com/AdarshSinghTomar768/Meta-Hackathon",
    },
    {
        "type": "github_repo",
        "name": "FixForge",
        "path": Path("/Users/adarsh/autonomous-devops-agent/FixForge/backend/main.py"),
        "url": "https://github.com/AdarshSinghTomar768/FixForge",
    },
]


def parse_pdf_text(path: Path) -> str:
    pdf = path.read_bytes()
    obj_re = re.compile(rb"(\d+)\s+(\d+)\s+obj(.*?)endobj", re.S)
    objs = {int(match.group(1)): match.group(3) for match in obj_re.finditer(pdf)}
    stream_re = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)

    cmap_by_obj: dict[int, dict[str, str]] = {}
    for obj_id, body in objs.items():
        match = stream_re.search(body)
        if not match:
            continue
        try:
            decoded = zlib.decompress(match.group(1))
        except Exception:
            continue
        if b"begincmap" not in decoded:
            continue
        cmap: dict[str, str] = {}
        lines = decoded.decode("latin1", errors="ignore").splitlines()
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if line.endswith("beginbfchar"):
                count = int(line.split()[0])
                for offset in range(1, count + 1):
                    values = re.findall(r"<([^>]+)>", lines[index + offset])
                    if len(values) >= 2:
                        cmap[values[0].upper()] = bytes.fromhex(values[1]).decode("utf-16-be", "ignore")
                index += count
            elif line.endswith("beginbfrange"):
                count = int(line.split()[0])
                for offset in range(1, count + 1):
                    values = re.findall(r"<([^>]+)>", lines[index + offset])
                    if len(values) == 3:
                        start, end, dst = (int(value, 16) for value in values)
                        for code in range(start, end + 1):
                            cmap[f"{code:04X}"] = chr(dst + code - start)
                index += count
            index += 1
        cmap_by_obj[obj_id] = cmap

    font_to_cmap: dict[int, dict[str, str]] = {}
    for obj_id, body in objs.items():
        match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", body)
        if match:
            font_to_cmap[obj_id] = cmap_by_obj.get(int(match.group(1)), {})

    pages: list[str] = []
    for obj_id, body in objs.items():
        if b"/Type /Page" not in body:
            continue
        fonts = {
            name.decode(): font_to_cmap[int(font_id)]
            for name, font_id in re.findall(rb"/(F\d+)\s+(\d+)\s+0\s+R", body)
        }
        content_match = re.search(rb"/Contents\s+(\d+)\s+0\s+R", body)
        if not content_match:
            continue
        content_obj = objs[int(content_match.group(1))]
        stream_match = stream_re.search(content_obj)
        if not stream_match:
            continue
        decoded = zlib.decompress(stream_match.group(1)).decode("latin1", errors="ignore")
        current_font = None
        parts: list[str] = []
        for line in decoded.splitlines():
            line = line.strip()
            font_match = re.search(r"/(F\d+)\s+[0-9.]+\s+Tf", line)
            if font_match:
                current_font = font_match.group(1)
            for hex_token in re.findall(r"<([0-9A-Fa-f]+)>\s*Tj", line):
                cmap = fonts.get(current_font or "", {})
                parts.append("".join(cmap.get(hex_token[i : i + 4].upper(), "") for i in range(0, len(hex_token), 4)))
            if line == "ET":
                parts.append("\n")
        pages.append("".join(parts))
    return "\n".join(pages)


def normalize_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_resume_chunks(source_name: str, source_type: str, source_path: str, url: str | None, text: str) -> list[dict]:
    cleaned = re.sub(r"\n\s*\n", "\n", text)
    headings = ["Profile", "Professional Experience", "Projects", "Skills", "Education"]
    pattern = "(" + "|".join(re.escape(item) for item in headings) + ")"
    parts = re.split(pattern, cleaned)

    chunks = []
    header_text = parts[0].strip()
    if header_text:
        chunks.append(
            {
                "chunk_id": f"{source_name.lower().replace(' ', '-')}-header",
                "title": f"{source_name} header",
                "source_type": source_type,
                "source_name": source_name,
                "source_path": source_path,
                "url": url,
                "text": header_text,
            }
        )

    for index in range(1, len(parts), 2):
        heading = parts[index].strip()
        body = parts[index + 1].strip() if index + 1 < len(parts) else ""
        if not body:
            continue
        chunks.extend(
            chunk_text(
                source_name=source_name,
                source_type=source_type,
                source_path=source_path,
                url=url,
                text=f"{heading}\n{body}",
            )
        )
    return chunks


def split_long_text(text: str, max_chars: int = 700) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    results: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            results.append(paragraph)
            continue
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if len(lines) > 1:
            current = []
            current_len = 0
            for line in lines:
                projected = current_len + len(line) + 1
                if current and projected > max_chars:
                    results.append(" ".join(current).strip())
                    current = [line]
                    current_len = len(line)
                else:
                    current.append(line)
                    current_len = projected
            if current:
                results.append(" ".join(current).strip())
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        current = []
        current_len = 0
        for sentence in sentences:
            projected = current_len + len(sentence) + 1
            if current and projected > max_chars:
                results.append(" ".join(current).strip())
                current = [sentence]
                current_len = len(sentence)
            else:
                current.append(sentence)
                current_len = projected
        if current:
            results.append(" ".join(current).strip())
    return results


def chunk_text(source_name: str, source_type: str, source_path: str, url: str | None, text: str) -> list[dict]:
    paragraphs = split_long_text(text)
    chunks = []
    for index, paragraph in enumerate(paragraphs, start=1):
        chunks.append(
            {
                "chunk_id": f"{source_name.lower().replace(' ', '-')}-{index}",
                "title": f"{source_name} chunk {index}",
                "source_type": source_type,
                "source_name": source_name,
                "source_path": source_path,
                "url": url,
                "text": paragraph,
            }
        )
    return chunks


def load_source_text(source: dict) -> str:
    path = source["path"]
    if path.suffix.lower() == ".pdf":
        return normalize_text(parse_pdf_text(path))
    return normalize_text(path.read_text())


def main() -> None:
    chunks = []
    for source in SOURCES:
        text = load_source_text(source)
        if source["type"] == "resume":
            chunks.extend(
                build_resume_chunks(
                    source_name=source["name"],
                    source_type=source["type"],
                    source_path=str(source["path"]),
                    url=source["url"],
                    text=text,
                )
            )
        else:
            chunks.extend(
                chunk_text(
                    source_name=source["name"],
                    source_type=source["type"],
                    source_path=str(source["path"]),
                    url=source["url"],
                    text=text,
                )
            )

    payload = {
        "generated_from": [str(item["path"]) for item in SOURCES],
        "chunks": chunks,
    }
    (DATA_DIR / "knowledge_base.json").write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(chunks)} chunks to {DATA_DIR / 'knowledge_base.json'}")


if __name__ == "__main__":
    main()
