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

This links `~/.hermes/pstack` (the full tree) and a single `pstack` skill in `~/.hermes/skills/software-development/`. The upstream skills stay out of the Hermes index, so they cost no prompt tokens until one is used. `HERMES_HOME` is respected; for a profile, link the router into `~/.hermes/profiles/<name>/skills/` instead.

Use it by naming a skill, for example `pstack correct on this repo` or `poteto-mode: fix the scroll drift bug`.

## Update

```sh
python3 generate.py --sync    # move UPSTREAM_PIN to cursor/plugins main, rebuild, run the checks
python3 generate.py --check   # verify dist/ and skills/ match the pin and every Cursor term has an adapter row
```

The symlinks point into `dist/`, so a rebuild updates the installed skills in place. The term check covers only the Cursor terms listed in `TERMS` in `generate.py`. If a new upstream term shows up in a run, add it to `TERMS`, add a row to the adapter, and rebuild.

The `upstream sync` workflow does this every day. It moves the pin only when something under `pstack/` changed upstream, then rebuilds, runs `--check`, commits, and tags. When the build fails, usually because of a new Cursor term, it opens an `upstream-sync` issue instead of committing.

## Releases

Tags are `v<pstack version>-hermes.<N>`, for example `v0.15.46-hermes.1`. A new pstack version starts again at `.1`. Our own adapter or generator changes, and a pin move that keeps the pstack version, bump `N`. `./next-tag.sh` prints the next tag. The exact upstream commit is in `UPSTREAM_PIN` and `dist/UPSTREAM.json`.

## Skills Hub

`skills/` is a second build of the same pin for the [Hermes Skills Hub](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills). It is committed so the hub can read it. Each skill is a self-contained folder with the adapter in `references/pstack-hermes-adapter.md` and the agent files it uses in `references/agents/`. Every folder passes the Skills Guard as `safe` for community installs.

```sh
hermes skills tap add khaeransori/pstack-hermes
hermes skills install khaeransori/pstack-hermes/skills/poteto-mode --category pstack
```

Install into one category (`pstack`) so links between sibling skills resolve. The hub build leaves out `make-bot-ui`, because its Tailscale setup needs `sudo`, the Benny automations, the guide, and statechart's test corpus. Use `install.sh` for the full tree. Unlike `install.sh`, each hub skill you install appears in the Hermes skill index.

## Per-role models (optional)

pstack picks a model per role: Opus at `xhigh` for features and judgment, a three-vendor panel for `arena` and `interrogate`, a cross-vendor judge. Plain Hermes runs every subagent on one model. With Nous's official [advanced-delegation](https://github.com/NousResearch/hermes-official-plugins/tree/main/advanced-delegation) plugin (Hermes 0.22.5 or newer), each `delegate_task` entry can pick a named model route, and the adapter maps pstack's model slugs onto those routes.

Name routes `<family>-<effort>`: the family is the model line, `opus`, `sonnet`, `haiku`, `fable` (Anthropic), `sol`, `astra`, `terra`, `luna` (OpenAI's `gpt-<version>-<tier>`; plain `gpt` for OpenAI models without a tier), `gemini`, or `grok`, and the effort is `xhigh`, `high`, `medium`, or `low`. The adapter maps `claude-opus-5-5-xhigh-fast` to `opus-xhigh`, `gpt-6.2-sol-xhigh` to `sol-xhigh`, `gemini-4-neon-xhigh` to `gemini-xhigh`, and so on. When the exact effort has no route (after a lower budget, say), it uses the same family's nearest route and says so; it never switches family. An example that covers pstack's defaults; add `opus-medium`, `fable-medium`, or `gemini-high` routes if you run a `medium` or `small` budget and want those levels exactly:

```yaml
# ~/.hermes/config.yaml
delegation:
  backend: model_map
  backends:
    model_map:
      options:
        - name: opus-xhigh
          description: "Hardest work: features, refactors, bug hunts, judgment."
          provider: anthropic
          model: claude-opus-5-5
          reasoning_effort: xhigh
        - name: opus-high
          description: "Strong and faster: swarm workers, panel seats, judging."
          provider: anthropic
          model: claude-opus-5-5
          reasoning_effort: high
        - name: fable-high
          description: "Second Anthropic family for panel seats."
          provider: anthropic
          model: claude-fable-5-2
          reasoning_effort: high
        - name: gemini-xhigh
          description: "Non-Anthropic panel seat and cross-vendor judge."
          provider: openrouter
          model: google/gemini-4-neon
          reasoning_effort: xhigh
```

Check each `model` id with one real call before saving, for example `hermes chat -Q --max-turns 1 --provider anthropic -m claude-fable-5-2 -q 'Reply with exactly: pong'`. Provider ids differ from pstack's slugs, and `hermes model` can list models your account cannot call (they return HTTP 404). Drop the `gemini-xhigh` route if you have no OpenRouter or Google key: panels then run Anthropic-only and the agent says so. Everything else needs no extra key. Set it up with `hermes plugins install advanced-delegation`, then `hermes delegation config` or the YAML above, then start a new session and run `pstack setup-pstack` to write the role lines.

Without the plugin everything still works on one model, as described below.

## Limits in Hermes

- **One model without the plugin.** Plain `delegate_task` has no model setting per task, so multi-vendor panels (`arena`, `interrogate`) run with one model and a different framing for each seat. The agent says so when this happens. See Per-role models above.
- **No nesting.** A child cannot spawn its own children or call `clarify`. The chat that runs the skill owns all spawning.
- **House rules take priority.** The agent still asks before sending anything outside the chat, creating cron jobs, or changing config, even when a playbook says "don't ask".
- Bugbot, cloud agents, Canvas, and Automations are skipped with a one-line note. Worktrees, `gh`, and cron (after asking) stand in where they fit.
- `automations/benny/` is reference only. `statechart` and `poteto-mode/scripts` need Node or Bun dependencies the first time they run.

The Codex version lives in [khaeransori/pstack-codex](https://github.com/khaeransori/pstack-codex).

## License

pstack content in `dist/` and `.upstream/`: MIT, © 2026 Lauren Tan (see upstream `LICENSE`). The adapter, generator, and installer in this repo: MIT, see `LICENSE`. This is an unofficial port and is not affiliated with Cursor or Nous Research.
