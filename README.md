# pstack-hermes

[pstack](https://github.com/cursor/plugins/tree/main/pstack), the skill set by Lauren Tan ([@poteto](https://x.com/poteto)), packaged for [Hermes Agent](https://github.com/NousResearch/hermes-agent) and [OpenAI Codex](https://github.com/openai/codex).

The skills are not rewritten. This repo has three parts:

- `adapter/hermes.md` and `adapter/codex.md` map the Cursor names used in pstack (`Task`, `AskQuestion`, `readonly`, `environment: "cloud"`, `/loop`, Bugbot, transcript paths, and so on) to each harness's tools. They follow the same approach as upstream's own [Claude Code adapter](https://github.com/cursor/plugins/blob/main/pstack/docs/harness/claude-code.md).
- `generate.py` builds `dist/hermes/` and `dist/codex/` from one pinned upstream commit. It copies every skill, agent, guide page, and the Benny automation sources as they are, and makes two kinds of edit only:
  1. It adds one line after the H1 of each file that uses a Cursor name, telling the agent to read its adapter first.
  2. It points relative links to files outside the tree at GitHub.
- `install.sh` builds, checks, and links one tree into place.

The build fails when a skill uses a known Cursor term that has no row in an adapter. `--check` fails when a tree in `dist/` has drifted from what the generator would produce.

## Install for Codex

```sh
git clone https://github.com/khaeransori/pstack-hermes ~/pstack-hermes
cd ~/pstack-hermes
./install.sh codex
```

This links `~/.codex/pstack` (the full tree) and `~/.agents/skills/pstack` (one router skill). Codex lists only the router in its skill catalog, so the 61 upstream skills cost no prompt tokens until one is used. Restart Codex, then name a skill: `$pstack correct on this repo`, or `$pstack poteto-mode: fix the scroll drift bug`.

`CODEX_HOME` is respected. To share it with a team through one repo instead, link `dist/codex/router` into `<repo>/.agents/skills/pstack` and change the paths in the router to match.

### Limits in Codex

- **OpenAI models only.** `spawn_agent` takes a `model` and `reasoning_effort`, so pstack roles keep their effort and a panel can mix OpenAI models, but not vendors. The agent says when a panel ran single-vendor.
- **No nesting by default.** `agents.max_depth` defaults to 1. The chat that runs the skill owns all spawning.
- **Shared working directory.** All agents edit the same checkout, so parallel writers each get a git worktree.
- **Asking questions.** `request_user_input` exists only in Plan mode (up to 3 questions). In Default mode the adapter uses `request_user_input_async` or plain text.
- **Sandbox and approvals win.** Children inherit the parent's sandbox; the agent requests escalation instead of working around it.
- Bugbot, Cursor cloud agents, Canvas, and Automations are skipped with a one-line note. `gh`, worktrees, and `codex review` stand in where they fit.

## Install for Hermes

```sh
git clone https://github.com/khaeransori/pstack-hermes ~/pstack-hermes
cd ~/pstack-hermes
./install.sh hermes
```

This links `~/.hermes/pstack` and a single `pstack` skill in `~/.hermes/skills/software-development/`. Use it by naming a skill, for example `pstack correct on this repo` or `poteto-mode: fix the scroll drift bug`. For a profile, link into `~/.hermes/profiles/<name>/skills/` instead.

### Limits in Hermes

- **One model.** `delegate_task` has no model setting per task, so multi-vendor panels (`arena`, `interrogate`) run with one model and a different framing for each seat. The agent says so when this happens.
- **No nesting.** A child cannot spawn its own children or call `clarify`. The chat that runs the skill owns all spawning.
- **House rules take priority.** The agent still asks before sending anything outside the chat, creating cron jobs, or changing config, even when a playbook says "don't ask".
- Bugbot, cloud agents, Canvas, and Automations are skipped with a one-line note. Worktrees, `gh`, and cron (after asking) stand in where they fit.

## Update

```sh
python3 generate.py --sync    # move UPSTREAM_PIN to cursor/plugins main, rebuild both trees, run the checks
python3 generate.py --check   # verify dist/ matches the pin and every Cursor term has a row in every adapter
```

The symlinks point into `dist/`, so a rebuild updates the installed skills in place. The term check covers only the Cursor terms listed in `TERMS` in `generate.py`. If a new upstream term shows up in a run, add it to `TERMS`, add a row to each adapter, and rebuild.

## What you get

- 58 pstack skills (workflow, `poteto-mode` and its playbooks, and 23 `principle-*` skills), plus `agents/` and `docs/guide/`.
- `automations/benny/` as reference only. Upstream ships these as dormant Cursor Automation sources; wiring them up is a separate scheduled or webhook flow you build yourself.
- `statechart` and `poteto-mode/scripts` need Node or Bun dependencies the first time they run.

## License

pstack content in `dist/` and `.upstream/`: MIT, © 2026 Lauren Tan (see upstream `LICENSE`). The adapters, generator, and installer in this repo: MIT, see `LICENSE`. This is an unofficial port and is not affiliated with Cursor, OpenAI, or Nous Research.
