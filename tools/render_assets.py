#!/usr/bin/env python3
"""Render the site's raster assets from HTML templates.

tools/og.html    -> static/og.png      (1200x630 link-preview card)
tools/favicon.html -> static/favicon.png (256x256 tab icon)

Both are pages, not drawings: they link the site's own aether.css, so the mark,
the palette and the typefaces are the ones the site actually ships and cannot
drift from them. Re-run after editing either template or the brand rules.

    python3 tools/render_assets.py
"""
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading

ASSETS = (
    ("og.html", "og.png", "1200,630"),
    ("favicon.html", "favicon.png", "256,256"),
)

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

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=static, **kw)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        for template, out, size in ASSETS:
            staged = os.path.join(static, "_render.html")
            shutil.copyfile(os.path.join(root, "tools", template), staged)
            rc = subprocess.call([
                chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--default-background-color=00000000",
                "--virtual-time-budget=6000", "--window-size=" + size,
                "--screenshot=" + os.path.join(static, out),
                "http://127.0.0.1:%d/_render.html" % port,
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.remove(staged)
            if rc != 0:
                srv.shutdown()
                print("chrome exited %d rendering %s" % (rc, template), file=sys.stderr)
                return rc
            print("wrote static/%s (%s)" % (out, size.replace(",", "x")))
        srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
