# pstack in Codex

pstack skills use Cursor names. In Codex, read this file once per session before you follow a pstack skill, then map each Cursor name in the skill with the tables below. `<pstack>` means the folder that holds `skills/`, `agents/`, and `docs/`. In this install it is `~/.codex/pstack`. If a Cursor field has no row, drop it and say so. Never pass a field or value the tool schema rejects. Tool names differ between Codex versions: when a row names two tools, use the one this session lists.

## Tools

| Cursor | Codex |
| --- | --- |
| `Task` | `spawn_agent`, one call per subagent, each with a unique `task_name` (lowercase, digits, underscores) and the brief in `message`. Pass `fork_turns: "none"` and put every path, constraint, and the pstack skill to read in `message`, so the child starts clean like a Cursor subagent. Use `fork_turns: "all"` only when the skill says the child needs this chat's history. |
| `Await` | `wait_agent` with a long `timeout_ms` (minutes). It reports which agents have updates; their final answers arrive as `FINAL_ANSWER` messages. Never busy-poll. |
| Spawn N subagents in one message | Issue the N `spawn_agent` calls back to back in one turn, then `wait_agent`. The session has a fixed number of concurrency slots, the parent included (the `<multi_agent_role>` note says how many). When N is larger, spawn in batches. |
| Stop a runaway subagent | `interrupt_agent`. `list_agents` shows what is still running. |
| `AskQuestion` | `request_user_input` when this turn lists it (Plan mode, at most 3 questions, 2 to 3 options each). Otherwise `request_user_input_async`, then end the turn and wait for the reply. If neither is listed (`codex exec`), ask in plain text and stop. Never use these tools for sandbox or command permission; those go through escalation. A skill's own approval step (accept a lint rule, an encoding, a role table) is a normal question and uses them. When a question has more options than the tool allows, ask in plain text with a numbered list. |
| Open a todolist, or copy steps into the todolist tool | `update_plan` if the session offers it. Otherwise keep the list in your reply and update it at each phase. |
| Run another pstack skill (`/name` or "the **name** skill") | Read `<pstack>/skills/<name>/SKILL.md` and follow it. Only the `pstack` router skill is in the Codex skill list. When you tell the user to type it, write `$pstack <name>`. |
| `Read` | Read the file with a shell command (`sed -n`, `cat`) through `exec_command`. |
| `Grep`, `Glob` | `rg` and `rg --files` through `exec_command`. |
| `Shell`, a terminal command | `exec_command`. Long runs: when it returns a session ID, poll with `write_stdin` and empty `chars`. Use `wait` only for a yielded `exec` cell. |
| `StrReplace`, edit a file | `apply_patch`. |
| `WebFetch`, `WebSearch` | The web search tool if this session offers it. Otherwise `curl` through `exec_command` when the sandbox allows network. If neither works, say so and continue without it. |

## Subagent fields

| Cursor | Codex |
| --- | --- |
| Nesting | The default `agents.max_depth` is 1: children cannot spawn children. The chat that runs the pstack skill owns every spawn. When a skill tells a delegate to spawn its own subagents, prefer returning so the parent spawns them. If the delegate does the work itself, it says in its report that the pass was not independent, so the parent can rerun it as a real child. |
| Reasoning level for a subagent | `reasoning_effort` on `spawn_agent`, with `fork_turns: "none"`. Full-history forks cannot override it. |
| "Inspect its report and diff", "revert and rerun" | A child returns a final answer, not a diff. All agents share one working directory. Before spawning a writer, record `git status --porcelain` and `git stash create` (prints a commit without touching the tree, empty when clean). Afterwards run `git diff` yourself and review that. To revert only the child's work, restore the files it touched from the stash commit (`git restore --source=<sha> -- <files>`), or from `HEAD` when there was none. Never `git checkout -- .` or `git reset --hard` over the user's edits. Safer still: give the writer its own worktree. |
| Approval modes: interactive, unattended, eval, caller pre-approval | Subagents inherit the parent's sandbox and approval settings; a brief cannot widen them. Interactive: the parent asks the user. A child never asks; it returns the decision as an open item. Unattended (`codex exec`, scheduled task, "don't ask me"): take the skill's unattended branch. Eval: only when the user or the brief says it is an eval run. An action that needs a fresh approval fails there; report it as an open item. Pre-approval reaches a child only as written text in its `message`. |
| Report-only or read-only run of a skill that edits | Do not edit the user's checkout. List each edit or deletion the skill would make as a proposed change (file, line, before, after), then stop. Proving a check against a past commit is allowed in a throwaway copy outside the repo (`git worktree add` under `$TMPDIR`, or `git archive <sha> | tar -x -C <tmp>`); remove it afterwards. |
| A skill "fails" (`fail /<name>`) | Say so in the reply's first line, `Failed <name>: <reason>`, with the open items. A child puts that line first in its final answer. |
| `subagent_type: generalPurpose` | A plain `spawn_agent` call. |
| A Project worker, agent mode ("readonly strips MCP") | A Project worker is a `spawn_agent` call in its own worktree (see `environment: "cloud"`). Codex children always keep the session's MCP servers, so agent mode needs nothing extra. |
| "Run the same command locally and in CI", a human's approval on an exception | Run it locally. If the repo has CI, add the command there; if it has none, say so and name the command a CI job should run. The human approval is the user's yes in this chat, recorded in the exception comment. |
| `subagent_type: "poteto-agent"` | A `spawn_agent` call whose `message` starts with "Read `<pstack>/agents/poteto-agent.md`, then `<pstack>/skills/poteto-mode/SKILL.md` in full, before any work." Give the absolute paths. |
| `subagent_type: "comment-sicko"` | A `spawn_agent` call whose `message` starts with "Read `<pstack>/agents/comment-sicko.md` and follow it." |
| The `model:` line in an agent file | It holds a Cursor slug. Map it with the Models table and pass the result as `model` and `reasoning_effort`, so the slug never reaches the API. |
| `readonly: true` | A normal call whose `message` says "Read-only: do not edit, create, or delete files, and do not commit." Codex cannot give one child a read-only sandbox, so after it returns, run `git status --porcelain` and revert anything it touched. |
| `readonly: false` | A normal call. It inherits the session's MCP servers. |
| `environment: "cloud"` | A git worktree on this machine: `git worktree add <path> -b <branch> <base>`, and tell the child to work only in `<path>`. Agents share one working directory, so every parallel writer needs its own worktree. Remove it when the worker is done. If the sandbox blocks writing to `.git`, request escalation for that command; if that is refused, use a plain copy (`git archive <base> \| tar -x -C <path>`) and compare with `diff -ru`. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first, or create its worktree from `<b>`. |
| `run_in_background: true` | Omit. Spawned agents already run while the parent keeps working. |
| `is_background` | Omit, as above. |
| `resume` | `followup_task` (or `send_input` / `resume_agent` in older Codex) when the agent still exists. Otherwise spawn a fresh agent and paste the earlier result into its `message`. |
| `file_attachments` | List the paths in `message`. |

## Models

Codex runs OpenAI models only. Per-spawn `model` and `reasoning_effort` work, so roles keep their effort, and a panel can mix OpenAI models, but not vendors.

| Cursor | Codex |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]` | Omit `model` (inherit the session model) and pass the slug's effort as `reasoning_effort`. Drop `-fast`. |
| `gpt-*` | Pass it as `model` only if `spawn_agent` lists it. Otherwise omit `model`. Keep the effort. |
| `grok-*`, `gemini-*`, any other non-OpenAI slug | Omit `model` and say so. Keep the slug's effort as `reasoning_effort`, as for `claude-*`. |
| "If the Task tool rejects a slug", fall back to the closest slug of the same family | When `spawn_agent` errors on a `model`, drop `model`, keep `reasoning_effort`, and do not retry that model this run. When every slug collapses to the session model, the fallback chain has nothing to do; say once that roles differ only by effort. |
| `auto` or `inherit-parent` | Omit `model` and `reasoning_effort`. |
| A panel (arena runners, interrogate reviewers, cross-judge pool) of N different vendors | Still spawn N children, one per seat. Where `spawn_agent` lists more than one model, give the seats different models; also give each seat a distinct framing in `message`. Tell the user the panel was single-vendor. A cross-vendor judge rule cannot be met. The judge is a fresh read-only `spawn_agent` on a different OpenAI model than the runners when one is listed; otherwise a fresh read-only `spawn_agent` on the session model, with no runner's history (`fork_turns: "none"`). It is never the parent, so the judge phase and its agreement check stay separate. Say the judge shared a vendor with the runners. |
| The `pstack-models.mdc` rule, `~/.cursor/rules/pstack-models.mdc` | `~/.codex/pstack-models.md`. Codex does not load it on its own; read it at the start of a pstack run if it exists. If the file or the role's line is missing, map the skill's default slug with this table. |
| A role value `<model> <effort>`, such as `gpt-6.2-sol high` | `model` and `reasoning_effort`, with `fork_turns: "none"`. |
| A role value `inherit-parent <effort>`, such as `inherit-parent xhigh` | Omit `model`, pass `reasoning_effort`. Bare `inherit-parent` omits both. |

## setup-pstack

Follow its steps with these changes:

- Detect. The detected models are the models that the `spawn_agent` description lists, each with its reasoning efforts. If it lists none, run `codex debug models` through `exec_command`; if that fails too, the only model is the session model. Write a real model as `<model> <effort>`, such as `gpt-6.2-sol xhigh`. The effort is the last token, so the budget step works as written.
- Defaults. Map each default slug with the Models table: `claude-<family>-<version>-<effort>` and `gemini-<...>-<effort>` both become `inherit-parent <effort>`, for example `claude-opus-5-5-xhigh-fast` is `inherit-parent xhigh`. The budget step then moves the effort token as written.
- Ask. Use the `AskQuestion` row. Step 3c usually has more choices than `request_user_input` allows, so ask it in plain text with a numbered list.
- Write. Write `~/.codex/pstack-models.md` with no frontmatter: the comment lines, the `# defaults: 3` line, the `# budget` line, and one line per role from step 5, exactly as the skill gives them (keep Cursor words in comments; this adapter maps them when read). Overwrite the whole file. The file is outside the workspace, so request escalation for the write. Never put the role lines in `AGENTS.md`.
- Report. Where the skill says the rule applies to new sessions, say instead that pstack reads the file at the start of each run.
- Resolve. "Wherever pstack is installed" means `<pstack>`, `~/.agents/skills/`, and `<repo>/.agents/skills/`.
- Never change `~/.codex/config.toml` without asking the user.

## Frontmatter

| Cursor | Codex |
| --- | --- |
| `disable-model-invocation: true` | Already true here: pstack skills are outside the Codex skill roots, so they run only when the user names one or a pstack skill routes to it. Drop the field silently. |
| `icon`, `alwaysApply`, `globs` | Drop silently. |

## Paths

| Cursor | Codex |
| --- | --- |
| `.cursor/skills/`, a project-local skill | `<repo>/.agents/skills/<name>/`. Codex scans `.agents/skills` from the working directory up to the repo root. |
| `~/.cursor/skills/`, a user skill | `~/.agents/skills/<name>/`. Codex picks up changes; restart it if one does not appear. |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `<pstack>`. Its version is in `<pstack>/plugin.json`. |
| `.cursor/automations/`, `.cursor/benny/`, `.cursor/settings.json` (Benny) | No Codex equivalent to install into. Benny is reference only here: read it, and if the user asks to wire it up, design a scheduled task in the ChatGPT desktop app or a `codex exec` job that reads its skills from `<pstack>/automations/benny/`, with config under `<repo>/.codex/benny/`. Ask before creating it, and before any Slack post, ticket, or PR it would make. |
| `.cursor/rules/*.mdc`, always-applied rules, "the agent instruction file" | The repo's `AGENTS.md` (nested `AGENTS.md` files apply to their folder). `~/.codex/AGENTS.md` for rules that are personal. Codex never reads `.mdc` files. When the repo has none and a skill writes a rule table, create `AGENTS.md` at the repo root; `README.md` does not count. |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `<pstack>/<path>` when that file exists. Read the local copy and never fetch it. Give the user the URL when they need a link. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | `~/.codex/sessions/<year>/<month>/<day>/rollout-*.jsonl` (`$CODEX_HOME` if set). Each file has the session's working directory in its first lines; read only sessions from this repo. Subagent threads are separate rollout files. |
| `/loop` | Keep iterating inside this turn while the check still moves. For a hunt longer than one turn, ask the user to schedule a follow-up (a scheduled task in the desktop app, or rerun `codex exec` with the plan file). |

## Cursor-only features

Codex has no Bugbot, Cursor cloud agents, Cursor Automations, or built-in PR tool. When a step needs one and the tables give no equivalent, put one line in your reply, `Skipped in Codex: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line.

| Cursor | Codex |
| --- | --- |
| Cursor Automations: routines, `update_state` routine calls, `api2.cursor.sh/automations` webhooks, routine wakes, and `SendToUser` secret requests | Skip with the line. A recurring routine can become a scheduled task in the ChatGPT desktop app if the user sets one up. Secret requests never map. |
| Bugbot | Bugbot comments on a GitHub PR are ordinary review threads, so triage them with `gh`. Skip a step that starts, waits for, or configures Bugbot when the PR has no Bugbot check or comment. A second review pass can use `codex review`. |
| Cursor cloud agents | `environment: "cloud"` maps to a worktree, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | `gh pr create`, `gh pr view`, `gh pr checks`. That is not a skip, so write no line. |
| Canvas, Cursor UI panes | Write the content as a markdown file and give its path. Skip interactive canvas features with the line. |

## Sandbox and approvals win over a pstack step

Codex's sandbox and approval settings are the user's choice. When a pstack step needs more access than the sandbox gives (network, writing outside the repo, pushing), request escalation the normal way or report it as an open item. Never work around the sandbox. Sending anything outside the session (messages, PR comments on someone else's repo, publishing) needs the user's yes, even if a playbook says "don't ask".
