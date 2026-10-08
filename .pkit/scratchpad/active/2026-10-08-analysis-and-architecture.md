---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# Analysis and architecture

## The question

Should pkit's architecture and its software analysis live together, or live apart and point at each other? And either way, how does a change on one side reach the other?

The question came up on 8 October, while choosing the analysis's kinds (#1362). software-analysis DEC-001 point 11 leaves "architecture views" outside the analysis, until a real need arrives.

## Where things stand

- **The analysis** lives under `tech-docs/analysis/`. software-analysis owns it: actors, glossary terms, use cases, journeys and revalidation records (DEC-001).
- **The architecture** lives in two places today:
  - **Records:** architecture decision records under `tech-docs/architecture/decisions/`, 61 of them. The overlay's `adr-records` names that folder, and the architect agent keeps it (COR-025).
  - **Docs:** the overlay's `architecture-docs` names `CONTRIBUTING.md` and the core records (`.pkit/decisions/core/`). There is no document that shows the architecture as views.
- **How they point at each other now:** an actor anchors to the records its role rests on (for example COR-009 for the developer). A use case will anchor to its actor, and may anchor to code and records. Nothing on the architecture side points at the analysis.

## Established practice

- **Kruchten's 4+1 view model (1995).** Four views describe an architecture: logical, process, development and physical. The use cases are the "+1": the scenarios that tie the four views together and check them.
- **RUP's use-case realisations.** Each use case has a realisation in the design model: which elements carry it out. Analysis and design stay apart, but every use case can be traced into the design.
- **C4 (Simon Brown).** Context, containers, components and code. Its system-context diagram names the people and other systems that use the system, which are close to our actors.
- **arc42.** A template for architecture documentation. Its "context and scope" section lists the system's users and neighbouring systems, and its "runtime view" walks important scenarios.

The common thread: architecture and analysis are kept as separate descriptions, but scenarios or use cases are the bridge between them.

## Forces

- **Owners.** The architect agent keeps architecture records; software-analysis keeps the analysis. Merging the places mixes owners (COR-013, every file has one owner).
- **Pace.** Use cases change when behaviour changes. Architecture changes when structure changes. These are different events.
- **Traceability.** A change to a component should reach the use cases it serves, and a new use case should reach the components that will carry it. Friction anchors already do this for anything they can name.
- **Duplication.** Actors and the system context describe the same people and systems. Two descriptions of one thing drift (living-docs' rule RS-LDOC-002: each fact is stated once).
- **Readers.** A newcomer wants one place to start. A maintainer wants each thing in one home.
- **Start small.** DEC-001 point 11 asks for a real need before a new kind.

## Candidate alternatives

- **A. Live together.** Architecture views move into the analysis's root, as one model with views and use cases side by side. One place to read, but mixed owners and paces.
- **B. Live apart, linked by anchors.** Each stays where it is. An architecture view, when one exists, anchors to the use cases it realises, and a use case anchors to the architecture records it rests on. A change on either side flags the other through friction. This is the "+1" of 4+1, made checkable.
- **C. The analysis gains an architecture-view kind.** software-analysis adds a kind for views (a context view, a component view), owned by the analysis. DEC-001 point 11 would need its own decision for it.
- **D. Architecture gains a context view that cites the actors.** The architecture side keeps a system-context view whose people and systems are the analysis's actors, cited by id rather than described again. It removes the duplication without moving anything.

B and D can combine: apart, anchored both ways, with the context view naming actors by id.

## The maintainer's view, 8 October

The analysis describes the requirements: what the system must do, and for whom. The architecture describes the solution: how the system is built to do it. So the two stay separate.

- **This matches established practice.** Requirements engineering keeps the problem space apart from the solution space (the "what" from the "how"). RUP keeps its requirements discipline apart from analysis and design. 4+1 and arc42 keep the architecture as its own description, with scenarios as the bridge.
- **It rules out A and C.** Both put solution views inside the analysis.
- **B and D remain.** Both keep the two apart, and differ only in how they point at each other. Whether they link at all, and how, is the question left.

## Open questions

- Does pkit need architecture views at all yet, beyond its decision records? If not, B is mostly about use cases anchoring to records, which they already may.
- Which direction must friction flow first: architecture → analysis, analysis → architecture, or both?
- Where would a view live, and which agent keeps it: the architect, or a capability?
- Does a use-case realisation (which components carry a use case) belong in the use case, in the view, or in neither?
