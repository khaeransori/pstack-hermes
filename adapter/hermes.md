# pstack in Hermes

pstack skills use Cursor names. In Hermes, read this file once per session before you follow a pstack skill, then map each Cursor name in the skill with the tables below. `<pstack>` means the folder that holds `skills/`, `agents/`, and `docs/`. In this install it is `~/.hermes/pstack`. If a Cursor field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

## Tools

| Cursor | Hermes |
| --- | --- |
| `Task` | `delegate_task`. One entry in `tasks` per subagent; several entries run in parallel. Children know nothing of this chat, so put every path, constraint, and the pstack skill to read in `context`. |
| `AskQuestion` | `clarify`. One call can hold up to 5 independent questions. When `clarify` is not offered (cron, one-shot runs), ask in plain text and stop. |
| Open a todolist, or copy steps into the todolist tool | `todo_list` (load it with `tool_describe` first). Otherwise keep the list in your reply and update it at each phase. |
| Run another pstack skill (`/name` or "the **name** skill") | `read_file` `<pstack>/skills/<name>/SKILL.md` and follow it. These skills are not in the Hermes skill index, so `skill_view` cannot find them. When you tell the user to type it, write `pstack <name>`. |
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
| Reasoning level for a subagent | `delegate_task` has no effort field. Put the level in `context` ("work at high effort: check every claim"). The run-wide default is `delegation.reasoning_effort` in config; never change it without asking. |
| "Inspect its report and diff" | `delegate_task` returns a summary, not a diff. The parent runs `git diff` / `git status --porcelain` with `terminal` in the child's checkout or worktree, and reviews that, not the summary. |
| Approval modes: interactive, unattended, eval, caller pre-approval | Interactive: the parent asks with `clarify`. A child never asks; it returns the decision as an open item. Unattended (cron, background, "don't ask me"): take the skill's unattended branch, and still stop for anything in the house rules below. Pre-approval reaches a child only as written text in its `context`. |
| Report-only or read-only run of a skill that edits | Do not edit. List each edit or deletion the skill would make as a proposed change (file, line, before, after), then stop. |
| A skill "fails" (`fail /<name>`) | Say so in the reply's first line, `Failed <name>: <reason>`, with the open items. A child puts that line first in its summary. Nothing else is needed. |
| `subagent_type: generalPurpose` | A plain `delegate_task` entry. |
| A Project worker, agent mode ("readonly strips MCP") | A Project worker is a `delegate_task` entry in its own worktree (see `environment: "cloud"`). Hermes children keep the session's tools, so agent mode needs nothing extra. |
| "Run the same command locally and in CI", a human's approval on an exception | Run it locally. If the repo has CI, add the command there; if it has none, say so and name the command a CI job should run. The human approval is the user's yes in this chat, recorded in the exception comment. |
| `subagent_type: "poteto-agent"` | A `delegate_task` entry whose `context` starts with "Read `<pstack>/agents/poteto-agent.md`, then `<pstack>/skills/poteto-mode/SKILL.md` in full, before any work." Give the absolute paths. |
| `subagent_type: "comment-sicko"` | A `delegate_task` entry whose `context` starts with "Read `<pstack>/agents/comment-sicko.md` and follow it." |
| The `model:` line in an agent file, or any model slug passed to `Task` | Omit it. `delegate_task` has no per-task model; children run on `delegation.model` from config, else the session model. Say so once per run. |
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

Hermes runs every child on one model, so pstack's per-role and multi-vendor choices collapse.

| Cursor | Hermes |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, `gpt-*`, `grok-*`, `gemini-*`, any other slug | Omit. The child runs on the configured delegation model. |
| `auto` or `inherit-parent` | Omit. |
| A panel (arena runners, interrogate reviewers, cross-judge pool) of N different vendors | Still spawn N children, one per seat, but they share one model. Give each seat a distinct framing in `context` (for example "assume the design is wrong", "optimize for the user", "optimize for the reader") and tell the user the panel was single-vendor. A cross-vendor judge rule cannot be met, so the parent judges and says so. |
| The `pstack-models.mdc` rule, `~/.cursor/rules/pstack-models.mdc` | `~/.hermes/pstack-models.md`. Read it at the start of a pstack run if it exists. Only its `# budget` line has an effect: pass the matching level as guidance in each child's `context` ("think at high effort"). |
| A role value `<model> <effort>` | Keep only the effort, as guidance in `context`. |

## setup-pstack

Follow its steps with these changes:

- Detect. The only models are the session model and `delegation.model` (`hermes config get delegation.model`; empty means the session model). Say that per-role models are not available in Hermes.
- Budget. Still ask for the budget with `clarify`.
- Write. Write `~/.hermes/pstack-models.md` with the comment lines, the `# defaults: 3` line, the `# budget` line, and the role lines from step 5, with every value set to `inherit-parent`. No frontmatter. Overwrite the whole file. Never put these lines in a project's `AGENTS.md`.
- Never change `delegation.model` or any other Hermes config without asking the user.

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
