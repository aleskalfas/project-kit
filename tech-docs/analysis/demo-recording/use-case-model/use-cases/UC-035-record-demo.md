---
id: UC-035
title: Record a demo of my command line
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/demo-recording/package.yaml
        - .pkit/capabilities/demo-recording/scripts/record.sh
        - .pkit/capabilities/demo-recording/scripts/run-storyboard.sh
        - .pkit/capabilities/demo-recording/scripts/validate.sh
        - .pkit/capabilities/demo-recording/scripts/storyboards/*.py
        - .pkit/capabilities/demo-recording/scripts/plugins/recording/*.sh
        - .pkit/capabilities/demo-recording/scripts/plugins/recording/directives.py
        - .pkit/capabilities/demo-recording/skills/demo-recording/*.md
      record:
        - demo-recording:DEC-001
        - demo-recording:DEC-002
        - demo-recording:DEC-004#1
        - demo-recording:DEC-004#2
        - COR-004
        - COR-005
        - COR-013
        - COR-017
        - COR-020
        - COR-021
        - COR-031
        - COR-050#2
        - COR-050#13
        - COR-055#3
---

# UC-035 — Record a demo of my command line

**Goal:** Record a demo of my command line by running an executable storyboard, a document people read as it stands.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): writes the demo bundle, or runs the commands of steps 2 and 4, for the developer through the `demo-recording` skill. The skill has it run `pkit demo-recording validate` before every recording (the skill's `start` operation).

**Preconditions:** None.

**Assumptions:**

- The project has demo-recording installed, or registered in place where demo-recording is developed. Its commands then answer as `pkit demo-recording record`, `run` and `validate` ([COR-017](../../../../../.pkit/decisions/core/COR-017-capability-pattern.md), [COR-021](../../../../../.pkit/decisions/core/COR-021-capability-command-dispatch.md) and [COR-031](../../../../../.pkit/decisions/core/COR-031-capability-origin.md)).
- The AI agent of variant 1b can load the `demo-recording` skill, deployed with demo-recording. It is one skill with an operation for each task ([COR-005](../../../../../.pkit/decisions/core/COR-005-bundle-pattern.md), [COR-013](../../../../../.pkit/decisions/core/COR-013-agent-architecture.md) and [COR-020](../../../../../.pkit/decisions/core/COR-020-skill-folder-form.md)).
- Where the machine runs macOS, it has iTerm2, and the terminal app that runs the commands holds the Accessibility and Screen Recording permissions. Nothing in the system checks for iTerm2 or the permissions. [DEC-004](../../../../../.pkit/capabilities/demo-recording/decisions/DEC-004-platform-coupling-and-gate-placement.md) names the stack the permissions serve: iTerm2, System Events and `screencapture`.
- The commands an executable storyboard types are the developer's own, and run in the developer's shell as written. [DEC-001](../../../../../.pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md) makes the executable storyboards the project's content, never demo-recording's.

**Trigger:** The developer wants a recorded demo of a command line, such as a walk through a feature for colleagues to watch.

**Main path:**

1. The developer writes a demo bundle: its recording configuration, `record.yaml`, and an executable storyboard in its `storyboards/` folder.
2. The developer runs `pkit demo-recording validate <storyboard>`.
3. The system parses the executable storyboard, and checks the content of each directive. It prints each step with a line for each of its directives, and ends with `✓ <n> step(s) parsed.  No errors.`. It changes no file of the project (core:REQ-005), and runs on any platform ([DEC-004 point 2](../../../../../.pkit/capabilities/demo-recording/decisions/DEC-004-platform-coupling-and-gate-placement.md#2-a-single-platform-gate-sits-at-the-recording-plugin-boundary-layer-3-of-demo-recordingdec-002-three-layer-plugin-architecture-not-at-the-capability-or-format-entry)).
4. The developer runs `pkit demo-recording record <demo> --config <bundle>/record.yaml`. `<demo>` names the executable storyboard: a path, or a name the system looks for beside the configuration and in the demo bundle's `storyboards/` folder.
5. The system finds the executable storyboard and the recording configuration. Before it reads the configuration's fields, it checks that it runs on macOS (DEC-004 point 2).
6. The system reads the working directory and the bounds of two windows from the recording configuration, and parses the executable storyboard again. Only then does it create the folder for videos, `recordings/` unless the configuration names another, and start the run's log in that folder's `.logs/`.
7. The system opens two iTerm2 windows at those bounds, each in the working directory. It records the first, and drives the recording from the second, outside the recorded area.
8. The system starts the screen capture of the first window, and carries out the directives step by step, in their order ([DEC-001](../../../../../.pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md)). It types narration, chat messages and commands into the bare shell or the panes the executable storyboard binds, and sends the keys it names. It waits where a directive asks it to wait for a pattern on screen, a fixed time or the developer's Enter.
9. Once the last step ends, the system stops the capture and saves the video in the folder for videos. Where ffmpeg is installed, the system re-encodes the `.mov` into a smaller `.mp4`, and removes the `.mov`.
10. The system runs each after-record hook the recording configuration lists, in its order, from the configuration's folder. Each gets `DCR_SCENARIO`, `DCR_STORYBOARD`, `DCR_VIDEO_PATH`, `DCR_CONFIG` and `DCR_REPO_ROOT`. Each also gets a `DCR_META_<KEY>` for each scalar key of the executable storyboard's front matter.
11. The system closes the two windows.

**Variants:**

- **1a.** The demo bundle exists already, from an earlier recording. The path goes on at step 2.
- **1b.** The developer has an AI agent write the demo bundle through the `demo-recording` skill's `new-bundle` and `storyboard-author` operations, and its after-record hooks through `hook-author`. The agent may also run steps 2 and 4 for the developer, through the skill's `validate` and `start` operations. The path goes on at step 2.
- **3a.** The executable storyboard breaks its format, in one of these ways:
  - it has no title
  - two of its steps share a number
  - a fenced block is never closed

  Or a directive's content is not what its tag asks. The system lists each error with its line, and exits with status 1. The developer mends the document, and the path goes back to step 2.
- **3b.** A fenced block carries a language tag that no loaded plugin provides. The system warns, naming its step and line, and goes on with the next fenced block ([DEC-001](../../../../../.pkit/capabilities/demo-recording/decisions/DEC-001-storyboard-as-executable-format.md)). At step 8, the system skips that fenced block with a warning.
- **4a.** The developer passes `--validate`. The system finds the executable storyboard and the recording configuration as step 5 does, and variant 5a applies. It then parses and prints the executable storyboard as step 3 does, opens no window, and the use case ends.
- **4b.** The developer passes `--no-recording`. The system carries out the directives as step 8 does, with no screen capture. It saves no video, runs no after-record hook and leaves both windows open, and the use case ends.
- **4c.** The developer passes `--interactive`. The system waits for the developer's Enter in the second window before the capture starts, and again before it stops. Ctrl-C at the first prompt starts no capture, leaves both windows open, and ends the use case. Ctrl-C at the second prompt keeps the capture running until the developer runs `pkit demo-recording record stop`, and the path then goes on at step 9.
- **4d.** The developer runs `pkit demo-recording record windows --config <bundle>/record.yaml`. The system opens the two windows as step 7 does, for a rehearsal, and records nothing. The use case ends.
- **4e.** The developer runs `pkit demo-recording run <storyboard>` instead. With `--validate`, the system does what step 3 does, on any platform. Otherwise it checks the platform as step 5 does, then carries out the directives as step 8 does, in the window that has the focus. It opens no window and captures nothing, and the use case ends.
- **5a.** The system finds no executable storyboard for `<demo>`, or no recording configuration. It refuses, saying where it looked, and the use case ends.
- **5b.** The system runs on another platform. It refuses with `demo-recording: this action requires macOS (darwin); detected '<os>'.`, and names `validate` and `--validate` as the paths that run anywhere. It writes nothing, and the use case ends.
- **6a.** The recording configuration lacks `cwd`, or the bounds of a window. The system refuses with `record.sh: config missing required fields (cwd / windows.recording / windows.control)`, and the use case ends.
- **6b.** The executable storyboard does not parse. The system refuses with `record.sh: storyboard has parse errors.  Run with --validate to see them.`, and opens no window. The use case ends.
- **8a.** The developer presses Ctrl-C in the second window. The system stops the capture, and the path goes on at step 9 with the video recorded so far.
- **8b.** A `ready` directive sees no new occurrence of its pattern within its timeout, 30 seconds unless it names another. The system warns, and goes on with the next directive.
- **8c.** A `narrate`, `chat` or `shell` directive comes before any `panes` directive binds the pane of that `narrate`, `chat` or `shell` directive. The system warns, and types into the pane that has the focus.
- **9a.** ffmpeg is not installed, or its conversion fails. The system keeps the `.mov` as the video.
- **10a.** An after-record hook is not executable, or exits with a status other than 0. The system warns and goes on with the next hook, and the recording does not fail.

**Postconditions:** The folder for videos holds the log of the run and its video, an `.mp4` where ffmpeg converted it and a `.mov` otherwise. Each executable after-record hook the recording configuration lists has run. The executable storyboard is as the developer wrote it, and still reads as a document.

**Minimal guarantees:**

- The check of step 3 changes no file of the project, and needs no macOS (core:REQ-005, [DEC-004 point 2](../../../../../.pkit/capabilities/demo-recording/decisions/DEC-004-platform-coupling-and-gate-placement.md#2-a-single-platform-gate-sits-at-the-recording-plugin-boundary-layer-3-of-demo-recordingdec-002-three-layer-plugin-architecture-not-at-the-capability-or-format-entry) and `validate.sh`).
- Off macOS, recording refuses before it writes anything or opens a window (DEC-004 point 2 and `platform-guard.sh`).
- An executable storyboard that does not parse opens no window and starts no capture (`record.sh`).
- Ctrl-C while the steps run stops the capture, so no capture runs on unseen (`_session.sh`).
- A failed conversion keeps the `.mov` (`ffmpeg_post.sh`).
- A failed after-record hook never fails a recording whose video is saved (`record.sh`).
