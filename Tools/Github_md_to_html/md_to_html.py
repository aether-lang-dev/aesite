#!/usr/bin/env python3
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Convert markdown files to HTML using pandoc")
    parser.add_argument("source_dir", help="Path to directory containing .md files")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    if not source_dir.is_dir():
        print(f"Error: '{source_dir}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).parent.resolve()
    template = script_dir / "articles_template.html"
    if not template.exists():
        print(f"Error: template '{template}' not found", file=sys.stderr)
        sys.exit(1)

    md_files = list(source_dir.glob("*.md"))
    if not md_files:
        print(f"No .md files found in '{source_dir}'")
        sys.exit(0)

    copied = []
    try:
        for md_file in md_files:
            dest = script_dir / md_file.name
            shutil.copy2(md_file, dest)
            copied.append(dest)
            print(f"Copied: {md_file.name}")

        for md_dest in copied:
            output = md_dest.with_suffix(".html")
            cmd = [
                "pandoc", md_dest.name,
                "-o", output.name,
                f"--template={template}",
                "--from=gfm"
            ]
            print(f"Converting: {md_dest.name} -> {output.name}")
            result = subprocess.run(cmd, cwd=script_dir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  pandoc error: {result.stderr.strip()}", file=sys.stderr)
            else:
                print(f"  Done: {output.name}")
    finally:
        for md_dest in copied:
            md_dest.unlink(missing_ok=True)
        print(f"\nCleaned up {len(copied)} .md file(s) from working directory.")

    output_dir = (script_dir / "../../static/Docs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    html_files = list(script_dir.glob("*.html"))
    # Exclude template files
    html_files = [f for f in html_files if f.name not in ("articles_template.html", "docs_page_template.html")]
    for html_file in html_files:
        shutil.move(str(html_file), output_dir / html_file.name)
        print(f"Moved: {html_file.name} -> {output_dir / html_file.name}")
    print(f"\nMoved {len(html_files)} HTML file(s) to '{output_dir}'.")

    # Generate docs.html index from the exported files
    _generate_docs_index(script_dir, output_dir, html_files)


def _extract_h1(html_path: Path) -> str:
    """Return the text of the first <h1> in the file, or a fallback from the filename."""
    text = html_path.read_text(encoding="utf-8")
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
    if m:
        # Strip any inner tags (e.g. <code>)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    # Fallback: prettify the filename
    return html_path.stem.replace("-", " ").replace("_", " ").title()


def _generate_docs_index(script_dir: Path, docs_dir: Path, html_files: list) -> None:
    docs_template = script_dir / "docs_page_template.html"
    if not docs_template.exists():
        print("Warning: docs_page_template.html not found, skipping docs.html generation.", file=sys.stderr)
        return

    links = []
    for html_file in html_files:
        dest_file = docs_dir / html_file.name
        title = _extract_h1(dest_file) if dest_file.exists() else _extract_h1(html_file)
        href = f"/Docs/{html_file.name}"
        links.append((title, f'      <a class="doc-card" href="{href}"><span class="doc-card-title">{title}</span></a>'))

    links.sort(key=lambda t: t[0].lower())
    doc_links_html = "\n".join(html for _, html in links)
    output_html = docs_template.read_text(encoding="utf-8").replace("{{DOC_LINKS}}", doc_links_html)

    static_dir = (script_dir / "../../static").resolve()
    out_path = static_dir / "docs.html"
    out_path.write_text(output_html, encoding="utf-8")
    print(f"Generated: docs.html -> {out_path}")


if __name__ == "__main__":
    main()
