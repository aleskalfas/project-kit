---
id: UC-026
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
---

# UC-026 — Record a demo of my command line

**Goal:** Record a demo of my command line by running an executable storyboard, a document people read as it stands.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): writes the demo bundle, or runs these commands, for the developer through the `demo-recording` skill. The skill has it validate the executable storyboard before every recording (the skill's `start` operation).

**Preconditions:** None.

**Assumptions:**

- The project has demo-recording installed, or registered in place where it is developed. Its commands then answer as `pkit demo-recording record`, `run` and `validate` (COR-017, COR-021 and COR-031).
- The AI agent of variant 1b can load the `demo-recording` skill, deployed with demo-recording. It is one skill with an operation for each task (COR-005, COR-013 and COR-020).
- Where the machine runs macOS, it has iTerm2, and the terminal app that runs the commands holds the Accessibility and Screen Recording permissions. Nothing in the system checks them (DEC-004 point 1).
- Each command an executable storyboard types runs in the developer's own shell, as the developer wrote it. Nothing in the system checks what it does (DEC-001).

**Trigger:** The developer wants a recorded demo of a command line, such as a walk through a feature for colleagues to watch.

**Main path:**

1. The developer writes a demo bundle: its recording configuration, `record.yaml`, and an executable storyboard in its `storyboards/` folder.
2. The developer runs `pkit demo-recording validate <storyboard>`.
3. The system parses the executable storyboard, and checks the content of each directive. It prints each step with a line for each of its directives, and ends with `✓ <n> step(s) parsed.  No errors.`. It writes nothing (core:REQ-005), and runs on any platform (DEC-004 point 2).
4. The developer runs `pkit demo-recording record <demo> --config <bundle>/record.yaml`. `<demo>` is a path, or a name the system looks for beside the configuration and in its `storyboards/` folder.
5. The system finds the executable storyboard and the recording configuration. Before it reads the configuration's fields, it checks that it runs on macOS (DEC-004 point 2).
6. The system reads the working directory and the bounds of two windows from the recording configuration, and parses the executable storyboard again. Only then does it create the folder for videos, `recordings/` unless the configuration names another, and start a log of the run in its `.logs/`.
7. The system opens two iTerm2 windows at those bounds, each in the working directory. It records the first, and drives the recording from the second, outside the recorded area.
8. The system starts the screen capture of the first window, and carries out the directives step by step, in their order (DEC-001). It types narration, chat messages and commands into the panes the storyboard binds them to. It waits where a directive asks it to wait for a pattern on screen, a fixed time or the developer's Enter.
9. Once the last step ends, the system stops the capture and saves the video in the folder for videos. Where ffmpeg is installed, it re-encodes the `.mov` into a smaller `.mp4`, and removes the `.mov`.
10. The system runs each after-record hook the recording configuration lists, in its order, from the configuration's folder. Each gets `DCR_SCENARIO`, `DCR_STORYBOARD`, `DCR_VIDEO_PATH`, `DCR_CONFIG` and `DCR_REPO_ROOT`, and a `DCR_META_<KEY>` for each key of the storyboard's front matter.
11. The system closes the two windows.

**Variants:**

- **1a.** The demo bundle exists already, from an earlier recording. The path goes on at step 2.
- **1b.** The developer has an AI agent write the demo bundle through the `demo-recording` skill's `new-bundle` and `storyboard-author` operations, and its after-record hooks through `hook-author`. The path goes on at step 2.
- **3a.** The executable storyboard breaks its format: it has no title, two of its steps share a number, or a fence is never closed. Or a directive's content is not what its tag asks. The system lists each error with its line, and exits with status 1. The developer mends the document, and the path goes back to step 2.
- **4a.** The developer passes `--validate`. The system parses and prints the executable storyboard as step 3 does, and opens no window. The use case ends.
- **4b.** The developer passes `--no-recording`. The system carries out the directives as step 8 does, with no screen capture. It saves no video, runs no after-record hook and leaves both windows open, and the use case ends.
- **4c.** The developer passes `--interactive`. The system waits for the developer's Enter in the second window before the capture starts, and again before it stops. Ctrl-C at the second prompt keeps the capture running until the developer runs `pkit demo-recording record stop`. The path then goes on at step 9.
- **4d.** The developer runs `pkit demo-recording record windows --config <bundle>/record.yaml`. The system opens the two windows as step 7 does, for a rehearsal, and records nothing. The use case ends.
- **4e.** The developer runs `pkit demo-recording run <storyboard>` instead. After the check of step 5, the system carries out the directives as step 8 does, into the pane that has the focus. It opens no window and captures nothing, and the use case ends. With `--validate`, it does what step 3 does.
- **5a.** The system finds no executable storyboard for `<demo>`, or no recording configuration. It refuses, saying where it looked, and the use case ends.
- **5b.** The system runs on another platform. It refuses with `demo-recording: this action requires macOS (darwin); detected '<os>'.`, and names validation as the path that runs anywhere. It writes nothing, and the use case ends.
- **6a.** The recording configuration lacks `cwd`, or the bounds of a window. The system refuses with `record.sh: config missing required fields (cwd / windows.recording / windows.control)`, and the use case ends.
- **6b.** The executable storyboard does not parse. The system refuses with `record.sh: storyboard has parse errors.  Run with --validate to see them.`, and opens no window. The use case ends.
- **8a.** The developer presses Ctrl-C in the second window. The system stops the capture, and the path goes on at step 9 with the video recorded so far.
- **8b.** A `ready` directive sees no new occurrence of its pattern within its timeout, 30 seconds unless it names another. The system warns, and goes on with the next directive.
- **9a.** ffmpeg is not installed, or its conversion fails. The system keeps the `.mov` as the video.
- **10a.** An after-record hook is not executable, or exits with a status other than 0. The system warns and goes on with the next hook, and the recording does not fail.

**Postconditions:** The folder for videos holds the log of the run and its video, an `.mp4` where ffmpeg converted it and a `.mov` otherwise. Each after-record hook has run. The executable storyboard is as the developer wrote it, and still reads as a document.

**Minimal guarantees:**

- Validation writes nothing, and needs no macOS (core:REQ-005, DEC-004 point 2 and `validate.sh`).
- Off macOS, recording refuses before it writes anything or opens a window (DEC-004 point 2 and `platform-guard.sh`).
- An executable storyboard that does not parse opens no window and starts no capture (`record.sh`).
- Ctrl-C while the steps run stops the capture, so no capture runs on unseen (`_session.sh`).
- A failed conversion keeps the `.mov` (`ffmpeg_post.sh`).
- A failed after-record hook never fails a recording whose video is saved (`record.sh`).
