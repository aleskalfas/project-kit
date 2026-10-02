# Adding an actor

An actor is a named role that uses the system, with needs of its own. It is an entry of the actors' collection file, `ACT-<slug>`, and the use cases and journeys that are its goals name it.

## 1. Is it an actor?

A role, not a person: a kind of user, a team, or another system acting on this one. Two roles with the same needs are one actor; one person who comes with two different sets of needs is two. A permission level is an actor only when it brings needs of its own.

A user story — a need in one sentence — is not an artefact of its own: it is one of the actor's `needs`, and the goal of a use case.

## 2. Choose the slug and the name

The role as the domain says it, in the singular — `tester`, `release-manager`, `billing-system`. The slug is the id for ever; `--name` is the display name and may change.

## 3. Decide what it rests on

Where does the software, or a decision, embody this role? The authentication role or the entry point it uses (`--path`), the decision that names it (`--record`). Anchor the narrowest thing that would change if the role changed.

When nothing embodies it — a sponsor, an outside auditor — stamp it with `--unanchored-because "<why>"` instead. Never both.

## 4. Stamp it

```
pkit analysis new actor <slug> --name "<Display name>" [--path <glob>]... [--record <id>]...
pkit analysis new actor <slug> --name "<Display name>" --unanchored-because "<why nothing embodies it>"
```

The entry is added to the actors' file where its id sorts, with its section in the body; the file is created the first time.

## 5. Fill it

- **`needs`** — what the actor needs from the system, one line each, replacing the placeholder.
- **The body section** — who this is, when they come to the system, and what they bring with them.

Then run the checks in the shared framing's "After stamping".

## Later

- **Renaming** — change `name`; the id stays, so nothing citing it breaks.
- **Withdrawing** — set `status: withdrawn` once no use case or journey in force names the actor.
