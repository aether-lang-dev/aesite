# Live playground backend: serves the site and runs /api/exec.
# The Aether toolchain must be present at runtime too, since /api/exec
# compiles and runs submitted code.
#
# This image runs UNTRUSTED code. It runs as a non-root user, and each
# submission runs in a private network namespace with ulimits and a timeout
# (see serve.ae). That is a baseline, not a full sandbox: deploy it on a
# disposable, resource-capped VM/microVM, e.g.
#   docker run --rm --read-only --tmpfs /tmp --pids-limit=256 \
#              --memory=512m --cpus=1 -p 8080:8080 aesite
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates gcc make git util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 runner
USER runner
WORKDIR /home/runner/app
COPY --chown=runner:runner . .

# Same install method the CI uses (proven), scoped to the runner user.
RUN curl -sSL https://raw.githubusercontent.com/aether-lang-org/aether/main/get.sh \
      | PREFIX="$HOME/.local" sh
ENV PATH="/home/runner/.local/bin:${PATH}"
RUN ae build serve.ae -o aesite-serve

# serve.ae reads $PORT; 8080 suits Fly/Render/Cloud Run.
ENV PORT=8080
EXPOSE 8080
CMD ["/home/runner/app/aesite-serve"]
