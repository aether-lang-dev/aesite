# Aether Language, website and REPL

The website for the Aether programming language, and its interactive REPL,
served by Aether's own `std.http` server.

## Serving

`serve.ae` serves the static site and the REPL API. It replaces the original
Go/Echo backend entirely.

- Static pages and assets from `static/`.
- `GET  /api/lesson/:nbr` returns a lesson `{ title, theory, starter_code }` from `resources/lessons/`.
- `PUT  /api/exec` compiles and runs the submitted source with `ae run` and returns `{ stdout, stderr }`. This is the live playground backend.
- `GET  /healthz` liveness.

It uses `std.http` (server, routing, zero-copy static files), `std.io`
(lesson files off disk), and `std.json` (escaped responses).

## Run

    ae run serve.ae            # http://localhost:1323/

or build a binary and run it from the repository root, so `static/` and
`resources/` resolve:

    ae build serve.ae -o aesite-serve
    ./aesite-serve

## Test

    ./test.sh

Builds `serve.ae`, starts it, exercises every route, and exits non-zero on
any failure. CI runs exactly this.

## Deploy

Pushes to `main` run `.github/workflows/deploy.yml`:

1. build `serve.ae` and run `./test.sh`,
2. publish `static/` to GitHub Pages at **aether-lang.dev**.

The custom domain is set by `static/CNAME`. On the registrar, point the apex
at GitHub Pages with four `A` records: `185.199.108.153`, `185.199.109.153`,
`185.199.110.153`, `185.199.111.153`.

The live REPL backend (`/api/exec` running real Aether) is the next step. It
deploys as the `serve.ae` server on a host of its own, since Pages serves
static content only.

## Playground

`static/repl.html` is a self-contained playground. Lessons load from
`static/lessons.json` (baked by `tools/genlessons.ae`, which also stores each
lesson's real output), so lessons, theory, and a sample run work on a static
host such as GitHub Pages with no server.

On load it probes `/healthz`. If a live `serve.ae` backend answers, Run
executes whatever is in the editor against it; otherwise Run shows the
precomputed output for the unedited lesson and points you at `ae run` for
local execution. To target a backend on another origin, set its URL in the
`<meta name="aesite-exec">` tag and allow CORS there.

Regenerate lessons after editing `resources/lessons/`:

    ae run tools/genlessons.ae

## Live backend (optional)

The static site works on its own. To make the playground run *edited* code, deploy
`serve.ae` as a backend and point the site at it.

Deploy with the included `Dockerfile` (the image keeps the Aether toolchain so
`/api/exec` can compile and run code). On Fly.io:

    fly launch --no-deploy    # once, creates the app from fly.toml
    fly deploy

Then set the backend origin in `static/repl.html`:

    <meta name="aesite-exec" content="https://your-app.fly.dev">

The playground probes `/healthz` and, when it answers, runs the editor's code there.

`/api/exec` runs ARBITRARY submitted code, i.e. arbitrary native code on the
host. It is hardened, not sandboxed: each request compiles in a fresh temp dir,
then the binary runs as a non-root user in a private network namespace
(`unshare`, no outbound access) under ulimits (CPU, file size) and a 10s
timeout, with output capped. Aether's containment model is language-level and
does not constrain untrusted external programs, so that is deliberately not
relied on here. A public deployment MUST add real OS isolation, e.g.

    docker run --rm --read-only --tmpfs /tmp --pids-limit=256 \
               --memory=512m --cpus=1 -p 8080:8080 aesite

plus rate limiting, and ideally a per-request microVM (Firecracker/gVisor).
Run it somewhere disposable, never on a host with secrets or writable mounts.

## Docs

`static/Docs/` is generated from the language's markdown docs. Regenerate after
they change:

    python3 tools/gendocs.py ~/Documents/git/aether/docs static/Docs

It converts every top-level `*.md` to a styled page (grouped sidebar, syntax
highlighting, cross-links rewritten to `/Docs/*.html`) and refreshes
`static/docs.html`. Output is committed and served as-is by Pages.

## Brand

`static/ae.svg` is the `ae` ligature, the org's mark, traced from the avatar
and trimmed to the glyph so it carries no background of its own. The `.ae` rule
in `static/aether.css` masks it and paints it `--red`; `font-size` stays the
sizing knob. It needs about 30px to read: below that the hairlines close up.

The stylesheet is inlined into every page, so after editing `aether.css`:

    python3 tools/inline_css.py

The card and the tab icon are pages too (`tools/og.html`, `tools/favicon.html`)
that link `aether.css`, so they cannot drift from the site's own mark and
palette. After editing either:

    python3 tools/render_assets.py

## Layout

    serve.ae                   # the Aether server
    test.sh                    # integration smoke test
    static/                    # HTML, CSS, ae.svg, Docs/, CNAME
    resources/lessons/<n>/     # content.html, code.ae, title.txt
    tools/gendocs.py           # markdown -> static/Docs/ generator
    tools/genlessons.ae        # resources/lessons -> static/lessons.json
    tools/inline_css.py        # aether.css -> every page's <head>
    tools/og.html, favicon.html   # templates for og.png and favicon.png
    tools/render_assets.py     # renders both to static/
    Dockerfile, fly.toml       # optional live exec backend
    .github/workflows/         # CI + Pages deploy

## Releases update this site automatically

When aether publishes a release, its pipeline dispatches `aether-release` to
this repo. The `sync aether release` workflow then checks out that tag,
regenerates `static/Docs` from its `docs/`, stamps the version from its
`VERSION` file, moves the toolchain pin in `deploy.yml` to the new tag,
commits, and dispatches `deploy.yml` to publish.

Doing this by hand meant doing it late: the site sat on v0.562 while aether
shipped 0.580.

Three things worth knowing:

- **The daily schedule is the backstop.** The cross-repo dispatch needs a PAT
  on the aether side (`AESITE_SYNC_TOKEN`, `contents: write` here). Without it
  the release still succeeds and says so, and this repo's 06:15 UTC check
  picks the release up within a day. A missing token delays the site; it does
  not stall it.
- **`static/Docs` is rebuilt from empty each time**, so a doc deleted upstream
  stops being served. Everything in that directory is generated — do not put
  anything hand-written there.
- **The deploy is still gated.** `deploy.yml` builds `serve.ae` with the new
  toolchain and runs the integration test before publishing. If a release
  breaks the site, nothing is deployed and the previous version stays up.

To publish a release by hand, run the `sync aether release` workflow and give
it a tag, or leave the tag empty to take the latest release.
