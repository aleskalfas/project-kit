---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-project, name: project}
      - {id: TERM-project-owned-content, name: project-owned content}
      - {id: TERM-skill, name: skill}
      - {id: TERM-storyboard, name: storyboard}
      - {id: TERM-system, name: system}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Record a demo of my command line by running an executable storyboard, a document people read as it stands.
      - id: ACT-ai-agent
        name: AI agent
TERM-after-record-hook:
  name: after-record hook
  status: active
  definition: "script of project-owned content that runs once each recording stops, with the video's path and the executable storyboard's front matter in its environment"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/scripts/record.sh
          - .pkit/capabilities/demo-recording/skills/demo-recording/hook-author.md
TERM-demo-bundle:
  name: demo bundle
  status: active
  definition: "folder of project-owned content that holds the recording configuration, executable storyboards, after-record hooks and videos of one recorded walkthrough of a command line"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/skills/demo-recording/new-bundle.md
          - .pkit/capabilities/demo-recording/scripts/record.sh
        record:
          - demo-recording:DEC-001
TERM-directive:
  name: directive
  noun-forms: [directives]
  status: active
  definition: "fenced block of an executable storyboard whose language tag names what is done at that point of the demo, such as typing a command"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/scripts/storyboards/plugin.py
          - .pkit/capabilities/demo-recording/scripts/plugins/recording/directives.py
        record:
          - demo-recording:DEC-001
          - demo-recording:DEC-002
TERM-executable-storyboard:
  name: executable storyboard
  noun-forms: [executable storyboards]
  status: active
  definition: "Markdown document that scripts a demo of a command line step by step, which people read as it stands and demo-recording's commands carry out directly"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/scripts/storyboards/parser.py
        record:
          - demo-recording:DEC-001
TERM-recording-configuration:
  name: recording configuration
  noun-forms: [recording configurations]
  status: active
  definition: "YAML file, `record.yaml`, that sets the working directory, window bounds, videos' folder and after-record hooks of one demo's screen captures"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/schemas/record-config.*
        record:
          - demo-recording:DEC-001
          - COR-023
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `020-set-up`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than demo-recording's floor, 1.26.0.
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [project-owned content](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project-owned-content--project-owned-content)
  - **Term:** [skill](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-skill--skill)
  - **Term:** [storyboard](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-storyboard--storyboard)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Record a demo of my command line by running an executable storyboard, a document people read as it stands.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)

## TERM-after-record-hook — after-record hook

**Example:** `hooks/upload-to-cdn.sh`, which a recording configuration lists under `hooks.after_record`, uploads the video that `DCR_VIDEO_PATH` names.

**Distinctions:**

- **Git hook:** a script git runs at one of its own events, such as `pre-push`. An after-record hook runs only once a recording stops (`record.sh`).

## TERM-demo-bundle — demo bundle

**Example:** `demo/quickstart/` holds `record.yaml`, the executable storyboard `storyboards/quickstart.md`, a `hooks/` folder and the `recordings/` folder its first recording creates.

**Distinctions:**

- **The capability's own files:** demo-recording ships the format, the commands and the skill. It never holds a demo bundle, which stays in the project's tree (DEC-001).

## TERM-directive — directive

**Example:** a block fenced with the tag `shell` and holding `git status` has the command typed into the pane the storyboard binds to the shell, and run.

**Distinctions:**

- **Prose:** the text of a step around its directives. People read it, and nothing carries it out (DEC-001).
- **Code block:** in other Markdown, a fenced block that shows code and runs nothing. In a step of an executable storyboard, every fenced block is read as a directive (`parser.py`).

## TERM-executable-storyboard — executable storyboard

**Example:** a demo's document opens with its title, then `## Step 1 — <title>`, with prose for the reader and a directive that types the first command.

**Distinctions:**

- **Storyboard:** the core's term for a document that scripts a dialogue with a person, which the file that carries it out follows. An executable storyboard runs commands, and scripts no dialogue.
- **A generated file:** none exists. The document is the one source, and nothing is generated from it (DEC-001).

## TERM-recording-configuration — recording configuration

**Example:** `demo/quickstart/record.yaml` names its `cwd`, the bounds `windows.recording` and `windows.control`, and `recordings_dir: ./recordings`. Its line `pkit_schema: demo-recording:record-config` binds it to its schema.

**Distinctions:**

- **Tunables:** typing speed and post-processing, such as `CHUNK_SIZE` and `DCR_CRF`, are environment variables of one run, never fields of the file (`record-config.yaml`).
- **Backbone configuration:** the core's file of one project's declarations. A recording configuration sets one demo's recordings alone.
