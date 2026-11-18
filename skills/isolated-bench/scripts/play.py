#!/usr/bin/env python3
"""Play use cases inside the bench container. Usage: play.py --lot 1 | --ids CU-001,CU-002 [--out /out]."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CAS = Path(os.environ.get("BENCH_CASES", "/bench/cases.jsonl"))


def load():
    return [json.loads(l) for l in CAS.read_text(encoding="utf-8").splitlines() if l.strip()]


def prepare(case):
    work = Path("/tmp/cases") / case["id"]
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    env = dict(os.environ, PILOT_DIR=str(work / "state"), BASH_ENV=os.environ.get("BENCH_HELPERS", "/bench/helpers.sh"))
    subprocess.run("git init -q && git config user.email bench@example.invalid && git config user.name bench",
                   shell=True, cwd=work, env=env)
    if case["kind"] == "claude":
        (work / ".claude").mkdir()
        (work / ".claude" / "settings.json").write_text(json.dumps({"env": {"PILOT_DIR": env["PILOT_DIR"]}}))
    if case.get("setup"):
        subprocess.run(["bash", "-c", case["setup"]], cwd=work, env=env, capture_output=True, text=True)
    env.update(case.get("env", {}))
    return work, env


def play_script(case, work, env):
    r = subprocess.run(["bash", "-c", case["cmd"]], cwd=work, env=env, capture_output=True, text=True, timeout=case.get("timeout", 120))
    output = (r.stdout + r.stderr)[-1500:]
    ok = r.returncode == case.get("expect_rc", 0)
    if ok and case.get("expect_re"):
        ok = re.search(case["expect_re"], r.stdout + r.stderr, re.M) is not None
    return ok, f"rc={r.returncode} output={output.strip()!r}", {}


def tools_of(trace):
    skills, tools, blocks = [], [], 0
    for line in trace.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "assistant":
            for c in (e.get("message") or {}).get("content") or []:
                if c.get("type") == "tool_use":
                    tools.append(c["name"])
                    if c["name"] == "Skill":
                        skills.append(str((c.get("input") or {}).get("skill", "")).split(":")[-1])
        if e.get("subtype") == "hook_response" and '"block"' in (e.get("stdout") or "") + (e.get("output") or ""):
            blocks += 1
    return skills, tools, blocks


def isolation_broken(trace):
    for line in trace.splitlines()[:5]:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("subtype") == "init":
            mcp = [t for t in e.get("tools", []) if t.startswith("mcp__")]
            servers = [m.get("name") for m in e.get("mcp_servers", [])]
            if mcp or servers:
                return f"{len(mcp)} MCP tools, servers {servers[:5]}"
    return ""


def play_claude(case, work, env, out):
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", case["prompt"], "--output-format", "stream-json",
           "--verbose", "--include-hook-events", "--max-turns", str(case.get("max_turns", 10)),
           "--strict-mcp-config", "--mcp-config", '{"mcpServers": {}}']
    if os.environ.get("BANC_MODEL"):
        cmd += ["--model", os.environ["BANC_MODEL"]]
    try:
        r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=case.get("timeout", 420))
        trace, rc = r.stdout, r.returncode
    except subprocess.TimeoutExpired as exc:
        trace, rc = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""), 124
    leak = isolation_broken(trace)
    (out / "traces").mkdir(parents=True, exist_ok=True)
    if leak:
        return False, f"ISOLATION BROKEN, trace not kept: {leak}", {}
    (out / "traces" / f"{case['id']}.jsonl").write_text(trace, encoding="utf-8")
    skills, tools, blocks = tools_of(trace)
    expected = case.get("skill")
    reasons = []
    if expected == "none":
        ok = not skills
        if not ok:
            reasons.append(f"skill loaded although not expected: {skills}")
    elif expected:
        ok = expected in skills
        if not ok:
            reasons.append(f"skill {expected} missing (seen: {skills or 'none'})")
    else:
        ok = True
    if case.get("hook_block") and blocks == 0:
        ok = False
        reasons.append("hook did not block")
    if case.get("check"):
        c = subprocess.run(["bash", "-c", case["check"]], cwd=work, env=env, capture_output=True, text=True)
        if c.returncode:
            ok = False
            reasons.append(f"check failed: {(c.stdout + c.stderr).strip()[-300:]!r}")
    if rc not in (0,) and not reasons and rc != 124:
        reasons.append(f"claude rc={rc}")
    if rc == 124:
        ok = False
        reasons.append("timed out")
    end = ""
    for line in trace.splitlines()[::-1]:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "result":
            end = f"turns={e.get('num_turns')} cost={e.get('total_cost_usd')}"
            break
    detail = "; ".join(reasons) or "as expected"
    return ok, f"{detail} | skills={skills} tools={tools[:12]} hook_blocks={blocks} {end}", {"skills": skills}


def play(case, out):
    start = time.time()
    if case["kind"] == "nt":
        return {"id": case["id"], "verdict": "NOT TESTABLE", "trace": case["reason"], "s": 0}
    work, env = prepare(case)
    try:
        if case["kind"] == "script":
            ok, trace, _ = play_script(case, work, env)
        else:
            ok, trace, _ = play_claude(case, work, env, out)
    except Exception as exc:  # the bench records, it does not stop
        ok, trace = False, f"exception {exc!r}"
    return {"id": case["id"], "verdict": "OK" if ok else "FAILED", "trace": trace, "s": round(time.time() - start)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lot", type=int)
    p.add_argument("--ids")
    p.add_argument("--out", default="/out")
    p.add_argument("--parallel", type=int, default=4)
    a = p.parse_args()
    cases = load()
    if a.ids:
        wanted = set(a.ids.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    elif a.lot:
        cases = [c for c in cases if c.get("lot") == a.lot]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scripts = [c for c in cases if c["kind"] != "claude"]
    agents = [c for c in cases if c["kind"] == "claude"]
    results = [play(c, out) for c in scripts]
    with ThreadPoolExecutor(a.parallel) as ex:
        results += list(ex.map(lambda c: play(c, out), agents))
    results.sort(key=lambda r: r["id"])
    with open(out / "results.jsonl", "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for r in results:
        print(f"{r['id']}  {r['verdict']:<12} {r['s']:>4}s  {r['trace'][:160]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
