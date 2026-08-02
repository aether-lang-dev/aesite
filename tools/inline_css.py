#!/usr/bin/env python3
"""Inline static/aether.css into every page's <head>.

The stylesheet was the last render-blocking request: the browser could not
paint until it had been fetched and parsed, and the @font-face rules inside
it were not even discovered until then, so the fonts chained behind it.

Inlining removes the request and puts the font declarations in the initial
HTML parse. aether.css stays the canonical file and is still served; this
copies it into the pages. RE-RUN THIS AFTER EDITING aether.css, or the
pages keep serving the old rules.

    python3 tools/inline_css.py
"""
import os
import re
import sys

OPEN = '<style id="aether-inline">'
CLOSE = '</style>'
LINK = re.compile(r'[ \t]*<link[^>]*href="/aether\.css"[^>]*>\n?')
BLOCK = re.compile(re.escape(OPEN) + r'.*?' + re.escape(CLOSE) + r'\n?', re.S)


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static = os.path.join(root, 'static')
    css_path = os.path.join(static, 'aether.css')
    css = open(css_path, encoding='utf-8').read()
    block = OPEN + '\n' + css.strip() + '\n' + CLOSE + '\n'

    touched = 0
    for dirpath, _, names in os.walk(static):
        for name in names:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            src = open(path, encoding='utf-8').read()
            if BLOCK.search(src):
                out = BLOCK.sub(lambda _: block, src, count=1)
                out = LINK.sub('', out)
            elif LINK.search(src):
                out = LINK.sub(lambda _: block, src, count=1)
                out = LINK.sub('', out)
            else:
                continue
            if out != src:
                open(path, 'w', encoding='utf-8').write(out)
                touched += 1
    print('inlined aether.css into %d page(s)' % touched)
    return 0


if __name__ == '__main__':
    sys.exit(main())
