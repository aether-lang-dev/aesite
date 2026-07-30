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

## Layout

    serve.ae                   # the Aether server
    test.sh                    # integration smoke test
    static/                    # HTML, CSS, Docs/, CNAME
    resources/lessons/<n>/     # content.html, code.ae, title.txt
    tools/gendocs.py           # markdown -> static/Docs/ generator
    tools/genlessons.ae        # resources/lessons -> static/lessons.json
    Dockerfile, fly.toml       # optional live exec backend
    .github/workflows/         # CI + Pages deploy
