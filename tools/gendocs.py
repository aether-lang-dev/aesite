#!/usr/bin/env python3
"""Generate the Aether documentation site from the language's markdown docs.

Reads every top-level ``*.md`` in the source docs directory, converts each to a
styled HTML page that matches the site design, and writes them to
``static/Docs/``. Also writes ``static/docs.html`` (a redirect to the first
doc) and keeps the sidebar grouped in a curated reading order.

Usage:
    python3 tools/gendocs.py [SRC_DOCS_DIR] [OUT_DIR]

Defaults: SRC=~/Documents/git/aether/docs   OUT=<repo>/static/Docs

This is a build tool. Its output (static/Docs/*.html) is committed and served
as-is by GitHub Pages, so re-run it whenever the upstream docs change.
"""

import html
import os
import re
import sys

VERSION = "0.467"
GH = "https://github.com/aether-lang-org/aether"
SITE = "Aether"
DOMAIN = "https://aether-lang.dev"

# Curated sidebar grouping and reading order. Any doc whose slug is not listed
# here is appended to "More" so nothing is ever silently dropped.
GROUPS = [
    ("Start", ["getting-started", "tutorial", "next-steps"]),
    ("Language", [
        "language-reference", "type-inference-guide", "type-annotation-style-guide",
        "type-inference-multi-value-returns", "distinct-types", "sequences",
        "named-args-and-select", "closures-and-builder-dsl", "closures-and-lifetimes",
        "module-system-design", "when-static-if",
    ]),
    ("Runtime", [
        "architecture", "actor-concurrency", "scheduler-quick-reference",
        "memory-management", "runtime-optimizations", "numa-support",
    ]),
    ("Interop", [
        "c-interop", "c-embedding", "emit-lib", "embedded-namespaces-and-host-bindings",
        "aether-embedded-in-host-applications",
    ]),
    ("Standard library", [
        "stdlib-reference", "stdlib-api", "http-server", "http-reverse-proxy",
        "http-handler-context",
    ]),
    ("Safety", ["containment-sandbox", "hide-and-seal", "config-is-code"]),
    ("Build & tooling", [
        "build-system", "formatter", "bindgen-consts", "install-layout",
        "runtime-config", "per-process-config", "cic-help",
    ]),
    ("Performance", ["performance-benchmarks", "profiling-guide", "allocators"]),
    ("Design & RFCs", [
        "structured-concurrency", "contract-folding", "error-unification",
        "compiler-trust-boundary", "json-parser-design", "aether_compared_to_capsicum",
        "isolated", "compile-time-eval", "dsl-without-macros", "lib-caller-info",
    ]),
    ("Contributing", [
        "stdlib-module-pattern", "stdlib-vs-contrib", "bootstrap-from-source",
        "release-glibc-portability",
    ]),
]

# Generated but kept out of the sidebar (dead/removed features).
NAV_SKIP = {"http-vcr"}

# Distinctive Aether keywords only. Kept conservative so ordinary identifiers
# and method names (map.new, list.add) are not miscoloured as keywords.
AE_KW = set((
    "actor struct message state extern func let var const builder callback union "
    "import exports export module as hide seal except if else for in while switch "
    "case default break continue return match receive reply send spawn_actor spawn "
    "make defer panic try catch after when requires ensures true false null self"
).split())
AE_TYPE = set((
    "int int64 int32 uint64 uint32 uint16 uint8 longdouble long short float double "
    "bool byte string cstring_const cstring void ptr actor_ref"
).split())
C_KW = set((
    "auto break case char const continue default do double else enum extern float "
    "for goto if inline int long register restrict return short signed sizeof "
    "static struct switch typedef union unsigned void volatile while bool size_t "
    "uint8_t uint16_t uint32_t uint64_t int8_t int16_t int32_t int64_t ssize_t "
    "int32 uint32 int64 uint64"
).split())
JSON_KW = {"true", "false", "null"}

LANG_ALIAS = {
    "ae": "aether", "c++": "cpp", "cc": "cpp", "hpp": "cpp", "h": "c",
    "shell": "bash", "sh": "bash", "zsh": "bash", "console": "bash",
    "text": "text", "txt": "text", "plain": "text", "output": "text",
    "out": "text", "": "text",
}
HL_LANGS = {"aether", "c", "cpp", "json", "bash", "toml", "ini", "make", "yaml", "yml", "dockerfile"}


# --------------------------------------------------------------------------
# Inline markdown -> HTML
# --------------------------------------------------------------------------

def esc(s):
    return html.escape(s, quote=False)


def resolve_href(url):
    url = url.strip()
    if url.startswith(("http://", "https://", "mailto:", "//", "#")):
        return url
    m = re.match(r"^(?:\./)?([\w./-]+?)\.md(#.+)?$", url)
    if m:
        base = m.group(1).split("/")[-1]
        return "/Docs/%s.html%s" % (base, m.group(2) or "")
    if url.startswith("../"):
        clean = url
        while clean.startswith("../"):
            clean = clean[3:]
        return "%s/tree/main/%s" % (GH, clean)
    if re.match(r"^(examples|contrib|std|runtime|src|docs|editor|tests)/", url):
        return "%s/tree/main/%s" % (GH, url)
    if url.endswith(".html"):
        return "/Docs/" + url.split("/")[-1]
    return url


def inline(text):
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return "\x00C%d\x00" % (len(codes) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+.!|>-])", r"\1", text)
    text = esc(text)

    def mklink(m):
        return '<a href="%s">%s</a>' % (esc(resolve_href(m.group(2))), m.group(1))

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", mklink, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)

    def unstash(m):
        return "<code>%s</code>" % esc(codes[int(m.group(1))])

    return re.sub(r"\x00C(\d+)\x00", unstash, text)


def heading_text(md):
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    t = t.replace("**", "").replace("`", "")
    return re.sub(r"(?<!\*)\*(?!\*)", "", t)


def slugify(text):
    s = heading_text(text).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return s.replace(" ", "-")


def strip_ticks(t):
    return t.replace("`", "")


# --------------------------------------------------------------------------
# Code fences with light syntax highlighting
# --------------------------------------------------------------------------

def highlight(code, lang):
    lang = LANG_ALIAS.get(lang, lang)
    if lang not in HL_LANGS:
        return esc(code)

    line_hash = lang in ("bash", "toml", "ini", "make", "yaml", "yml", "dockerfile")
    has_block = lang in ("aether", "c", "cpp")
    kws = AE_KW if lang == "aether" else C_KW if lang in ("c", "cpp") else JSON_KW if lang == "json" else set()

    pat = []
    if has_block:
        pat.append(r"(?P<block>/\*.*?\*/)")
    pat.append(r'(?P<str>"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')')
    pat.append(r"(?P<line>#[^\n]*)" if line_hash else r"(?P<line>//[^\n]*)")
    pat.append(r"(?P<num>\b\d[\d_]*(?:\.\d+)?\b)")
    pat.append(r"(?P<id>[A-Za-z_]\w*)")
    rx = re.compile("|".join(pat), re.S)

    out, pos = [], 0
    for m in rx.finditer(code):
        if m.start() > pos:
            out.append(esc(code[pos:m.start()]))
        kind, tok = m.lastgroup, m.group()
        if kind in ("block", "line"):
            out.append('<span class="com">%s</span>' % esc(tok))
        elif kind == "str":
            out.append('<span class="str">%s</span>' % esc(tok))
        elif kind == "num":
            out.append('<span class="num">%s</span>' % esc(tok))
        elif kind == "id" and tok in kws:
            out.append('<span class="kw">%s</span>' % esc(tok))
        elif kind == "id" and lang == "aether" and tok in AE_TYPE:
            out.append('<span class="fn">%s</span>' % esc(tok))
        else:
            out.append(esc(tok))
        pos = m.end()
    if pos < len(code):
        out.append(esc(code[pos:]))
    return "".join(out)


# --------------------------------------------------------------------------
# Block markdown -> HTML
# --------------------------------------------------------------------------

LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
HR_RE = re.compile(r"^(\*\s*){3,}$|^(-\s*){3,}$|^(_\s*){3,}$")


def is_block_start(line):
    s = line.strip()
    return bool(
        s.startswith("```") or re.match(r"#{1,6}\s", s) or s.startswith(">")
        or s.startswith("|") or LIST_RE.match(line) or HR_RE.match(s)
    )


def split_pipes(r):
    out, cur, tick, esc_next = [], "", False, False
    for ch in r:
        if esc_next:
            cur += ch
            esc_next = False
        elif ch == "\\":
            cur += ch
            esc_next = True
        elif ch == "`":
            tick = not tick
            cur += ch
        elif ch == "|" and not tick:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def table(rows):
    def cells(r):
        r = r.strip()
        if r.startswith("|"):
            r = r[1:]
        if r.endswith("|"):
            r = r[:-1]
        return [c.strip() for c in split_pipes(r)]

    head = "".join("<th>%s</th>" % inline(c) for c in cells(rows[0]))
    body = "".join(
        "<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in cells(r))
        for r in rows[2:]
    )
    return "<div class=\"tw\"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (head, body)


def parse_list(lines, i, indent0):
    n = len(lines)
    ordered = bool(re.match(r"\d", LIST_RE.match(lines[i]).group(2)))
    items = []
    while i < n:
        line = lines[i]
        if not line.strip():
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            mj = LIST_RE.match(lines[j]) if j < n else None
            if mj and len(mj.group(1)) >= indent0:
                i = j
                continue
            break
        m = LIST_RE.match(line)
        if not m or len(m.group(1)) < indent0:
            break
        if len(m.group(1)) > indent0:
            nested, i = parse_list(lines, i, len(m.group(1)))
            if items:
                items[-1] += nested
            else:
                items.append(nested)
            continue
        raw = m.group(3).strip()
        i += 1
        cont, nested = [], ""
        while i < n and lines[i].strip():
            m2 = LIST_RE.match(lines[i])
            if m2 and len(m2.group(1)) == indent0:
                break
            if m2 and len(m2.group(1)) > indent0:
                sub, i = parse_list(lines, i, len(m2.group(1)))
                nested += sub
                continue
            if m2 and len(m2.group(1)) < indent0:
                break
            cont.append(lines[i].strip())
            i += 1
        full = raw + ((" " + " ".join(cont)) if cont else "")
        items.append(inline(full) + nested)
    tag = "ol" if ordered else "ul"
    return "<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % it for it in items), tag), i


def convert(md):
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            lang = s[3:].strip().lower()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % highlight("\n".join(buf), lang))
            continue
        m = re.match(r"(#{1,6})\s+(.*)$", line)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            out.append('<h%d id="%s">%s</h%d>' % (lvl, slugify(txt), inline(txt), lvl))
            i += 1
            continue
        if HR_RE.match(s):
            out.append("<hr>")
            i += 1
            continue
        if (s.startswith("|") and i + 1 < n and "-" in lines[i + 1]
                and re.match(r"^\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1].strip())):
            block = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            out.append(table(block))
            continue
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]).strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf)))
            continue
        if LIST_RE.match(line):
            block_html, i = parse_list(lines, i, len(LIST_RE.match(line).group(1)))
            out.append(block_html)
            continue
        buf = []
        while i < n and lines[i].strip() and not is_block_start(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

def doc_title(md, slug):
    for ln in md.split("\n"):
        m = re.match(r"#\s+(.*)$", ln.strip())
        if m:
            return m.group(1).strip()
    return slug.replace("-", " ").title()


def doc_description(md):
    in_fence = False
    for ln in md.split("\n"):
        s = ln.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not s or s.startswith(("#", ">", "|", "-", "*", "<")):
            continue
        text = re.sub(r"[`*]", "", s)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 30:
            return (text[:152] + "...") if len(text) > 155 else text
    return "Aether language documentation."


def build_order(slugs_present):
    order, seen = [], set()
    for grp, slugs in GROUPS:
        picked = [s for s in slugs if s in slugs_present]
        for s in picked:
            seen.add(s)
        if picked:
            order.append((grp, picked))
    extra = sorted(s for s in slugs_present if s not in seen and s not in NAV_SKIP)
    if extra:
        order.append(("More", extra))
    return order


def sidebar(order, titles, cur):
    parts = []
    for grp, slugs in order:
        parts.append('<div class="grp">%s</div>' % grp)
        for s in slugs:
            on = ' class="on"' if s == cur else ""
            parts.append('<a href="/Docs/%s.html"%s>%s</a>'
                         % (s, on, esc(strip_ticks(titles[s]))))
    return "\n".join(parts)


def group_of(order, cur):
    for grp, slugs in order:
        if cur in slugs:
            return grp.lower()
    return "docs"


def extract_headings(body_html):
    hs = []
    for m in re.finditer(r'<h([23]) id="([^"]+)">(.*?)</h\1>', body_html, re.S):
        text = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
        hs.append((int(m.group(1)), m.group(2), text))
    return hs


def toc_html(hs):
    if len(hs) < 2:
        return ""
    items = "".join('<a href="#%s" class="l%d" data-id="%s">%s</a>'
                    % (hid, lvl, hid, esc(txt)) for lvl, hid, txt in hs)
    return ('<nav class="toc" aria-label="On this page">'
            '<div class="toc-h">On this page</div>%s</nav>' % items)


def plaintext(body_html):
    t = re.sub(r"<(pre|code)[^>]*>.*?</\1>", " ", body_html, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title} · {site}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{domain}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/aether.css">
</head>
<body>
<a class="skip" href="#doc">Skip to content</a>
<header class="site-head">
  <div class="wrap bar">
    <a class="brand" href="/" aria-label="Aether"><span class="ae">ae</span><span class="nm">aether</span></a>
    <nav>
      <a href="/repl.html">Playground</a>
      <a href="/Docs/getting-started.html" class="on">Docs</a>
      <a class="src" href="{gh}">Source</a>
      <span class="vtag">v{version}</span>
    </nav>
  </div>
</header>
<div class="wrap">
  <div class="doc-shell">
    <nav class="doc-nav" aria-label="Documentation">
      <div class="docsearch"><input id="ds" type="search" placeholder="Search the docs" aria-label="Search documentation" autocomplete="off" spellcheck="false"><kbd>/</kbd><div class="ds-res" id="dsres" role="listbox"></div></div>
{nav}</nav>
    <main class="doc-main">
      <article class="doc-body" id="doc">
        <div class="bc"><span class="prompt">$</span>docs / {group}</div>
{body}
      </article>
    </main>
    {toc}
  </div>
</div>
<script src="/docs.js" defer></script>
<footer class="site-foot">
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <span class="ae">ae</span>
      <p class="foot-tag">Actors that compile to C.</p>
      <p class="foot-status">v0.467 &middot; pre-1.0, actively developed</p>
    </div>
    <div class="foot-col">
      <h4>Docs</h4>
      <a href="/Docs/getting-started.html">Getting Started</a>
      <a href="/Docs/tutorial.html">Tutorial</a>
      <a href="/Docs/language-reference.html">Language Reference</a>
      <a href="/Docs/stdlib-reference.html">Standard Library</a>
    </div>
    <div class="foot-col">
      <h4>Project</h4>
      <a href="https://github.com/aether-lang-org/aether">GitHub</a>
      <a href="https://github.com/aether-lang-org/aether/issues">Issues</a>
      <a href="https://github.com/aether-lang-org/aether/blob/main/CHANGELOG.md">Changelog</a>
      <a href="https://github.com/sponsors/nicolas-maman">Sponsor</a>
    </div>
    <div class="foot-col">
      <h4>Try</h4>
      <a href="/repl.html">Playground</a>
      <a href="/Docs/getting-started.html">Install</a>
      <a href="/Docs/architecture.html">Architecture</a>
    </div>
  </div>
  <div class="wrap foot-legal"><span>MIT licensed &middot; compiles to C</span><span>aether-lang.dev</span></div>
</footer>
</body>
</html>
"""


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/Documents/git/aether/docs")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "static", "Docs")
    os.makedirs(out, exist_ok=True)

    docs = {}
    for name in sorted(os.listdir(src)):
        if not name.endswith(".md"):
            continue
        slug = name[:-3]
        with open(os.path.join(src, name), encoding="utf-8") as fh:
            docs[slug] = fh.read()

    titles = {s: doc_title(md, s) for s, md in docs.items()}
    order = build_order(set(docs))
    index = []

    for slug, md in docs.items():
        body = convert(md)
        headings = extract_headings(body)
        page = PAGE.format(
            title=esc(strip_ticks(titles[slug])),
            site=SITE,
            desc=esc(doc_description(md)),
            gh=GH,
            version=VERSION,
            nav=sidebar(order, titles, slug),
            group=esc(group_of(order, slug)),
            body=body,
            toc=toc_html(headings),
            canon="%s/Docs/%s.html" % (DOMAIN, slug),
            domain=DOMAIN,
        )
        page = page.replace("github.com/nicolasmd87/aether", "github.com/aether-lang-org/aether")
        page = re.sub(r"\s*\u2014\s*", ", ", page)   # no em-dashes (house style)
        with open(os.path.join(out, slug + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page)
        index.append({
            "slug": slug,
            "title": strip_ticks(titles[slug]),
            "group": group_of(order, slug),
            "headings": [{"id": hid, "text": txt} for _, hid, txt in headings],
            "text": re.sub(r"\s*\u2014\s*", ", ", plaintext(body))[:6000],
        })

    import json
    _sj = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    _sj = re.sub(r"\s*\u2014\s*", ", ", _sj)   # no em-dashes anywhere
    with open(os.path.join(here, "static", "search.json"), "w", encoding="utf-8") as fh:
        fh.write(_sj)

    urls = ["%s/" % DOMAIN, "%s/repl.html" % DOMAIN]
    urls += ["%s/Docs/%s.html" % (DOMAIN, s) for s in sorted(docs)]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append("  <url><loc>%s</loc></url>" % u)
    sm.append("</urlset>")
    with open(os.path.join(here, "static", "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sm) + "\n")

    # drop orphaned pages whose source .md was removed upstream
    for fn in os.listdir(out):
        if fn.endswith(".html") and fn[:-5] not in docs:
            os.remove(os.path.join(out, fn))
            print("removed orphan:", fn)

    first = "getting-started" if "getting-started" in docs else sorted(docs)[0]
    with open(os.path.join(here, "static", "docs.html"), "w", encoding="utf-8") as fh:
        fh.write('<!doctype html><meta charset="utf-8">'
                 '<meta http-equiv="refresh" content="0; url=/Docs/%s.html">'
                 '<link rel="canonical" href="/Docs/%s.html">' % (first, first))

    print("generated %d docs -> %s" % (len(docs), out))


if __name__ == "__main__":
    main()
