"""Convert paper PDFs into token-efficient Markdown with source-page anchors."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf


_REFERENCE_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?references$", re.I)
_NUMBERED_HEADING = re.compile(
    r"^(\d+(?:\.\d+)*\.?)\s+([A-Z][^.!?]{1,100})$"
)
_KNOWN_HEADING = re.compile(
    r"^(abstract|introduction|related work|background|method|methodology|"
    r"approach|experiments?|experimental setup|results?|discussion|"
    r"limitations?|conclusion|conclusions|acknowledg(?:e)?ments?|"
    r"supplementary material)$",
    re.I,
)
_CVF_WATERMARK_PARTS = (
    "This CVPR paper is the Open Access version",
    "Except for this watermark, it is identical to the accepted version",
    "the final published version of the proceedings is available on IEEE Xplore",
)
_LIGATURES = str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi"})


@dataclass(frozen=True)
class ConversionStats:
    """Quality and size statistics for one converted paper."""

    source_pdf: str
    output_markdown: str
    title: str
    pages: int
    source_words: int
    output_words: int
    source_characters: int
    output_characters: int
    low_text_pages: int
    references_removed: bool
    references_start_page: int | None
    quality: str


def _normalize_line(line: str) -> str:
    """Normalize one PDF line without changing its semantics."""

    line = line.translate(_LIGATURES).replace("\u00ad", "")
    return re.sub(r"\s+", " ", line).strip()


def _is_noise_line(line: str, repeated_lines: set[str]) -> bool:
    """Return whether a line is a repeated header, footer, or watermark."""

    if not line:
        return False
    if line in repeated_lines:
        return True
    if any(part.lower() in line.lower() for part in _CVF_WATERMARK_PARTS):
        return True
    return bool(re.fullmatch(r"\d{4,6}", line))


def _heading_level(line: str) -> tuple[int, str] | None:
    """Return a Markdown level and title for a detected section heading."""

    numbered = _NUMBERED_HEADING.fullmatch(line)
    if numbered:
        depth = numbered.group(1).count(".") + 1
        return min(5, depth + 1), line
    if _KNOWN_HEADING.fullmatch(line):
        return 2, line
    return None


def _reflow_page(lines: list[str]) -> str:
    """Reflow wrapped PDF lines while preserving detected headings."""

    output: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(" ".join(paragraph))
            paragraph.clear()

    for line in lines:
        heading = _heading_level(line)
        if heading:
            flush_paragraph()
            level, title = heading
            output.append(f"{'#' * level} {title}")
        elif not line:
            flush_paragraph()
        elif paragraph and paragraph[-1].endswith("-") and line[0].islower():
            paragraph[-1] = paragraph[-1][:-1] + line
        else:
            paragraph.append(line)

    flush_paragraph()
    return "\n\n".join(output)


def _extract_pages(pdf_path: Path) -> tuple[list[str], str]:
    """Extract dehyphenated page text and infer a document title."""

    with pymupdf.open(pdf_path) as document:
        flags = pymupdf.TEXTFLAGS_TEXT | pymupdf.TEXT_DEHYPHENATE
        pages = [page.get_text("text", flags=flags) for page in document]
        metadata_title = _normalize_line((document.metadata or {}).get("title", ""))

    first_lines = [
        normalized
        for line in pages[0].splitlines()
        if (normalized := _normalize_line(line))
    ]
    inferred_title = first_lines[0] if first_lines else pdf_path.stem.replace("_", " ")
    if metadata_title and metadata_title.lower() not in {"untitled", "microsoft word"}:
        inferred_title = metadata_title
    return pages, inferred_title


def convert_pdf(pdf_path: Path, output_path: Path) -> ConversionStats:
    """Convert one PDF to cleaned Markdown and return conversion statistics."""

    pages, title = _extract_pages(pdf_path)
    source_text = "\n".join(pages)
    source_words = len(source_text.split())
    low_text_pages = sum(len(page.strip()) < 200 for page in pages)
    normalized_by_page = [
        [_normalize_line(line) for line in page.splitlines()] for page in pages
    ]
    has_abstract_heading = any(
        line.lower() == "abstract"
        for page_lines in normalized_by_page
        for line in page_lines
    )
    line_counts = Counter(
        line
        for page_lines in normalized_by_page
        for line in set(page_lines)
        if 3 <= len(line) <= 180
    )
    repeat_threshold = max(3, math.ceil(len(pages) * 0.30))
    repeated_lines = {
        line for line, count in line_counts.items() if count >= repeat_threshold
    }

    body_started = False
    references_removed = False
    references_start_page: int | None = None
    rendered_pages: list[str] = []
    for page_number, page_lines in enumerate(normalized_by_page, start=1):
        cleaned_lines: list[str] = []
        for line in page_lines:
            if _is_noise_line(line, repeated_lines):
                continue
            if _REFERENCE_HEADING.fullmatch(line):
                references_removed = True
                references_start_page = page_number
                break
            if not body_started:
                if line.lower() == "abstract":
                    body_started = True
                    cleaned_lines.append(line)
                elif not has_abstract_heading and re.fullmatch(
                    r"1\.?\s+introduction", line, re.I
                ):
                    body_started = True
                    cleaned_lines.append(line)
                continue
            cleaned_lines.append(line)

        if body_started and cleaned_lines:
            rendered = _reflow_page(cleaned_lines)
            if rendered:
                rendered_pages.append(
                    f"<!-- source-page: {page_number} -->\n\n{rendered}"
                )
        if references_removed:
            break

    body = "\n\n".join(rendered_pages).strip()
    output_words = len(body.split())
    low_ratio = low_text_pages / max(1, len(pages))
    if source_words < 1_000 or low_ratio > 0.25:
        quality = "insufficient-text-layer"
    elif source_words < 4_000 or not body:
        quality = "partial"
    else:
        quality = "good"

    warning = ""
    if quality != "good":
        warning = (
            "> [!WARNING]\n"
            f"> Extraction quality is **{quality}**. Consult the source PDF or "
            "replace it with a text-layer/OCR version before using it as evidence.\n\n"
        )
    source_link = f"../reference_papers_origin/{pdf_path.name}"
    frontmatter = {
        "source_pdf": pdf_path.name,
        "pages": len(pages),
        "source_words": source_words,
        "references_removed": references_removed,
        "references_start_page": references_start_page,
        "extraction_quality": quality,
        "converter": f"PyMuPDF-{pymupdf.__version__}",
    }
    metadata_lines = ["---"] + [
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in frontmatter.items()
    ] + ["---"]
    markdown = (
        "\n".join(metadata_lines)
        + f"\n\n# {title}\n\n"
        + f"[Open source PDF]({source_link})\n\n"
        + warning
        + (body if body else "_No reliable body text was extracted._")
        + "\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return ConversionStats(
        source_pdf=pdf_path.name,
        output_markdown=output_path.name,
        title=title,
        pages=len(pages),
        source_words=source_words,
        output_words=output_words,
        source_characters=len(source_text),
        output_characters=len(body),
        low_text_pages=low_text_pages,
        references_removed=references_removed,
        references_start_page=references_start_page,
        quality=quality,
    )


def write_index(output_dir: Path, stats: list[ConversionStats]) -> None:
    """Write a Markdown index and machine-readable conversion manifest."""

    total_source_words = sum(item.source_words for item in stats)
    total_output_words = sum(item.output_words for item in stats)
    reduction = 1.0 - total_output_words / max(1, total_source_words)
    quality_counts = Counter(item.quality for item in stats)
    lines = [
        "# Processed Reference Papers",
        "",
        "Token-efficient Markdown converted from `../reference_papers_origin/`.",
        "Original PDFs remain authoritative for equations, tables, figures, and",
        "citation verification. Bibliographies and repeated page furniture are removed.",
        "",
        "## Corpus summary",
        "",
        f"- Papers: {len(stats)}",
        f"- Source words: {total_source_words:,}",
        f"- Processed words: {total_output_words:,}",
        f"- Word reduction: {reduction:.1%}",
        f"- Good text layers: {quality_counts.get('good', 0)}",
        f"- Partial/insufficient text layers: "
        f"{len(stats) - quality_counts.get('good', 0)}",
        "",
        "## Papers",
        "",
        "| Paper | Pages | Source words | Processed words | Quality |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for item in stats:
        lines.append(
            f"| [{item.title}]({item.output_markdown}) | {item.pages} | "
            f"{item.source_words:,} | {item.output_words:,} | {item.quality} |"
        )
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```powershell",
            "conda activate auto_research",
            "python tools/scripts/convert_reference_papers.py `",
            "  --input-dir paper1/reference_papers_origin `",
            "  --output-dir paper1/reference_papers_processed",
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    (output_dir / "manifest.json").write_text(
        json.dumps([asdict(item) for item in stats], ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def convert_corpus(input_dir: Path, output_dir: Path) -> list[ConversionStats]:
    """Convert every top-level PDF in a directory and write corpus indexes."""

    pdf_paths = sorted(input_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = [
        convert_pdf(pdf_path, output_dir / f"{pdf_path.stem}.md")
        for pdf_path in pdf_paths
    ]
    write_index(output_dir, stats)
    return stats


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Convert paper PDFs to token-efficient Markdown."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    """Run the corpus converter from the command line."""

    args = build_parser().parse_args()
    stats = convert_corpus(args.input_dir, args.output_dir)
    quality_counts = Counter(item.quality for item in stats)
    print(
        f"Converted {len(stats)} PDFs: "
        f"{quality_counts.get('good', 0)} good, "
        f"{len(stats) - quality_counts.get('good', 0)} requiring review."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
