#!/usr/bin/env bash
# Integration smoke test for the Aether aesite server.
# Builds serve.ae, starts it, exercises every route including real code
# execution, and exits non-zero on any failure. CI runs this.
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.aether/bin:$PATH"

PORT=1323; BIN=/tmp/aesite-serve-test; LOG=/tmp/aesite-test.log; fail=0

echo "building serve.ae ..."
if ! ae build serve.ae -o "$BIN" 2>/tmp/aesite-build.log; then
  echo "BUILD FAILED"; grep -vE "ld: warning|newer 'macOS'" /tmp/aesite-build.log; exit 1
fi
lsof -ti tcp:$PORT 2>/dev/null | xargs kill -9 2>/dev/null
"$BIN" >"$LOG" 2>&1 & SRV=$!
cleanup(){ kill "$SRV" 2>/dev/null; lsof -ti tcp:$PORT 2>/dev/null | xargs kill -9 2>/dev/null; }
trap cleanup EXIT
ready=0; for _ in $(seq 1 40); do curl -s -o /dev/null "http://localhost:$PORT/healthz" && { ready=1; break; }; sleep .25; done
[ "$ready" = 1 ] || { echo "SERVER DID NOT START"; cat "$LOG"; exit 1; }
base="http://localhost:$PORT"

code(){ local d=$1 w=$2; shift 2; local g; g=$(curl -s -m30 -o /dev/null -w '%{http_code}' "$@"); [ "$g" = "$w" ] && echo "  PASS  $d ($g)" || { echo "  FAIL  $d (want $w got $g)"; fail=1; }; }
body(){ local d=$1 nd=$2; shift 2; curl -s -m30 "$@" | grep -q -- "$nd" && echo "  PASS  $d" || { echo "  FAIL  $d (missing: $nd)"; fail=1; }; }

echo "routes ..."
code "GET  /"                     200 "$base/"
code "GET  /aether.css"           200 "$base/aether.css"
code "GET  /repl.html"            200 "$base/repl.html"
code "GET  /Docs/getting-started" 200 "$base/Docs/getting-started.html"
code "GET  /Docs/language-ref"    200 "$base/Docs/language-reference.html"
code "GET  /healthz"              200 "$base/healthz"
code "GET  /api/lesson/1"         200 "$base/api/lesson/1"
code "GET  /api/lesson/999"       404 "$base/api/lesson/999"
code "GET  /missing.html"         404 "$base/missing.html"
body "lesson 1 starter_code"      '"starter_code"' "$base/api/lesson/1"
echo "real execution ..."
body "exec runs code"             'smoke ok'  -X PUT "$base/api/exec" -d 'main(){ println("smoke ok") }'
body "exec shows compile errors"  'Undefined' -X PUT "$base/api/exec" -d 'main(){ println(nope) }'

[ "$fail" = 0 ] && echo "ALL PASS" || echo "FAILURES ABOVE"
exit $fail
