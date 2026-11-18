FROM python:3.12-slim AS app
RUN useradd --uid 1000 --create-home --home-dir /pilot --shell /bin/bash pilot \
    && mkdir /out && chown pilot:pilot /out
USER pilot
ENV HOME=/pilot \
    PATH=/pilot/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /pilot/claude-pilot-pack
COPY --chown=pilot:pilot LICENSE README.md AGENTS.md ./
COPY --chown=pilot:pilot skills ./skills
COPY --chown=pilot:pilot hooks ./hooks
COPY --chown=pilot:pilot templates ./templates
COPY --chown=pilot:pilot demo ./demo
RUN mkdir -p ~/.claude/skills ~/.claude/hooks ~/.local/bin \
    && cp -r skills/* ~/.claude/skills/ \
    && chmod +x ~/.claude/skills/sub-session/scripts/sub-session ~/.claude/skills/question-registry/scripts/q \
    && ln -sf ~/.claude/skills/sub-session/scripts/sub-session ~/.local/bin/sub-session \
    && ln -sf ~/.claude/skills/question-registry/scripts/q ~/.local/bin/q \
    && cp hooks/q-registered.py ~/.claude/hooks/ \
    && printf '%s\n' '{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/q-registered.py"}]}]}}' > ~/.claude/settings.json \
    && PILOT_DIR="$(mktemp -d)" q new --source build "Does the registry work?" | grep -qx Q1

FROM app AS test
COPY --chown=pilot:pilot tests ./tests
CMD ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]

FROM app
CMD ["python3", "demo/run.py", "--out", "/out/index.html"]
