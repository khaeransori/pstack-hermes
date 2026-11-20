# pstack-hermes

[pstack](https://github.com/cursor/plugins/tree/main/pstack), the skill set by Lauren Tan ([@poteto](https://x.com/poteto)), packaged for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

The skills are not rewritten. This repo has two parts:

- `adapter/hermes.md` maps the Cursor names used in pstack (`Task`, `AskQuestion`, `readonly`, `environment: "cloud"`, `/loop`, Bugbot, transcript paths, and so on) to Hermes tools (`delegate_task`, `clarify`, `todo_list`, `cronjob_manage`, `gh`, worktrees). It follows the same approach as upstream's own [Claude Code adapter](https://github.com/cursor/plugins/blob/main/pstack/docs/harness/claude-code.md).
- `generate.py` builds `dist/` from a pinned upstream commit. It copies every skill, agent, guide page, and the Benny automation sources as they are, and makes two kinds of edit only:
  1. It adds one line after the H1 of each file that uses a Cursor name, telling the agent to read the adapter first.
  2. It points relative links to files outside the tree at GitHub.

The build fails when a skill uses a known Cursor term that has no row in the adapter. `--check` fails when `dist/` has drifted from what the generator would produce.

## Install

```sh
git clone https://github.com/khaeransori/pstack-hermes ~/pstack-hermes
cd ~/pstack-hermes
python3 generate.py                     # clones cursor/plugins into .upstream/ and builds dist/
ln -sfn ~/pstack-hermes/dist ~/.hermes/pstack
mkdir -p ~/.hermes/skills/software-development
ln -sfn ~/pstack-hermes/dist/router ~/.hermes/skills/software-development/pstack
```

This adds a single `pstack` skill to the Hermes index. The 61 upstream skills stay out of the index, so they cost no prompt tokens until one is used. The router skill tells the agent to read the adapter and then `~/.hermes/pstack/skills/<name>/SKILL.md`.

Use it by naming a skill, for example `pstack correct on this repo` or `poteto-mode: fix the scroll drift bug`.

For a profile, link into `~/.hermes/profiles/<name>/skills/` instead.

## Update

```sh
python3 generate.py --sync    # move UPSTREAM_PIN to cursor/plugins main, rebuild, run the checks
python3 generate.py --check   # verify dist/ matches the pin and every Cursor term has an adapter row
```

The term check covers only the Cursor terms listed in `TERMS` in `generate.py`. If a new upstream term shows up in a run, add it to `TERMS`, add a row to the adapter, and rebuild.

## What you get

- 58 pstack skills (workflow, `poteto-mode` and its playbooks, and 23 `principle-*` skills), plus `agents/` and `docs/guide/`.
- `automations/benny/` as reference only. Upstream ships these as dormant Cursor Automation sources. In Hermes they would be a webhook or cron flow, which you build yourself.

## Limits in Hermes

- **One model.** `delegate_task` has no model setting per task, so multi-vendor panels (`arena`, `interrogate`) run with one model and a different framing for each seat. The agent says so when this happens.
- **No nesting.** A child cannot spawn its own children or call `clarify`. The chat that runs the skill owns all spawning.
- **Cursor-only features have no equivalent.** Bugbot, cloud agents, Canvas, and Automations are skipped with a one-line note. Where a close match exists, it is used instead: worktrees, `gh`, and cron after asking.
- **House rules take priority.** The agent still asks before sending anything outside the chat, creating cron jobs, or changing config, even when a playbook says "don't ask".
- `statechart` and `poteto-mode/scripts` need Node or Bun dependencies the first time they run.

## License

pstack content in `dist/` and `.upstream/`: MIT, © 2026 Lauren Tan (see upstream `LICENSE`). The adapter and generator in this repo: MIT, see `LICENSE`. This is an unofficial port and is not affiliated with Cursor or xAI.
