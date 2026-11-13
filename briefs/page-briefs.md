# The showcase deck's page briefs

**Audience:** developers who have not used pkit, a tool that brings a methodology into a software project.

**Media:** 1280 × 720 slides, projected in a room during a 30-minute talk, also handed out as a PDF and shown as a web page. There are two languages, English and Czech, and two modes, light and dark.

## 1. How pkit fits together

- **Point (the lead):** "In five layers, from your decisions down to your code: each carries out the ones above it."
- **Structure:** an ordered stack of five layers, with the source at the top: decisions; working rules, schemas and processes; skills, agents and permissions; pkit's commands and checks; your code and documents.
  - Ideas enter at the top.
  - Two relations run between layers: each layer carries out the one above it, and where a layer and a decision disagree, the layer is checked first.
- **The original, which the maintainer liked:** a stepped pyramid, narrow at the top, darkest at the top. The notes stood on the left, so the slide read left to right, and the ideas arrow entered the apex. A reader saw at once that decisions are the source and everything below carries them out.

## 2. Install pkit

- **Point:** "Install the tool once, then add pkit to each project with one command. Upgrades replace pkit's files, never yours."
- **Structure:**
  - two steps in order: once on your machine, then in each project;
  - what a project then holds, split into pkit's files and your files;
  - an alternative for whoever does not want pkit in the repository: `pkit visibility private`.
- **The original's style:** command lines on a light terminal panel, in a monospace. The prompt and comments are grey and the command is green. In a listing, pkit's files are purple and yours are blue, told apart by a key line.

## 3. Where permissions come from

- **Point:** "From rules your project writes down as data. Your AI tool applies them to every call, so they hold when an agent forgets them."
- **Structure:** three kinds of permission (guardrails for everyone, an agent's own tools, one agent's rule), each passing through the same three stages: written as data, what your AI tool gets, what a call meets. Plus one limit: a command hidden behind another can slip past.
- **Evidence:** a line on how project-kit itself uses it.

## 4. How capabilities work together

- **Point:** "A capability never names another, only a role. One that needs something opens a slot, and any other can fill it."
- **Structure:** a mapping. Two capabilities, living-docs and software-analysis, fill three slots that project-management opens: the docs a change must update, which agent fixes each doc, and the use cases to plan from. Each capability plays a role.
  - **Evidence:** real `pkit status` output showing the roles and a filled slot.
  - **What it gives you:** swap a capability for one in the same role, install only what you need, and `pkit validate` checks the wiring.
  - **The limit:** each role has one capability so far.
