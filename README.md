# Aether Language, website and REPL

The website for the Aether programming language, and its interactive REPL,
served by Aether's own `std.http` server.

## Serving

`serve.ae` serves the static site and the REPL API. It replaces the original
Go/Echo backend entirely.

- Static pages and assets from `static/`.
- `GET  /api/lesson/:nbr` returns a lesson `{ title, theory, starter_code }` from `resources/lessons/`.
- `PUT  /api/exec` returns a code execution result (mocked until the Aether executor lands).
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

## Layout

    serve.ae                   # the Aether server
    test.sh                    # integration smoke test
    static/                    # HTML, CSS, Docs/, CNAME
    resources/lessons/<n>/     # content.html, code.ea, title.txt
    Tools/Github_md_to_html/   # markdown -> Docs/ generator (still Python; Aether port pending)
    .github/workflows/         # CI + Pages deploy
