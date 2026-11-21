# pstack in Hermes

pstack skills use Cursor names. In Hermes, read this file once per session before you follow a pstack skill, then map each Cursor name in the skill with the tables below. This copy ships inside a skill installed from the Hermes Skills Hub (`khaeransori/pstack-hermes`, pstack 0.15.46, upstream `d42aff08aa58`), so there is no `<pstack>` tree. Map its paths: `<pstack>/skills/<name>/` is the installed `<name>` skill folder (`skill_view(name)` shows its path); `<pstack>/agents/<file>` is `references/agents/<file>` in the skill you are running; `<pstack>/plugin.json` and `<pstack>/docs/` are on GitHub at https://github.com/cursor/plugins/tree/d42aff08aa58965d2735c4ead61a9af82b89d0d0/pstack. Give absolute paths to children. If a Cursor field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

## Tools

| Cursor | Hermes |
| --- | --- |
| `Task` | `delegate_task`. One entry in `tasks` per subagent; several entries run in parallel. Children know nothing of this chat, so put every path, constraint, and the pstack skill to read in `context`. |
| `AskQuestion` | `clarify`. One call can hold up to 5 independent questions. When `clarify` is not offered (cron, one-shot runs), ask in plain text and stop. |
| Open a todolist, or copy steps into the todolist tool | `todo_list` (load it with `tool_describe` first). Otherwise keep the list in your reply and update it at each phase. |
| Run another pstack skill (`/name` or "the **name** skill") | `skill_view(name)` and follow it. If it is not installed, ask the user to run `hermes skills install khaeransori/pstack-hermes/skills/<name> --category pstack` (one-time). When you tell the user to type it, write `pstack <name>`. |
| `Read` | `read_file` |
| `Grep`, `Glob` | `search_files` (`target: "content"` for Grep, `target: "files"` for Glob). |
| `Shell`, a terminal command | `terminal`. Long runs: `background: true` with `notify: true`. |
| `StrReplace`, edit a file | `patch`. New or rewritten files: `write_file` (read the file first if it exists). |
| `WebFetch`, `WebSearch` | `web_extract`, `web_search`. Pages that need JS or login: `browser_exec`. |
| `Await` | Background `delegate_task` results come back as a new message between turns. End the turn with a one-line status. Never poll. |

## Subagent fields

| Cursor | Hermes |
| --- | --- |
| Nesting | Children cannot spawn children (`delegation.max_spawn_depth: 1`) and cannot call `clarify`. The chat that runs the pstack skill owns every spawn. When a skill tells a delegate to spawn its own subagents, prefer returning so the parent spawns them. If the delegate does the work itself, it says in its report that the pass was not independent (no fresh perspective), so the parent can rerun it as a real child. |
| Reasoning level for a subagent | Routed: pick the route whose name ends in that level (see Models). Single-model: `delegate_task` has no effort field, so put the level in `context` ("work at high effort: check every claim"). The run-wide default is `delegation.reasoning_effort` in config; never change it without asking. |
| "Inspect its report and diff" | `delegate_task` returns a summary, not a diff. The parent runs `git diff` / `git status --porcelain` with `terminal` in the child's checkout or worktree, and reviews that, not the summary. |
| Approval modes: interactive, unattended, eval, caller pre-approval | Interactive: the parent asks with `clarify`. A child never asks; it returns the decision as an open item. Unattended (cron, background, "don't ask me"): take the skill's unattended branch, and still stop for anything in the house rules below. Pre-approval reaches a child only as written text in its `context`. |
| Report-only or read-only run of a skill that edits | Do not edit. List each edit or deletion the skill would make as a proposed change (file, line, before, after), then stop. |
| A skill "fails" (`fail /<name>`) | Say so in the reply's first line, `Failed <name>: <reason>`, with the open items. A child puts that line first in its summary. Nothing else is needed. |
| `subagent_type: generalPurpose` | A plain `delegate_task` entry. |
| A Project worker, agent mode ("readonly strips MCP") | A Project worker is a `delegate_task` entry in its own worktree (see `environment: "cloud"`). Hermes children keep the session's tools, so agent mode needs nothing extra. |
| "Run the same command locally and in CI", a human's approval on an exception | Run it locally. If the repo has CI, add the command there; if it has none, say so and name the command a CI job should run. The human approval is the user's yes in this chat, recorded in the exception comment. |
| `subagent_type: "poteto-agent"` | A `delegate_task` entry whose `context` starts with the kickoff line poteto-mode requires (`Read <path>/worker.md before anything else.`), then "Read `<pstack>/agents/poteto-agent.md`, then `<pstack>/skills/poteto-mode/SKILL.md` in full, before any work." Give the absolute paths. Its model comes from the role line, else the agent file's `model:`, mapped with Models. An `inherit-parent` role still gets these read lines; only `option` is dropped. |
| `subagent_type: "comment-sicko"` | A `delegate_task` entry whose `context` starts with "Read `<pstack>/agents/comment-sicko.md` and follow it." |
| The `model:` line in an agent file, or any model slug passed to `Task` | Map it to a route with the Models section and pass it as the entry's `option`. Single-model: omit it, and say once per run that children run on one model. |
| `readonly: true` | A normal entry whose `context` says "Read-only: do not edit, create, or delete files, and do not commit." After it returns, run `git status --porcelain` and revert anything it touched. |
| `readonly: false` | A normal entry. It inherits the session's MCP servers. |
| `environment: "cloud"` | A git worktree on this machine: `git worktree add <path> -b <branch> <base>`, and name the path in `context`. Remove it when the worker is done. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first, or create its worktree from `<b>`. |
| `run_in_background: true` | Omit. In the gateway, `delegate_task` already runs in the background and returns results as a new message. |
| `is_background` | Omit, as above. |
| `resume` | If the child is still running, `delegate_task` with `action: "steer"`. If it finished, spawn a fresh entry and paste the earlier result into its `context`. |
| `file_attachments` | List the paths in `context`. Images go in the entry's `images` field. |

## Models

Hermes has two modes. Check which one this session has before the first spawn: look at the `delegate_task` schema's task items.

- **Routed.** The items have an `option` property (the `advanced-delegation` plugin, `delegation.backend: model_map`). Its enum is the list of routes, and its description gives `name: description` for each. Each entry can run on a different model.
- **Single-model.** There is no `option` property. Every child runs on `delegation.model`, else the session model, so pstack's per-role and multi-vendor choices collapse.

A `profile` property instead of `option` means profile routes. Treat the session as single-model for pstack, and say so.

### Route names

pstack expects routes named `<family>-<effort>`, all lowercase: the family is a model family (`opus`, `sonnet`, `haiku`, `fable`, `sol`, `astra`, `terra`, `luna`, `gpt`, `gemini`, `grok`), and the effort is `xhigh`, `high`, `medium`, or `low`. Examples: `opus-xhigh`, `opus-high`, `fable-high`, `sol-xhigh`, `gemini-xhigh`. The effort is the last token, so setup-pstack's budget step works as written. The family names the vendor: `opus`, `sonnet`, `haiku`, and `fable` are Anthropic; `sol`, `astra`, `terra`, `luna`, and `gpt` are OpenAI; `gemini` is Google; `grok` is xAI. An OpenAI family is the model line (the tier in `gpt-<version>-<tier>`), as `opus` is for Anthropic; `gpt` is only for OpenAI models without a tier. A route whose name does not follow this shape is still usable when the user names it in a role line, but never pick it from a slug.

### Mapping a slug to a route

Do this for every slug: an agent file's `model:`, a role line, a skill default, a panel entry, a judge-pool entry.

1. Family and effort. `claude-<family>-<version>-<effort>[-fast]` is family `<family>` (`opus`, `fable`, ...). `gpt-<version>-<tier>-<effort>` with tier `sol`, `astra`, `terra`, or `luna` (such as `gpt-6.2-sol-xhigh`) is family `<tier>`; any other `gpt-*` slug (such as `gpt-5.4-mini`) is family `gpt`. `gemini-*`, `grok-*` are families `gemini`, `grok`. The effort is the last token, or the one before a trailing `fast`. Drop the version and `-fast`; the route's own `service_tier` decides speed, so never set one.
2. Exact route. If `<family>-<effort>` is in the enum, use it.
3. Nearest route of the same family. Otherwise take the same family's route closest in effort, preferring the lower one on a tie, and say which slug moved to which route. This is how a budget or a "lower it for routine work" step lands on a real route.
4. No route for the family. The slug is unrouted; see the rows below. Never fill the gap with another family.

A route name written directly (in a role line, such as `opus-high` or a user's `deep`) is used as is when it is in the enum; otherwise apply steps 1 to 4 to it.

| Cursor | Hermes, routed | Hermes, single-model |
| --- | --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, such as `claude-opus-5-5-xhigh-fast`; `gpt-*`, `gemini-*`, `grok-*` slugs | `option` set to the route from the steps above, such as `opus-xhigh`. | Omit. Put the effort in `context`. |
| An unrouted slug outside a panel | Omit `option`, put the effort in `context` ("work at xhigh effort"), and say where it ran: the `model_map` default route if one is set, else the session model. | Omit, as above. |
| `auto` or `inherit-parent` | Omit `option` and put the role's effort, if the budget names one, in `context`. It runs on the default route, else the session model. | Omit. |
| A panel (arena runners, interrogate reviewers) | One entry per seat, each on its route. An unrouted seat is dropped, as arena says for a rejected slug, while at least two seats remain; a seat kept with no route runs like an unrouted slug. Every two seats that share a model (same route, or no route next to each other or next to a route on the session model) get distinct framings in `context` ("assume the design is wrong", "optimize for the user", "optimize for the reader"). Tell the user each seat's route, which seats were dropped, and whether the panel was single-vendor. | Still spawn N children, one per seat, sharing one model, each with a distinct framing in `context`. Tell the user the panel was single-vendor. |
| The cross-vendor judge (arena Phase C, a cross-judge pool) | Map the pool entries in order. The judge is the first one whose route's vendor differs from the parent's (the session model's vendor; `opus`, `sonnet`, `haiku`, `fable` are all Anthropic, and `sol`, `astra`, `terra`, `luna`, `gpt` are all OpenAI). If the vendor of a route is unclear (a name outside the convention), check its provider with `hermes delegation config --show`. If no entry qualifies, skip the judge and say so, as arena does. Never let the parent stand in as judge. | The rule cannot be met: skip the judge and say so. The parent still scores candidates in Phase D. |
| The `pstack-models.mdc` rule, `~/.cursor/rules/pstack-models.mdc` | `~/.hermes/pstack-models.md`. Read it at the start of a pstack run if it exists. A role line beats a skill default and an agent file's `model:`. | The same file. Only its `# budget` line has an effect: pass the matching level as guidance in each child's `context`. |
| A role value `<model> <effort>` | The route for that model and effort, by the steps above. | Keep only the effort, as guidance in `context`. |

### Checking what ran

After a routed batch returns, read each result's `route` (provider and model the child ran on).

- If it differs from the route you asked for, or `fallback_activated` is true, say so in your report.
- If that happened to the judge and its provider now matches the parent's vendor, the vendor rule broke: discard its verdict, treat Phase C as skipped, and say so.
- A refused entry (`route.refused: true`) is a routing error, not a model failure. For a judge, move to the next pool entry. For anything else, re-map the slug once with the steps above, or omit `option`, and retry that entry once.
- An entry that failed before doing any work with a connection or access error (HTTP 401, 403 or 404, a timeout, DNS or TLS failure, "provider unavailable") lost its route, for example because a VPN-only endpoint dropped mid-session. Treat that route as missing from the enum for the rest of the run: a panel seat on it is unrouted (drop it while at least two seats remain), a judge moves to the next pool entry, and any other entry is re-mapped once with the steps above. Do not retry the same route. Name the route and the error in your report.

Panels larger than `delegation.max_concurrent_children` run in batches.

## setup-pstack

Follow its steps with these changes:

- Detect. Routed: the detected models are the routes in `delegate_task`'s `option` enum, with their descriptions. `hermes delegation config --show` also lists each route's provider and model; if that command is not available, use the enum alone and say the provider check did not run. Single-model: the only models are the session model and `delegation.model` (`hermes config get delegation.model`; empty means the session model). Say that per-role models need the `advanced-delegation` plugin, and keep going.
- Defaults. Routed: map each default slug in step 5 to a route with the Models section. A default whose family has no route becomes `inherit-parent`, and you tell the user which. Single-model: every value is `inherit-parent`.
- Budget. Ask for it with `clarify`. Routed: move each value's effort as the skill says for slugs (each panel entry moves its own effort; poteto-mode's "panel seats keep their listed level" is about runtime, not setup), then map it with the steps in Models, so it lands on the nearest route of its family. A value with no route for its family becomes `inherit-parent`, and you say which. Route names outside the convention (no effort token) do not move.
- Confirm. Show each role with its route, and the provider and model behind it from `hermes delegation config --show`.
- Write. Write `~/.hermes/pstack-models.md` with the comment lines (copied as the skill gives them; this adapter maps their Cursor words when read), the `# defaults: 3` line, the `# budget` line, and one line per role from step 5, each value a route name, or `inherit-parent`. No frontmatter. Validation: every route name must be in the enum; the "xhigh or below" check applies only to names that carry an effort. Step 2's migration rules match slugs only, so they never touch a file of route names. Overwrite the whole file. Never put these lines in a project's `AGENTS.md`.
- Never install the plugin, add or change routes, or change `delegation.*` or any other Hermes config without asking the user. If the user wants routes, show them the `model_map` example in pstack-hermes's README and let them apply it.

## Frontmatter

| Cursor | Hermes |
| --- | --- |
| `disable-model-invocation: true` | Already true here: pstack skills are outside the Hermes skill index, so they run only when the user names one or a pstack skill routes to it. Drop the field silently. |
| `icon`, `alwaysApply`, `globs` | Drop silently. |

## Paths

| Cursor | Hermes |
| --- | --- |
| `.cursor/skills/`, a project-local skill | `<repo>/.hermes/skills/`. Hermes loads it only when the repo root is in `skills.trusted_project_dirs`. Tell the user, and never add it yourself. |
| `~/.cursor/skills/`, a user skill | `~/.hermes/skills/<category>/<name>/` through `skill_manage`. |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `<pstack>`. Its version is in `<pstack>/plugin.json`. |
| `.cursor/automations/`, `.cursor/benny/`, `.cursor/settings.json` (Benny) | No Hermes equivalent to install into. Benny is reference only here: read it, and if the user asks to wire it up, design a Hermes webhook route or cron job that reads its skills from `<pstack>/automations/benny/`, with config under `<repo>/.hermes/benny/`. Ask before creating it, and before any Slack post, ticket, or PR it would make. |
| `.cursor/rules/*.mdc`, always-applied rules | The repo's `AGENTS.md`, or `.hermes.md` when the rule is Hermes-only. Hermes never reads `.mdc` files. |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `<pstack>/<path>` when that file exists. Read the local copy and never fetch it. Give the user the URL when they need a link. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | `chat_history_lookup` for past sessions. Raw files are `~/.hermes/sessions/*.jsonl` and `~/.hermes/state.db`. Subagent transcripts are the paths `delegate_task` returned. |
| `/loop` | Keep iterating inside this turn while the check still moves. For a hunt longer than one turn, schedule a wake with `cronjob_manage` that re-reads the plan file and continues. Ask before creating a cron job. |

## Cursor-only features

Hermes has no Bugbot, Cursor cloud agents, Cursor Automations, or built-in PR tool. When a step needs one and the tables give no equivalent, put one line in your reply, `Skipped in Hermes: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line.

| Cursor | Hermes |
| --- | --- |
| Cursor Automations: routines, `update_state` routine calls, `api2.cursor.sh/automations` webhooks, routine wakes, and `SendToUser` secret requests | Routines and wakes map to `cronjob_manage` or a Hermes webhook route, after asking the user. Secret requests never map: skip with the line. |
| Bugbot | Bugbot comments on a GitHub PR are ordinary review threads, so triage them with `gh`. Skip a step that starts, waits for, or configures Bugbot when the PR has no Bugbot check or comment. |
| Cursor cloud agents | `environment: "cloud"` maps to a worktree, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | `gh pr create`, `gh pr view`, `gh pr checks`. That is not a skip, so write no line. |
| Canvas, Cursor UI panes | Write the content as a markdown file and send its path. Skip interactive canvas features with the line. |

## Hermes house rules that win over a pstack step

- Sending anything outside this chat (email, messages, PR comments on someone else's repo, publishing) needs the user's yes first, even if a playbook says "don't ask".
- Never type a password, token, or card number. Use the vault tools.
- Git pushes to a remote need the write token the user set up, and a yes for anything outside the user's own repos.
