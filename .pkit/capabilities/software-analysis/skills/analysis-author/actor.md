# Adding an actor

An actor is a named role that uses the system, with needs of its own. It is a file of its own, `use-case-model/actors/ACT-<slug>.md`, and the use cases and journeys that are its goals name it.

## 1. Is it an actor?

A role, not a person: a kind of user, a team, or another system acting on this one. Two roles with the same needs are one actor; one person who comes with two different sets of needs is two. A permission level is an actor only when it brings needs of its own.

A user story — a need in one sentence — is not an artefact of its own: it is one of the actor's `needs`, and the goal of a use case.

## 2. Choose the slug and the name

The role as the domain says it, in the singular — `tester`, `release-manager`, `billing-system`. The slug is the id for ever, and names the file. `--name` is the display name and may change.

## 3. Decide what it rests on

Where does the software, or a decision, embody this role? The authentication role or the entry point it uses (`--path`), the decision that names it (`--record`). Anchor the narrowest thing that would change if the role changed.

When nothing embodies it — a sponsor, an outside auditor — stamp it with `--unanchored-because "<why>"` instead. Never both.

## 4. Stamp it

```
pkit analysis new actor <slug> --name "<Display name>" [--path <glob>]... [--record <id>]...
pkit analysis new actor <slug> --name "<Display name>" --unanchored-because "<why nothing embodies it>"
```

The stamp writes `ACT-<slug>.md` in the actors' folder, headed `# ACT-<slug> — <name>`. Its front matter holds the id, the name and the needs, so the needs read just above the description. `needs` holds one item, its hint, as each part of the body does: `<!-- pkit:hint … -->`, which says what goes there and gives an example.

## 5. Fill it

Fill each part as its hint says, and delete the hint: each part of the body, and `needs` in the front matter, whose one item holds its hint. The needs stay in the front matter, where a tool reads them, and never go in the body.

Then run the checks in the shared framing's "After stamping", `pkit analysis validate --preview` first.

## Later

- **Renaming** — change `name`, and the heading after the id with it: the check holds the two to agree. The id and the file's name stay, so nothing citing it breaks.
- **Withdrawing** — set `status: withdrawn` once no use case or journey in force names the actor. The file stays.
