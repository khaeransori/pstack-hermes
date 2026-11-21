#!/usr/bin/env python3
"""Build the Hermes pstack tree from an upstream cursor/plugins checkout.

    python3 generate.py            # rebuild dist/ from the pinned upstream
    python3 generate.py --check    # fail if dist/ is out of date or a check fails
    python3 generate.py --sync     # fetch upstream main, move the pin, rebuild

Skills are copied byte for byte. The only edits are (1) one adapter line after the H1 of every
file that uses a Cursor name, and (2) relative links to files left out of the tree rewritten to
GitHub. Every Cursor term in TERMS that a skill uses must have a row in adapter/hermes.md, or
the build fails. Terms not in TERMS are not detected: when a new upstream term appears, add it there.
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
REPO = "https://github.com/cursor/plugins"
COPY_DIRS = ["skills", "agents", "docs/guide", "automations"]
COPY_FILES = ["README.md", "LICENSE", "plugin.json"]
LINK = re.compile(r"\]\(([^)\s]+)\)")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

TARGETS = {
    "hermes": {
        "label": "Hermes",
        "home": "~/.hermes/pstack",
        "read": "`read_file`",
        "invoke": "pstack <name>",
        "rules": "Hermes house rules win over a pstack step: ask before sending anything outside the chat, "
                 "never handle secrets by hand, ask before creating cron jobs or changing config.",
        "frontmatter": "version: 1.0.0\nauthor: Lauren Tan (pstack, MIT); adapter khaeransori/pstack-hermes\n"
                       "license: MIT\nmetadata:\n  hermes:\n    tags: [pstack, poteto, code-quality, verification, lint, agents]\n",
    },
}

# (adapter key that must appear in every adapter, regex that detects the Cursor term in a skill)
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
    ("Project worker", r"Project workers?\b"),
    ("in CI", r"locally and in CI"),
    ("Cursor-only features", r"Bugbot|Cursor [Aa]utomation|cursor\.(sh|com)/automations|[Cc]loud [Aa]gent|built-in PR tool|SendToUser|update_state"),
]
ROUTE_KEY = "Run another pstack skill"


def git(*args, cwd=UP):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def ensure_upstream(sync=False):
    if not UP.exists():
        subprocess.run(["git", "clone", "-q", REPO, str(UP)], check=True)
    if sync:
        git("fetch", "-q", "origin", "main")
        PIN.write_text(git("rev-parse", "origin/main") + "\n")
    sha = PIN.read_text().strip()
    try:
        git("cat-file", "-e", sha + "^{commit}")
    except subprocess.CalledProcessError:
        git("fetch", "-q", "origin", "main")
    git("checkout", "-q", "--detach", sha)
    return sha


def walk(d: Path):
    return sorted(p for p in d.rglob("*") if p.is_file() and p.name != ".DS_Store" and "node_modules" not in p.parts)


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def build(sha, target):
    cfg = TARGETS[target]
    adapter_src = ROOT / "adapter" / f"{target}.md"
    adapter_rel = f"docs/harness/{target}.md"
    line = (f"In {cfg['label']}, read [the {cfg['label']} adapter](REL) once per session before you follow "
            f"this file. It maps the Cursor names in pstack to {cfg['label']} tools.")
    src = UP / "pstack"
    files = {}
    for d in COPY_DIRS:
        for p in walk(src / d):
            files[str(p.relative_to(src))] = (p.read_bytes(), os.access(p, os.X_OK))
    for f in COPY_FILES:
        files[f] = ((src / f).read_bytes(), False)
    files[adapter_rel] = (adapter_src.read_bytes(), False)

    skills = sorted(p.parent.name for p in (src / "skills").glob("*/SKILL.md"))
    benny = sorted(p.parent.name for p in (src / "automations/benny/skills").glob("*/SKILL.md"))
    route = re.compile(rf"the \*\*(?P<bold>{'|'.join(map(re.escape, skills))})\*\* skill|`/(?P<cmd>{'|'.join(map(re.escape, skills))})`")
    adapter = adapter_src.read_text()
    problems, users, wrapped = [], {}, 0

    def terms_used(prefix):
        used = set()
        for rel, (b, _) in files.items():
            if rel.startswith(prefix) and rel.endswith(".md"):
                t = b.decode("utf-8")
                used.update(key for key, rx in TERMS if re.search(rx, t))
                for ln in t.split("\n"):
                    for m in route.finditer(ln):
                        if f"(../{m.group('bold') or m.group('cmd')}/" not in ln:
                            used.add(ROUTE_KEY)
        return used

    units = ([f"skills/{s}/" for s in skills] + [f"automations/benny/skills/{s}/" for s in benny]
             + [f"agents/{p.name}" for p in sorted((src / "agents").glob("*.md"))])
    for unit in units:
        used = terms_used(unit)
        for k in used:
            users.setdefault(k, []).append(unit.rstrip("/"))
        head = unit + "SKILL.md" if unit.endswith("/") else unit
        if unit.endswith("/"):
            name = unit.rstrip("/").split("/")[-1]
            m = re.search(r"^name:(.*)$", frontmatter(files[head][0].decode()), re.M)
            got = m.group(1).strip().strip("'\"") if m else ""
            if got != name:
                problems.append(f"{head} has name {got!r}, not its folder name {name}")
            if not SKILL_NAME.match(name) or len(name) > 64:
                problems.append(f"{unit} is not a valid skill name")
        if used:
            text = files[head][0].decode()
            if not re.search(r"^# ", text, re.M):
                problems.append(f"{head} uses Cursor names but has no H1")
                continue
            rel = os.path.relpath(adapter_rel, os.path.dirname(head))
            text = re.sub(r"^(# .*)\n+", lambda m: f"{m.group(1)}\n\n{line.replace('REL', rel)}\n\n", text, count=1, flags=re.M)
            files[head] = (text.encode(), files[head][1])
            wrapped += 1
    for key, who in sorted(users.items()):
        if key not in adapter:
            problems.append(f"{target} adapter has no row for {key}, used by {', '.join(who)}")

    problems += rewrite_links(files, src, sha, adapter_rel)

    files["UPSTREAM.json"] = (json.dumps({
        "repo": REPO, "commit": sha, "commit_date": git("log", "-1", "--format=%cI", sha),
        "pstack_version": json.loads((src / "plugin.json").read_text())["version"], "target": target,
        "skills": len(skills), "benny_reference_skills": len(benny), "files_with_adapter_line": wrapped,
    }, indent=2).encode() + b"\n", False)
    files["router/SKILL.md"] = (router(src, skills, benny, sha, target).encode(), False)
    return files, problems, len(skills) + len(benny), wrapped


def rewrite_links(files, src, sha, adapter_rel):
    """Keep in-tree links, point left-out pstack files at GitHub, and report anything dangling."""
    problems = []

    def resolve(frm, href):
        target = re.sub(r"[#?].*", "", href)
        if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            return None
        path = os.path.normpath(os.path.join(os.path.dirname(frm), target))
        return path if (src / path).exists() or path == adapter_rel else None

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
            return f"]({REPO}/{kind}/{sha}/pstack/{t}{href[len(re.sub(r'[#?].*', '', href)):]})"

        files[rel] = (LINK.sub(fix, b.decode()).encode(), x)
        for href in LINK.findall(files[rel][0].decode()):
            t = resolve(rel, href)
            if t and not has(t):
                problems.append(f"{rel} links to {href}, which is not in the tree")
    return problems


def router(src, skills, benny, sha, target):
    cfg = TARGETS[target]
    rows = []
    for s in skills:
        m = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", frontmatter((src / "skills" / s / "SKILL.md").read_text()), re.M | re.S)
        d = re.sub(r"\s+", " ", m.group(1)).replace('\\"', '"').replace('"', "'").strip().strip("'>- ") if m else ""
        rows.append(f"- `{s}`: {d[:220]}{'…' if len(d) > 220 else ''}")
    home, read = cfg["home"], cfg["read"]
    return f"""---
name: pstack
description: "Use when doing rigorous engineering with pstack (poteto-mode, correct, verification, unslop). Routes to the {len(skills)} upstream pstack skills."
{cfg['frontmatter']}---

# pstack ({cfg['label']})

Generated by pstack-hermes `generate.py` from cursor/plugins `{sha[:12]}`. Do not edit by hand.

pstack is Lauren Tan's (poteto) skill set: push every correction up the pyramid (codebase > static analysis > verification > prose > human review), and make agents prove their work. The skill text is upstream, byte for byte.

## How to run a pstack skill

1. {read} `{home}/docs/harness/{target}.md` once per session. It maps every Cursor name in pstack to a {cfg['label']} tool.
2. {read} `{home}/skills/<name>/SKILL.md` and follow it. Its `references/`, `playbooks/`, and `scripts/` sit beside it.
3. The user says "{cfg['invoke']}" or "/<name>" for these. For rigorous work with no named skill, start with `poteto-mode`; it picks a playbook.

{cfg['rules']}

Maintaining this port: edit `adapter/{target}.md` or `generate.py` in pstack-hermes, never the generated tree. After any change run `python3 generate.py && python3 generate.py --check`. The build only catches Cursor terms listed in `TERMS`; when a run finds an unmapped term, add it to `TERMS` and a row to the adapter.

Upstream skill docs: `{home}/README.md`, guide in `{home}/docs/guide/`.

## Skills

{chr(10).join(rows)}

## Reference only: Benny automations

Upstream ships these as dormant Cursor Automation sources (Slack bug triage, then repro and a draft fix PR), not as slash skills. They are in `{home}/automations/benny/` for reading. Do not run them as a normal skill. Wiring them up means a new scheduled or webhook flow that posts to Slack and opens tickets and PRs, so ask the user before building it.

{chr(10).join(f"- `{b}`: `automations/benny/skills/{b}/SKILL.md`" for b in benny)}
"""


HUB = ROOT / "skills"
HUB_REPO = "khaeransori/pstack-hermes"
HUB_ADAPTER = "references/pstack-hermes-adapter.md"
# Left out of the hub: make-bot-ui needs sudo to install Tailscale (the Skills Guard blocks it for
# community installs), and statechart's test corpus is 377 fixture files no run reads.
HUB_SKIP_SKILLS = {"make-bot-ui"}
HUB_SKIP_PATHS = [re.compile(r"^skills/statechart/scripts/test/")]
HUB_INTRO = ("`<pstack>` means the folder that holds `skills/`, `agents/`, and `docs/`. "
             "In this install it is `~/.hermes/pstack`.")
HUB_ROUTE = ("`read_file` `<pstack>/skills/<name>/SKILL.md` and follow it. These skills are not in the Hermes "
             "skill index, so `skill_view` cannot find them. When you tell the user to type it, write `pstack <name>`.")


def hub_adapter(dist_adapter, sha, version):
    text = dist_adapter
    for old, new in [
        (HUB_INTRO, f"This copy ships inside a skill installed from the Hermes Skills Hub (`{HUB_REPO}`, pstack "
                    f"{version}, upstream `{sha[:12]}`), so there is no `<pstack>` tree. Map its paths: "
                    "`<pstack>/skills/<name>/` is the installed `<name>` skill folder (`skill_view(name)` shows its "
                    "path); `<pstack>/agents/<file>` is `references/agents/<file>` in the skill you are running; "
                    "`<pstack>/plugin.json` and `<pstack>/docs/` are on GitHub at "
                    f"{REPO}/tree/{sha}/pstack. Give absolute paths to children."),
        (HUB_ROUTE, "`skill_view(name)` and follow it. If it is not installed, ask the user to run "
                    f"`hermes skills install {HUB_REPO}/skills/<name> --category pstack` (one-time). When you tell "
                    "the user to type it, write `pstack <name>`."),
    ]:
        if old not in text:
            raise SystemExit(f"FAIL hub: adapter text changed, update HUB_INTRO/HUB_ROUTE in generate.py: {old[:60]}")
        text = text.replace(old, new)
    return text


def build_hub(files, sha):
    """Hub layout for `hermes skills tap add` / install: one self-contained folder per skill under skills/."""
    meta = json.loads(files["UPSTREAM.json"][0])
    adapter = hub_adapter(files["docs/harness/hermes.md"][0].decode(), sha, meta["pstack_version"])
    skills = sorted({k.split("/")[1] for k in files if re.match(r"skills/[^/]+/SKILL\.md$", k)} - HUB_SKIP_SKILLS)
    agents = {k.split("/")[-1]: v for k, v in files.items() if k.startswith("agents/")}
    hub = {}

    def target(frm, href):
        t = re.sub(r"[#?].*", "", href)
        if not t or re.match(r"^[a-z][a-z0-9+.-]*:", t, re.I):
            return None
        return os.path.normpath(os.path.join(os.path.dirname(frm), t))

    for s in skills:
        own = {k: v for k, v in files.items()
               if k.startswith(f"skills/{s}/") and not any(rx.match(k) for rx in HUB_SKIP_PATHS)}
        text_all = "".join(b.decode("utf-8", "ignore") for k, (b, _) in own.items() if k.endswith(".md"))
        for name, v in agents.items():
            if name[:-3] in text_all:
                own[f"skills/{s}/references/agents/{name}"] = v
        own[f"skills/{s}/{HUB_ADAPTER}"] = (adapter.encode(), False)
        for rel, (b, x) in list(own.items()):
            if not rel.endswith(".md") or rel.endswith(HUB_ADAPTER):
                continue

            def fix(m, rel=rel):
                href = m.group(1)
                t = target(rel, href)
                frag = href[len(re.sub(r"[#?].*", "", href)):]
                if t is None or t in own or any(k.startswith(t + "/") for k in own):
                    return m.group(0)
                if t == "docs/harness/hermes.md":
                    return f"]({os.path.relpath(f'skills/{s}/{HUB_ADAPTER}', os.path.dirname(rel))}{frag})"
                sib = re.match(r"skills/([^/]+)(/.*)?$", t)
                if sib and sib.group(1) in skills and sib.group(1) != s:
                    return m.group(0)  # sibling skill: same category folder once both are installed
                kind = "tree" if (UP / "pstack" / t).is_dir() else "blob"
                return f"]({REPO}/{kind}/{sha}/pstack/{t}{frag})"

            own[rel] = (LINK.sub(fix, b.decode()).encode(), x)
        hub.update(own)
    hub["skills/pstack/SKILL.md"] = (hub_router(files, skills, sha).encode(), False)
    hub["skills/pstack/" + HUB_ADAPTER] = (adapter.encode(), False)
    hub["skills/README.md"] = (hub_readme(skills, meta).encode(), False)
    return {k[len("skills/"):]: v for k, v in hub.items()}


def hub_router(files, skills, sha):
    body = files["router/SKILL.md"][0].decode()
    rows = "\n".join(l for l in body.split("\n") if re.match(r"- `[a-z0-9-]+`: ", l) and l.split("`")[1] in skills)
    return f"""---
name: pstack
description: "Use when doing rigorous engineering with pstack (poteto-mode, correct, verification, unslop). Index of the pstack skills and how to run them in Hermes."
{TARGETS['hermes']['frontmatter']}---

# pstack (Hermes Skills Hub)

Generated by pstack-hermes `generate.py` from cursor/plugins `{sha[:12]}`. Do not edit by hand.

pstack is Lauren Tan's (poteto) skill set: push every correction up the pyramid (codebase > static analysis > verification > prose > human review), and make agents prove their work. The skill text is upstream, byte for byte, with one adapter line added.

## How to run a pstack skill

1. `read_file` [`{HUB_ADAPTER}`]({HUB_ADAPTER}) once per session. It maps every Cursor name in pstack to a Hermes tool.
2. `skill_view(<name>)` and follow it. If it is not installed, ask the user to run `hermes skills install {HUB_REPO}/skills/<name> --category pstack`, or install the whole set with `hermes skills tap add {HUB_REPO}`.
3. The user says "pstack <name>" or "/<name>" for these. For rigorous work with no named skill, start with `poteto-mode`; it picks a playbook.

{TARGETS['hermes']['rules']}

Not in the hub build: `make-bot-ui` (its Tailscale setup needs root) and the Benny automations. Get them from the full install at https://github.com/{HUB_REPO}.

## Skills

{rows}
"""


def hub_readme(skills, meta):
    return f"""# pstack skills for the Hermes Skills Hub

Generated by `generate.py` from cursor/plugins `{meta['commit'][:12]}` (pstack {meta['pstack_version']}). Do not edit by hand.

{len(skills)} pstack skills plus the `pstack` index skill, one self-contained folder each, with the Hermes adapter in `{HUB_ADAPTER}`.

```sh
hermes skills tap add {HUB_REPO}                                  # browse and search all of them
hermes skills install {HUB_REPO}/skills/poteto-mode --category pstack
```

Install into one category (`pstack`) so links between sibling skills resolve. For the full tree with the Benny automations, the guide, and `make-bot-ui`, use `install.sh` from the repo root instead.
"""


def write_tree(out, files):
    shutil.rmtree(out, ignore_errors=True)
    for rel, (b, x) in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        p.chmod(0o755 if x else 0o644)


def drift(out, files):
    on_disk = {str(p.relative_to(out)): (p.read_bytes(), os.access(p, os.X_OK)) for p in walk(out)} if out.exists() else {}
    return sorted(k for k in set(files) | set(on_disk) if files.get(k) != on_disk.get(k))


def main():
    sync, check = "--sync" in sys.argv, "--check" in sys.argv
    sha = ensure_upstream(sync)
    failed = False
    for target in TARGETS:
        files, problems, n, wrapped = build(sha, target)
        out = DIST
        for p in problems:
            print("FAIL", target, p)
        if problems:
            failed = True
            continue
        hub = build_hub(files, sha)
        if check:
            hub_drift = drift(HUB, hub)
            for k in hub_drift[:20]:
                print("DRIFT hub", k)
            if hub_drift:
                print(f"skills/ is out of date ({len(hub_drift)} files). Run python3 generate.py")
                failed = True
        else:
            write_tree(HUB, hub)
            print(f"hub: {len({k.split('/')[0] for k in hub}) - 1} skills, {len(hub)} files in skills/")
        if check:
            dist_drift = drift(out, files)
            for k in dist_drift[:20]:
                print("DRIFT", target, k)
            if dist_drift:
                print(f"dist/ is out of date ({len(dist_drift)} files). Run python3 generate.py")
                failed = True
            elif not failed:
                print(f"dist/ and skills/ up to date: {n} skills, upstream {sha[:12]}")
            continue
        write_tree(out, files)
        print(f"{target}: {n} skills, {wrapped} files with the adapter line, {len(files)} files, upstream {sha[:12]}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
