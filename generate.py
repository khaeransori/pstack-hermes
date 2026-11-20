#!/usr/bin/env python3
"""Build the Hermes pstack tree from an upstream cursor/plugins checkout.

    python3 generate.py            # rebuild dist/ from the pinned upstream
    python3 generate.py --check    # fail if dist/ is out of date or a check fails
    python3 generate.py --sync     # fetch upstream main, move the pin, rebuild

Skills are copied byte for byte. The only edits are (1) one adapter line after the H1 of every
file that uses a Cursor name, and (2) relative links to files left out of the tree rewritten to
GitHub. Every Cursor term in TERMS that a skill uses must have a row in adapter/hermes.md, or the
build fails. Terms not in TERMS are not detected: when a new upstream term appears, add it there.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UP = ROOT / ".upstream"
PIN = ROOT / "UPSTREAM_PIN"
DIST = ROOT / "dist"
ADAPTER_SRC = ROOT / "adapter" / "hermes.md"
ADAPTER_REL = "docs/harness/hermes.md"
REPO = "https://github.com/cursor/plugins"
COPY_DIRS = ["skills", "agents", "docs/guide", "automations"]
COPY_FILES = ["README.md", "LICENSE", "plugin.json"]
LINK = re.compile(r"\]\(([^)\s]+)\)")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# (adapter key that must appear in hermes.md, regex that detects the Cursor term in a skill)
TERMS = [
    ("`Task`", r"`Task`|\bTask (tool|subagent|call)"),
    ("`AskQuestion`", r"AskQuestion"),
    ("todolist", r"(?i)\btodo ?list\b"),
    ("generalPurpose", r"generalPurpose"),
    ("poteto-agent", r"poteto-agent"),
    ("comment-sicko", r"comment-sicko"),
    ("`readonly: true`", r"readonly: (true|false)|readonly/Ask"),
    ('`environment: "cloud"`', r'environment: "(cloud|local)"'),
    ("cloud_base_branch", r"cloud_base_branch"),
    ("`run_in_background: true`", r"run_in_background"),
    ("`is_background`", r"is_background"),
    ("`resume`", r"`resume`"),
    ("`file_attachments`", r"file_attachments"),
    ("`Await`", r"\bAwait\b"),
    ("`Read`", r"`Read`"),
    ("`Grep`", r"`Grep`|`Glob`"),
    ("`StrReplace`", r"StrReplace"),
    ("`WebFetch`", r"WebFetch|WebSearch"),
    ("`Shell`", r"`Shell`"),
    ("claude-", r"\bclaude-[a-z]+-\d"),
    ("`gpt-*`", r"\bgpt-\d"),
    ("`grok-*`", r"\bgrok-\d"),
    ("`gemini-*`", r"\bgemini-\d"),
    ("inherit-parent", r"inherit-parent"),
    ("pstack-models.mdc", r"pstack-models\.mdc"),
    (".cursor/skills/", r"\.cursor/skills"),
    ("~/.cursor/plugins/", r"\.cursor/plugins|\.cursor-plugin"),
    (".cursor/rules/", r"\.cursor/rules|always-applied rule"),
    (".cursor/automations/", r"\.cursor/automations|\.cursor/benny|\.cursor/settings\.json"),
    ("agent-transcripts", r"agent-transcripts|\.cursor/projects"),
    ("`/loop`", r"`/loop`|\s/loop\b"),
    ("Canvas", r"\bCanvas\b"),
    ("Cursor-only features", r"Bugbot|Cursor [Aa]utomation|cursor\.(sh|com)/automations|[Cc]loud [Aa]gent|built-in PR tool|SendToUser|update_state"),
]
ROUTE_KEY = "Run another pstack skill"
LINE = (f"In Hermes, read [the Hermes adapter](REL) once per session before you follow this file. "
        "It maps the Cursor names in pstack to Hermes tools.")


def git(*args, cwd=UP):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def ensure_upstream(sync=False):
    if not UP.exists():
        subprocess.run(["git", "clone", "-q", REPO, str(UP)], check=True)
    if sync:
        git("fetch", "-q", "origin", "main")
        sha = git("rev-parse", "origin/main")
        PIN.write_text(sha + "\n")
    sha = PIN.read_text().strip()
    try:
        git("cat-file", "-e", sha + "^{commit}")
    except subprocess.CalledProcessError:
        git("fetch", "-q", "origin", "main")
    git("checkout", "-q", "--detach", sha)
    return sha


def walk(d: Path):
    return sorted(p for p in d.rglob("*") if p.is_file() and p.name != ".DS_Store" and "node_modules" not in p.parts)


def build(sha):
    src = UP / "pstack"
    files = {}  # rel path -> (bytes, executable)
    for d in COPY_DIRS:
        for p in walk(src / d):
            files[str(p.relative_to(src))] = (p.read_bytes(), os.access(p, os.X_OK))
    for f in COPY_FILES:
        files[f] = ((src / f).read_bytes(), False)
    files[ADAPTER_REL] = (ADAPTER_SRC.read_bytes(), False)

    skills = sorted(p.parent.name for p in (src / "skills").glob("*/SKILL.md"))
    others = "|".join(map(re.escape, skills))
    route = re.compile(rf"the \*\*(?P<bold>{others})\*\* skill|`/(?P<cmd>{others})`")
    adapter = ADAPTER_SRC.read_text()
    problems, users, wrapped = [], {}, 0

    def classify(prefix):
        used = set()
        for rel, (b, _) in files.items():
            if rel.startswith(prefix) and rel.endswith(".md"):
                t = b.decode("utf-8")
                for key, rx in TERMS:
                    if re.search(rx, t):
                        used.add(key)
                for line in t.split("\n"):
                    for m in route.finditer(line):
                        n = m.group("bold") or m.group("cmd")
                        if f"(../{n}/" not in line:
                            used.add(ROUTE_KEY)
        return used

    benny = sorted(p.parent.name for p in (src / "automations/benny/skills").glob("*/SKILL.md"))
    units = ([f"skills/{s}/" for s in skills] + [f"automations/benny/skills/{s}/" for s in benny]
             + [f"agents/{p.name}" for p in (src / "agents").glob("*.md")])
    for unit in units:
        used = classify(unit)
        for k in used:
            users.setdefault(k, []).append(unit.rstrip("/"))
        head = unit + "SKILL.md" if unit.endswith("/") else unit
        if unit.endswith("/"):
            name = unit.rstrip("/").split("/")[-1]
            fm = re.match(r"^---\n(.*?)\n---", files[head][0].decode(), re.S)
            got = re.search(r"^name:(.*)$", fm.group(1), re.M).group(1).strip().strip("'\"") if fm else ""
            if got != name:
                problems.append(f"{head} has name {got!r}, not its folder name {name}")
            if not SKILL_NAME.match(name) or len(name) > 64:
                problems.append(f"{unit} is not a valid skill name")
        if used:
            text = files[head][0].decode()
            if not re.search(r"^# ", text, re.M):
                problems.append(f"{head} uses Cursor names but has no H1")
                continue
            rel = os.path.relpath(ADAPTER_REL, os.path.dirname(head))
            text = re.sub(r"^(# .*)\n+", lambda m: f"{m.group(1)}\n\n{LINE.replace('REL', rel)}\n\n", text, count=1, flags=re.M)
            files[head] = (text.encode(), files[head][1])
            wrapped += 1
    for key, who in sorted(users.items()):
        if key not in adapter:
            problems.append(f"Hermes adapter has no row for {key}, used by {', '.join(who)}")

    # Links: keep in-tree, point left-out pstack files at GitHub, fail on anything dangling.
    def resolve(frm, href):
        target = re.sub(r"[#?].*", "", href)
        if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            return None
        path = os.path.normpath(os.path.join(os.path.dirname(frm), target))
        return path if (src / path).exists() or path == ADAPTER_REL else None

    def has(path):
        return path in files or any(k.startswith(path + "/") for k in files)

    for rel, (b, x) in list(files.items()):
        if not rel.endswith(".md"):
            continue
        def fix(m, rel=rel):
            href = m.group(1)
            t = resolve(rel, href)
            if not t or t.startswith("..") or has(t):
                return m.group(0)
            kind = "tree" if (src / t).is_dir() else "blob"
            tail = href[len(re.sub(r"[#?].*", "", href)):]
            return f"]({REPO}/{kind}/{sha}/pstack/{t}{tail})"
        files[rel] = (LINK.sub(fix, b.decode()).encode(), x)
        for href in LINK.findall(files[rel][0].decode()):
            t = resolve(rel, href)
            if t and not has(t):
                problems.append(f"{rel} links to {href}, which is not in the tree")

    files["UPSTREAM.json"] = (json.dumps({
        "repo": REPO, "commit": sha, "commit_date": git("log", "-1", "--format=%cI", sha),
        "pstack_version": json.loads((src / "plugin.json").read_text())["version"],
        "skills": len(skills), "benny_reference_skills": len(benny), "files_with_adapter_line": wrapped,
    }, indent=2).encode() + b"\n", False)
    files["router/SKILL.md"] = (router(src, skills, sha, benny).encode(), False)
    return files, problems, skills + benny, wrapped


def router(src, skills, sha, benny):
    rows = []
    for s in skills:
        fm = re.match(r"^---\n(.*?)\n---", (src / "skills" / s / "SKILL.md").read_text(), re.S).group(1)
        m = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", fm, re.M | re.S)
        d = re.sub(r"\s+", " ", m.group(1)).replace('\\"', '"').replace('"', "'").strip().strip("'>- ") if m else ""
        d = d[:220] + ("…" if len(d) > 220 else "")
        rows.append(f"- `{s}`: {d}")
    return f"""---
name: pstack
description: "Use when doing rigorous engineering with pstack (poteto-mode, /correct, verification). Routes to the 58 upstream pstack skills."
version: 1.0.0
author: Lauren Tan (pstack, MIT); Hermes adapter khaeransori/pstack-hermes
license: MIT
metadata:
  hermes:
    tags: [pstack, poteto, code-quality, verification, lint, agents]
---

# pstack (Hermes)

Generated by pstack-hermes `generate.py` from cursor/plugins `{sha[:12]}`. Do not edit by hand.

pstack is Lauren Tan's (poteto) skill set: push every correction up the pyramid (codebase > static analysis > verification > prose > human review), and make agents prove their work. The skill text is upstream, byte for byte.

## How to run a pstack skill

1. `read_file` `~/.hermes/pstack/docs/harness/hermes.md` once per session. It maps every Cursor name in pstack to a Hermes tool.
2. `read_file` `~/.hermes/pstack/skills/<name>/SKILL.md` and follow it. Its `references/`, `playbooks/`, and `scripts/` sit beside it.
3. The user says "pstack <name>" or "/<name>" for these. For rigorous work with no named skill, start with `poteto-mode`; it picks a playbook.

Hermes house rules win over a pstack step: ask before sending anything outside the chat, never handle secrets by hand, ask before creating cron jobs or changing config.

Maintaining this port: edit `~/pstack-hermes/adapter/hermes.md` or `generate.py`, never `dist/` (this file is generated too). After any change run `python3 generate.py && python3 generate.py --check`. The build only catches Cursor terms listed in `TERMS`; when a run finds an unmapped term, add it to `TERMS` and a row to the adapter. Smoke-test new rows by delegating a report-only run of a pstack skill with only the adapter as context.

Upstream skill docs: `~/.hermes/pstack/README.md`, guide in `~/.hermes/pstack/docs/guide/`. Re-sync: `python3 ~/pstack-hermes/generate.py --sync`.

## Skills

{chr(10).join(rows)}

## Reference only: Benny automations

Upstream ships these as dormant Cursor Automation sources (Slack bug triage, then repro and a draft fix PR), not as slash skills. They are in `~/.hermes/pstack/automations/benny/` for reading. Do not run them as a normal skill. Wiring them up means a new Hermes webhook or cron flow, and it posts to Slack, opens tickets and PRs, so ask the user before building it.

{chr(10).join(f"- `{b}`: `automations/benny/skills/{b}/SKILL.md`" for b in benny)}
"""


def main():
    sync, check = "--sync" in sys.argv, "--check" in sys.argv
    sha = ensure_upstream(sync)
    files, problems, skills, wrapped = build(sha)
    for p in problems:
        print("FAIL", p)
    if problems:
        sys.exit(1)
    if check:
        on_disk = {str(p.relative_to(DIST)): (p.read_bytes(), os.access(p, os.X_OK)) for p in walk(DIST)} if DIST.exists() else {}
        drift = sorted(k for k in set(files) | set(on_disk) if files.get(k) != on_disk.get(k))
        for k in drift[:20]:
            print("DRIFT", k)
        if drift:
            print(f"dist/ is out of date ({len(drift)} files). Run python3 generate.py")
            sys.exit(1)
        print(f"dist/ up to date: {len(skills)} skills, upstream {sha[:12]}")
        return
    shutil.rmtree(DIST, ignore_errors=True)
    for rel, (b, x) in files.items():
        p = DIST / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        p.chmod(0o755 if x else 0o644)
    print(f"{len(skills)} skills, {wrapped} files with the adapter line, {len(files)} files, upstream {sha[:12]}")


if __name__ == "__main__":
    main()
