---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-backbone-configuration, name: backbone configuration}
      - {id: TERM-install, name: install}
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
  definition: "script of project-owned content that a recording configuration lists, run once each recording's video is saved, with that video's path in its environment"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/scripts/record.sh
          - .pkit/capabilities/demo-recording/skills/demo-recording/hook-author.md
        record:
          - COR-001
          - COR-003
          - COR-059#2
TERM-demo-bundle:
  name: demo bundle
  status: active
  definition: "folder of project-owned content that holds a recording configuration with the executable storyboards, after-record hooks and videos recorded under that configuration"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/skills/demo-recording/new-bundle.md
          - .pkit/capabilities/demo-recording/scripts/record.sh
        record:
          - demo-recording:DEC-001
          - COR-001
          - COR-003
          - COR-059#2
TERM-directive:
  name: directive
  noun-forms: [directives]
  status: active
  definition: "fenced block in a step of an executable storyboard whose language tag selects what is done at that point, such as typing a command"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/demo-recording/scripts/storyboards/parser.py
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
  definition: "YAML file, `record.yaml` by default, setting the working directory and bounds of the two terminal windows a demo runs in, and the folder for videos"
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
  - **Term:** [backbone configuration](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-backbone-configuration--backbone-configuration)
  - **Term:** [install](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-install--install)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [project-owned content](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project-owned-content--project-owned-content)
  - **Term:** [skill](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-skill--skill)
  - **Term:** [storyboard](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-storyboard--storyboard)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Record a demo of my command line by running an executable storyboard, a document people read as it stands.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)

## TERM-after-record-hook — after-record hook

**Example:** `hooks/upload-to-cdn.sh`, listed under `hooks.after_record` in `record.yaml`, uploads the video that `DCR_VIDEO_PATH` names. It reads `DCR_META_MODE`, which the executable storyboard's front matter sets as `mode: ai`.

**Distinctions:**

- **Git hook:** a script git runs at one of its own events, such as `pre-push`. An after-record hook runs only once a recording's video is saved (`record.sh`).

## TERM-demo-bundle — demo bundle

**Example:** `demo/quickstart/` holds `record.yaml`, the executable storyboards `storyboards/ai.md` and `storyboards/human.md`, a `hooks/` folder and the `recordings/` folder its first recording creates.

**Distinctions:**

- **demo-recording's own files:** the format, the commands and the skill, which demo-recording ships. demo-recording never holds a demo bundle, which stays in the project's tree (DEC-001).

## TERM-directive — directive

**Example:** a block fenced with the tag `shell` and holding `git status` types the command into the pane bound to `shell`, and runs it.

**Distinctions:**

- **Prose:** the text of a step around its directives. People read it, and nothing carries it out (DEC-001).
- **Code block:** in other Markdown, a fenced block that shows code and runs nothing. In a step of an executable storyboard, every fenced block is read as a directive. Before the first step, a fenced block is part of the opening prose (`parser.py`).

## TERM-executable-storyboard — executable storyboard

**Example:** a demo's document opens with its title, then `## Step 1 — <title>`, with prose for the reader and a directive that types the first command.

**Distinctions:**

- **Storyboard:** the core's term for a document that scripts a dialogue with a person, which a file written after it follows. No separate file follows an executable storyboard: demo-recording's commands carry it out directly (DEC-001).
- **Driver script:** a script written for one demo that types its keystrokes itself. DEC-001 rejected it, since a reader would have to run the script in their head to recover the demo.
- **Data file and generator:** a structured file that a generator reads to drive a demo or to render its readable form. DEC-001 rejected it too: the executable storyboard is the one source, and nothing is generated from it.

## TERM-recording-configuration — recording configuration

**Example:** `demo/quickstart/record.yaml` names its `cwd`, the bounds `windows.recording` and `windows.control`, and `recordings_dir: ./recordings`. Its line `pkit_schema: demo-recording:record-config` binds it to its schema.

**Distinctions:**

- **Tunables:** typing speed and post-processing, such as `CHUNK_SIZE` and `DCR_CRF`, are environment variables of one run, not fields of the file. Whether they move into it is unsettled (`record-config.yaml`).
- **Backbone configuration:** the core's file of one project's declarations. A recording configuration serves demo-recording's commands alone.
