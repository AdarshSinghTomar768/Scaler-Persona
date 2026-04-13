from __future__ import annotations

from pathlib import Path


OUTPUT = Path("/Users/adarsh/scaler-persona/reports/evals-report.pdf")

LINES = [
    "Adarsh AI Persona Evals Report",
    "",
    "Voice Quality",
    "- Latency: measured time to first spoken response after caller utterance end; target under 2s.",
    "- Accuracy: compared spoken answers against retrieved resume and repo evidence.",
    "- Task completion: checked follow-ups, availability lookup, and booking completion.",
    "",
    "Chat Groundedness",
    "- Hallucination rate: sampled responses for unsupported claims across resume and project questions.",
    "- Retrieval quality: validated top chunks for RAG, repo summary, and role-fit prompts.",
    "- Citation usefulness: confirmed the UI exposed enough source context for manual review.",
    "",
    "Failure Modes And Fixes",
    "- Resume retrieval was too coarse. Fix: PDF extraction plus tighter chunking.",
    "- Fit questions preferred repo docs. Fix: query expansion and resume weighting.",
    "- Booking could look complete without credentials. Fix: explicit missing_credentials status.",
    "",
    "What I Would Improve With 2 More Weeks",
    "- Add full conversational tool calling for booking inside the chat thread.",
    "- Add automated latency/interruption/retrieval eval harnesses.",
    "- Add deployment automation for Vapi, Twilio, and Cal.com.",
]


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_line(text: str, width: int = 92) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)
    return lines


def build_content_stream() -> bytes:
    chunks = ["BT", "/F1 12 Tf", "50 770 Td", "14 TL"]
    first = True
    for raw_line in LINES:
        for line in wrap_line(raw_line):
            if first:
                chunks.append(f"({escape_pdf_text(line)}) Tj")
                first = False
            else:
                chunks.append("T*")
                chunks.append(f"({escape_pdf_text(line)}) Tj")
    chunks.append("ET")
    return "\n".join(chunks).encode("latin1")


def write_pdf() -> None:
    content = build_content_stream()
    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(f"<< /Length {len(content)} >>\nstream\n".encode("latin1") + content + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin1"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("latin1")
    )
    OUTPUT.write_bytes(pdf)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    write_pdf()
