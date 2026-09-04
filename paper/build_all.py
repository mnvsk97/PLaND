#!/usr/bin/env python3
"""Build the PLaND paper in its common distribution formats."""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PAPER_BASENAME = "PLAND_PAPER"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def convert_docx_to_html(docx: Path, destination: Path) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError(
            "LibreOffice is required for HTML export. Use the bundled workspace "
            "runtime, which provides the soffice command."
        )

    with tempfile.TemporaryDirectory(prefix="pland-paper-html-") as temp:
        temp_dir = Path(temp)
        run([
            soffice,
            "--headless",
            "--convert-to",
            "html:HTML (StarWriter)",
            "--outdir",
            str(temp_dir),
            str(docx),
        ])
        generated = temp_dir / f"{docx.stem}.html"
        if not generated.exists():
            raise RuntimeError("LibreOffice did not produce the expected HTML file")
        html = generated.read_text(encoding="utf-8")

        def embed_image(match: re.Match[str]) -> str:
            image_name = match.group(1)
            image_path = temp_dir / image_name
            if not image_path.is_file():
                raise RuntimeError(f"HTML image sidecar was not generated: {image_name}")
            mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            return f'src="data:{mime_type};base64,{encoded}"'

        html = re.sub(r'src="([^"/]+\.(?:jpg|jpeg|png|gif))"', embed_image, html)
        destination.write_text(html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).with_name("PAPER.md"),
        help="Markdown manuscript to build (default: paper/PAPER.md)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "output" / "paper",
        help="Directory for all generated formats (default: output/paper)",
    )
    parser.add_argument(
        "--allow-pending-results",
        action="store_true",
        help="Allow draft result markers in the DOCX build",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown = output_dir / f"{PAPER_BASENAME}.md"
    pdf = output_dir / f"{PAPER_BASENAME}.pdf"
    docx = output_dir / f"{PAPER_BASENAME}.docx"
    html = output_dir / f"{PAPER_BASENAME}.html"

    shutil.copy2(source, markdown)
    # Both builders refresh derived figure files. Stage the source and figures
    # so a reproduction build never changes the checked-in source tree merely
    # because conversion tools emit different JPEG metadata.
    with tempfile.TemporaryDirectory(prefix="pland-paper-source-") as directory:
        staged_root = Path(directory)
        staged_source = staged_root / source.name
        staged_figures = staged_root / "figures"
        shutil.copy2(source, staged_source)
        shutil.copytree(source.parent / "figures", staged_figures)

        run([
            sys.executable,
            str(Path(__file__).with_name("build_pdf.py")),
            str(staged_source),
            str(pdf),
        ])

        docx_command = [
            sys.executable,
            str(Path(__file__).with_name("build_manuscript.py")),
            str(staged_source),
            str(docx),
            "--figures-dir",
            str(staged_figures),
        ]
        if args.allow_pending_results:
            docx_command.append("--allow-pending-results")
        run(docx_command)
    convert_docx_to_html(docx, html)

    for artifact in (markdown, pdf, docx, html):
        if not artifact.exists() or artifact.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty paper artifact: {artifact}")
        print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
