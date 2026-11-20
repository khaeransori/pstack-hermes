# pstack-hermes

[pstack](https://github.com/cursor/plugins/tree/main/pstack), the skill set by Lauren Tan ([@poteto](https://x.com/poteto)), packaged for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

The skills are not rewritten. This repo has three parts:

- `adapter/hermes.md` maps the Cursor names used in pstack (`Task`, `AskQuestion`, `readonly`, `environment: "cloud"`, `/loop`, Bugbot, transcript paths, and so on) to Hermes tools (`delegate_task`, `clarify`, `todo_list`, `cronjob_manage`, `gh`, worktrees). It follows the same approach as upstream's own [Claude Code adapter](https://github.com/cursor/plugins/blob/main/pstack/docs/harness/claude-code.md).
- `generate.py` builds `dist/` from a pinned upstream commit. It copies every skill, agent, guide page, and the Benny automation sources as they are, and makes two kinds of edit only:
  1. It adds one line after the H1 of each file that uses a Cursor name, telling the agent to read the adapter first.
  2. It points relative links to files outside the tree at GitHub.
- `install.sh` builds, checks, and links the tree into Hermes.

The build fails when a skill uses a known Cursor term that has no row in the adapter. `--check` fails when `dist/` has drifted from what the generator would produce.

## Install

```sh
git clone https://github.com/khaeransori/pstack-hermes ~/pstack-hermes
cd ~/pstack-hermes
./install.sh
```

This links `~/.hermes/pstack` (the full tree) and a single `pstack` skill in `~/.hermes/skills/software-development/`. The 61 upstream skills stay out of the Hermes index, so they cost no prompt tokens until one is used. `HERMES_HOME` is respected; for a profile, link the router into `~/.hermes/profiles/<name>/skills/` instead.

Use it by naming a skill, for example `pstack correct on this repo` or `poteto-mode: fix the scroll drift bug`.

## Update

```sh
python3 generate.py --sync    # move UPSTREAM_PIN to cursor/plugins main, rebuild, run the checks
python3 generate.py --check   # verify dist/ matches the pin and every Cursor term has an adapter row
```

The symlinks point into `dist/`, so a rebuild updates the installed skills in place. The term check covers only the Cursor terms listed in `TERMS` in `generate.py`. If a new upstream term shows up in a run, add it to `TERMS`, add a row to the adapter, and rebuild.

## Limits in Hermes

- **One model.** `delegate_task` has no model setting per task, so multi-vendor panels (`arena`, `interrogate`) run with one model and a different framing for each seat. The agent says so when this happens.
- **No nesting.** A child cannot spawn its own children or call `clarify`. The chat that runs the skill owns all spawning.
- **House rules take priority.** The agent still asks before sending anything outside the chat, creating cron jobs, or changing config, even when a playbook says "don't ask".
- Bugbot, cloud agents, Canvas, and Automations are skipped with a one-line note. Worktrees, `gh`, and cron (after asking) stand in where they fit.
- `automations/benny/` is reference only. `statechart` and `poteto-mode/scripts` need Node or Bun dependencies the first time they run.

The Codex version lives in [khaeransori/pstack-codex](https://github.com/khaeransori/pstack-codex).

## License

pstack content in `dist/` and `.upstream/`: MIT, © 2026 Lauren Tan (see upstream `LICENSE`). The adapter, generator, and installer in this repo: MIT, see `LICENSE`. This is an unofficial port and is not affiliated with Cursor or Nous Research.
