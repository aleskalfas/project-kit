---
rule-set: VIS
loaded: true
budget: 383
version: 1.0.0
rules:
  RS-VIS-001:
    origin: {decision: "visual-communication:DEC-024"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-024#6"]}
  RS-VIS-002:
    origin: {decision: "visual-communication:DEC-024"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-024#6"]}
  RS-VIS-003:
    origin: {decision: "visual-communication:DEC-024"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-024#4", "visual-communication:DEC-024#6"]}
  RS-VIS-004:
    origin: {decision: "visual-communication:DEC-024"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-024#6", "visual-communication:DEC-020#5"]}
---

## Operational rules of the visual-communication capability

*These are the visual-communication capability's operational rules, kept as its loaded rule set `VIS` (COR-070). They bind on the work of every session in a project where visual-communication is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one of these rules cannot be kept with a rule of another capability's, stop the step and report the clash, rather than choose between them. Where a project's rule cannot be kept with one of these, this one binds. The loaded file is generated from `.pkit/capabilities/visual-communication/rule-sets/vis.md`, where the set is authored, by `pkit rule-sets generate`. A project that receives them by sync or install edits neither.*

### RS-VIS-001 — Never take a command of the capability out of the sandbox yourself

**Never apply an exclusion from the session's sandbox, and never use the harness's escape on your own, to run a command of visual-communication outside it.** Letting a command out of the sandbox is a person's act (visual-communication DEC-024 point 6).

### RS-VIS-002 — Run a command in the form the project writes it

**Run each command of visual-communication in the form the project uses, and never change that form to slip out of the session's sandbox.** One such change is running it as `uv run` where the permission model excludes `uv` (visual-communication DEC-024 point 6).

### RS-VIS-003 — Where a look stops on a sandbox, read a pipeline's drawings or ask a person

**Where the session's sandbox stops `pkit visual look`, read a build pipeline's drawings of the piece where you can reach them.** Otherwise, or where you need the working tree drawn, ask a person, naming the ways on the stop names. A run the permission model confines, such as a builder's, reaches no pipeline's drawings. There only the SVG renderer's pages remain (visual-communication DEC-024 points 4 and 6).

### RS-VIS-004 — Read the folder a person's look left, and never draw over it

**Where a person ran `pkit visual look` outside the session's sandbox, read the folder that run left, and never run the look over it.** A run replaces its renderer's folder (visual-communication DEC-024 point 6, DEC-020 point 5).
