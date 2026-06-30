---
mode: ai
---

# Greenfield setup — adopt pkit in a brand-new project

The S1 demo (takeaway #1: *"trivial to start"*). From an empty repo to a working,
conventioned issue workflow in three commands — then the first conversation with the
`project-manager` agent, which does the issue work on your own GitHub identity.

This storyboard drives a **throwaway greenfield directory** (the `cwd` in `record.yaml`).
Reset it to an empty git repo (linked to a disposable GitHub repo) before each take.

## Step 1 — an empty project

```boot
narration: |
  Brand-new project — nothing here yet.
  Let's adopt pkit and have a real issue workflow in a couple of minutes.
command: ls -la
```

## Step 2 — bind the panes

```panes
narrate: 0
shell: 1
chat: 2
```

## Step 3 — get pkit (one command)

First, install pkit itself — one command, nothing project-specific.

```narrate
Step 1: install pkit. One command — and notice you never think about Python or uv.
```

```shell
uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git
```

```ready
pattern: Installed
timeout: 180
```

## Step 4 — set up the repo

`pkit init` lays the methodology into the repo itself — all in-tree, version-locked to the binary (per ADR-033, the content ships in the wheel; no checkout needed).

```narrate
Step 2: pkit init. It sets up everything the project needs, right in the repo.
```

```shell
pkit init
```

```ready
pattern: Next steps
timeout: 60
```

## Step 5 — turn on project-management + bootstrap the tracker

Install the project-management capability, then bootstrap the GitHub tracker — labels, board, the lifecycle states.

```narrate
Step 3: turn on project-management and bootstrap GitHub — labels, board, lifecycle. One go.
```

```shell
pkit capabilities install project-management
```

```ready
pattern: installed
timeout: 60
```

```shell
pkit project-management bootstrap
```

```ready
pattern: bootstrap
timeout: 90
```

## Step 6 — meet the project-manager agent

From here you never touch issues by hand — you talk to the `project-manager` agent, and it acts on *your* GitHub identity.

```narrate
That's the whole setup. From now on you just talk to the project-manager agent.
```

```shell
claude --agent project-manager
```

```ready
pattern: project-manager
timeout: 30
```

## Step 7 — file work by just asking

Describe the work in plain words; the agent files it with the right classification and puts it on the board — no manual labels, no missed steps.

```chat
File a Task to add CI status badges to the README, classify it, and put it on the board. When the issue exists, say BOARD-READY.
```

```ready
pattern: BOARD-READY
timeout: 180
```

## Step 8 — that's it

```narrate
Empty repo to a conventioned, agent-driven workflow — in minutes. That's takeaway #1.
```
