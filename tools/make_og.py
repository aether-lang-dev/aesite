#!/usr/bin/env python3
"""Render tools/og.html to static/og.png, the link-preview card.

The card is a page, not a drawing: it links the site's own aether.css, so the
mark, the palette and the typefaces are the ones the site actually ships and
cannot drift from them. Re-run after editing tools/og.html or the brand rules.

    python3 tools/make_og.py
"""
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading

CHROMES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "chromium", "chromium-browser",
)


def find_chrome():
    for c in CHROMES:
        if os.path.isfile(c):
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static = os.path.join(root, "static")
    chrome = find_chrome()
    if not chrome:
        print("no Chrome or Chromium found; cannot render the card", file=sys.stderr)
        return 1

    staged = os.path.join(static, "_og.html")
    shutil.copyfile(os.path.join(root, "tools", "og.html"), staged)

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=static, **kw)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out = os.path.join(static, "og.png")
        rc = subprocess.call([
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--virtual-time-budget=6000", "--window-size=1200,630",
            "--screenshot=" + out, "http://127.0.0.1:%d/_og.html" % port,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        srv.shutdown()

    os.remove(staged)
    if rc != 0:
        print("chrome exited %d" % rc, file=sys.stderr)
        return rc
    print("wrote static/og.png (1200x630)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
