#!/usr/bin/env bash
# Integration smoke test for the Aether aesite server.
# Builds serve.ae, starts it, exercises every route, tears down.
# Exits non-zero on any failure, so CI can gate on it.
set -u
cd "$(dirname "$0")"

PORT=1323
BIN=/tmp/aesite-serve-test
LOG=/tmp/aesite-test.log
fail=0

echo "building serve.ae ..."
if ! ae build serve.ae -o "$BIN" 2>/tmp/aesite-build.log; then
  echo "BUILD FAILED"
  grep -vE "ld: warning|newer 'macOS'" /tmp/aesite-build.log
  exit 1
fi

lsof -ti tcp:$PORT 2>/dev/null | xargs kill -9 2>/dev/null
"$BIN" >"$LOG" 2>&1 &
SRV=$!
cleanup() { kill "$SRV" 2>/dev/null; lsof -ti tcp:$PORT 2>/dev/null | xargs kill -9 2>/dev/null; }
trap cleanup EXIT

# wait for the listener
ready=0
for _ in $(seq 1 40); do
  if curl -s -o /dev/null "http://localhost:$PORT/healthz"; then ready=1; break; fi
  sleep 0.25
done
if [ "$ready" != 1 ]; then echo "SERVER DID NOT START"; cat "$LOG"; exit 1; fi

base="http://localhost:$PORT"

code() { # desc want curl-args...
  local desc=$1 want=$2; shift 2
  local got; got=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$@")
  if [ "$got" = "$want" ]; then echo "  PASS  $desc ($got)"; else echo "  FAIL  $desc (want $want, got $got)"; fail=1; fi
}
body() { # desc needle curl-args...
  local desc=$1 needle=$2; shift 2
  if curl -s -m 5 "$@" | grep -q -- "$needle"; then echo "  PASS  $desc"; else echo "  FAIL  $desc (missing: $needle)"; fail=1; fi
}

echo "testing routes ..."
code "GET  /"               200 "$base/"
code "GET  /style.css"      200 "$base/style.css"
code "GET  /faq.html"       200 "$base/faq.html"
code "GET  /docs.html"      200 "$base/docs.html"
code "GET  /healthz"        200 "$base/healthz"
code "GET  /api/lesson/1"   200 "$base/api/lesson/1"
code "GET  /api/lesson/999" 404 "$base/api/lesson/999"
code "GET  /missing.html"   404 "$base/missing.html"
code "PUT  /api/exec"       200 -X PUT "$base/api/exec" -d '{}'
body "lesson 1 JSON title"  '"title"'  "$base/api/lesson/1"
body "lesson 1 JSON theory" '"theory"' "$base/api/lesson/1"
body "exec JSON stdout"     '"stdout"' -X PUT "$base/api/exec" -d '{}'
body "homepage is html"     '<html'    "$base/"

if [ "$fail" = 0 ]; then echo "ALL PASS"; else echo "FAILURES ABOVE"; fi
exit $fail
