# md_to_html

Converts GitHub-flavoured Markdown files to styled HTML using [pandoc](https://pandoc.org/) and deploys them to the static site.

## What it does

1. Reads all `.md` files from the given source directory.
2. Converts each file to HTML using `articles_template.html` as the pandoc template.
3. Moves the generated HTML files to `static/Docs/`.
4. Generates (or overwrites) `static/docs.html` — an index page with card links to every document, sorted alphabetically by the document's `<h1>` heading.

## Requirements

- Python 3.8+
- `pandoc` installed and available on `PATH`

## Usage

```bash
python md_to_html.py <path-to-markdown-directory>
```

**Example** — convert all `.md` files in the project root:

```bash
python Tools/Github_md_to_html/md_to_html.py /path/to/your/markdown/files
```

## Templates

| File | Purpose |
|---|---|
| `articles_template.html` | Pandoc template applied to every converted document |
| `docs_page_template.html` | Template for the generated `docs.html` index page |

## Stylesheets

Generated HTML documents reference the following stylesheets from the `static/` folder using absolute paths:

| File | Purpose |
|---|---|
| `static/style.css` | Base site styles |
| `static/subpages.css` | Subpage layout styles |
| `static/articles.css` | Article-specific typography and layout |
