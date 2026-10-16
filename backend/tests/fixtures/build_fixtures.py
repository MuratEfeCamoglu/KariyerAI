"""Sentetik test CV'lerini üretir. Kişiler uydurmadır (ISKELET V13).

Çalıştırma (backend/ içinde): uv run python -m tests.fixtures.build_fixtures
"""

from pathlib import Path

import docx

FIXTURES = Path(__file__).parent

PDF_CV_LINES = [
    "Deniz Arslan",
    "deniz.arslan@example.com | +90 555 000 11 22",
    "",
    "Summary: Backend developer with six years of experience building payment APIs.",
    "",
    "Experience",
    "Senior Backend Developer, Ornek Teknoloji A.S. (2021-03 - present)",
    "Designed FastAPI services handling 2 million requests per day.",
    "Backend Developer, Deneme Yazilim (2018-06 - 2021-02)",
    "Maintained Django applications and PostgreSQL databases.",
    "",
    "Education: BSc Computer Engineering, Ornek University, 2018",
    "Skills: Python, FastAPI, PostgreSQL, Docker",
    "Languages: English (C1), German (A2)",
]

DOCX_CV_LINES = [
    "Elif Kaya",
    "elif.kaya@example.com · +90 555 000 33 44",
    "Özet: İnsan kaynakları analitiği alanında dört yıllık deneyime sahip veri analisti.",
    "Deneyim",
    "Veri Analisti, Örnek Lojistik A.Ş. (2020-09 – halen)",
    "Bordro ve işe alım verileri için Power BI raporları hazırladı.",
    "Eğitim: İstatistik Lisans, Örnek Üniversitesi, 2020",
    "Beceriler: SQL, Python, Power BI, Excel",
    "Diller: İngilizce (B2), Türkçe (C2)",
]


def _pdf(content: str) -> bytes:
    """Tek sayfalık, Helvetica fontlu minimal PDF (yalnızca ASCII metin)."""
    stream = content.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode()
    out += f"startxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_pdf(lines: list[str]) -> bytes:
    body = "".join(f"({_escape(line)}) Tj T*\n" for line in lines)
    return _pdf(f"BT /F1 10 Tf 50 800 Td 14 TL\n{body}ET")


def image_only_pdf() -> bytes:
    """Taranmış CV benzeri: metin katmanı yok, yalnızca çizim."""
    return _pdf("0.5 g 50 400 495 380 re f")


def text_docx(lines: list[str]) -> bytes:
    from io import BytesIO

    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def main() -> None:
    (FIXTURES / "cv_deniz_arslan.pdf").write_bytes(text_pdf(PDF_CV_LINES))
    (FIXTURES / "cv_elif_kaya.docx").write_bytes(text_docx(DOCX_CV_LINES))
    (FIXTURES / "scanned_cv.pdf").write_bytes(image_only_pdf())
    print("Fixture'lar yazıldı:", FIXTURES)


if __name__ == "__main__":
    main()
