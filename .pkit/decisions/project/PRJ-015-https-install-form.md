---
id: PRJ-015
title: pkit is installed over the repository's public HTTPS URL
status: accepted
date: 2026-11-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

**In plain terms:** pkit's install command names the repository's HTTPS URL rather than its SSH URL. The repository is public, so an install over HTTPS needs no key and no token, and it works the same on a person's laptop and on a machine nobody set up. A machine that reaches github.com over SSH alone keeps the same command and configures itself to send it over SSH. A script a project carries to run this install, for a machine with nobody at the keyboard, is no installer of its own. The channel stays as [PRJ-004](PRJ-004-distribution-channel.md) decides it: a direct git URL on github.com with no registry, `uv tool install` as the only frontend, and release tags with `latest`. The tool's own side, the URL compiled into it, how its fetches fail and the install script it ships, is [ADR-090](../../../tech-docs/architecture/decisions/ADR-090-self-fetch-over-https.md)'s, accepted with this record.

PRJ-004 recommends the SSH form, `git+ssh://git@github.com/aleskalfas/project-kit.git`. It weighs SSH against HTTPS with a token, which it keeps for a person who authenticates that way, and says a pipeline that installs pkit needs an SSH deploy key or a token in its runner. Its reason, that most developers already hold an SSH key for github.com, assumes a token is the price of HTTPS.

A public repository fetched over HTTPS needs no credential, so neither the key nor the token is needed. Installs on machines with nobody at the terminal, such as a pipeline's runner, a container or a hosted agent's machine, met the SSH form's cost in [#3002](https://github.com/aleskalfas/project-kit/issues/3002): such a machine often holds no SSH key, and nobody is there to add one.

## Decision

pkit is installed over the repository's public HTTPS URL, with no credential, and a script that runs that install is no installer of its own.

### 1. The install the project gives names the HTTPS URL

The install of pkit that the project gives, and every install line the tool prints, name the HTTPS URL:

```
uv tool install git+https://github.com/aleskalfas/project-kit.git@latest
```

The same URL names a given release, `@v<version>`, and the development install, with no tag. The changelog, the release notes and a record's Context, which record the install of their day, stay as they were written.

### 2. One URL form is documented

The project documents the HTTPS form alone. A machine that reaches github.com over SSH and not over HTTPS keeps the same lines, and configures its own git and uv to send these fetches over SSH, such as by git's URL rewriting (`url.<base>.insteadOf`). That configuration is the machine's: the project names what it takes, and pkit writes none of it, since a rule in a machine's configuration reaches every repository that machine fetches.

### 3. The documented install needs no credential

Over the documented form, installing pkit needs no credential on any machine while the repository is public, a pipeline's runner included. A fetch that does need one uses the credential the machine already holds, and pkit adds no credential of its own. Such fetches include one a machine sends over SSH by its own configuration, which needs its SSH key, and an install from a fork kept in a private repository, which needs an SSH key the machine holds or a token in its git credential store. A private repository's credential in a pipeline stays a concern of the project that keeps the repository.

### 4. A script that runs the install is no installer of its own

A script a project carries in its repository, which runs `uv tool install` from this URL at a release tag, adds no install path. So PRJ-004's ban on a `curl … | bash` installer does not reach it.

## Rationale

**Why HTTPS.** PRJ-004 chose SSH over HTTPS with a token. A public repository's HTTPS form needs no token, so SSH's advantage is gone for a person at their laptop as much as for a machine. An HTTPS fetch reaches github.com from any machine that reaches it over HTTPS, and needs nothing set up first.

**Why one URL form.** A second form would buy nothing for a public repository. A person who prefers SSH gains nothing by it, and a machine that reaches github.com over SSH alone is served by its own configuration with the same lines. One form also keeps what the project documents equal to what the tool prints.

**Who loses, and their remedy.** Two kinds of machine that installed over SSH no longer install with the documented lines as they stand:

- a machine whose egress allows SSH to github.com but not HTTPS, which configures its own git and uv as point 2 says;
- a machine behind a proxy that intercepts TLS, which reaches github.com over HTTPS but fails on the proxy's certificate, and trusts that certificate in git and in uv, as any HTTPS tool there needs.

**Why such a script is no installer.** PRJ-004 rejects a `curl … | bash` installer for two reasons: it runs a script fetched over the network, and it needs the installer hosted somewhere. Neither holds for a script a project carries. It is not fetched to be run: it sits in the project's repository, committed and reviewed like any other file there. Nothing is hosted for it beyond the repository the channel already names. What installs pkit is still `uv tool install` from the git URL at a release tag. So PRJ-004's "No registry today" admits the script, and this point changes nothing PRJ-004 decides.

**Why a record of its own, and not an edit to PRJ-004.** PRJ-004 chose the SSH form among the alternatives and gave its reason. This record decides otherwise on that one choice, so it partly supersedes PRJ-004, and the channel stands (decisions README, "Refining an accepted record"). The precedent is PRJ-010's partial supersession of PRJ-003.

### Alternatives considered

- **Keep SSH canonical, with HTTPS secondary.** Rejected: the lines pkit prints and gives take the canonical form, so a machine that follows them gets SSH and needs a key nobody is there to add.
- **Keep the SSH form documented beside the HTTPS one.** Rejected: for a public repository it serves nobody the machine's own configuration does not, and a second documented form drifts from what the tool prints.
- **HTTPS with a token as the form for machines.** Rejected: a public repository needs no token, and a token would add a credential to store and rotate.
- **Supersede PRJ-004 whole with a restated channel record.** Rejected: the channel, the frontend, the tags and the revisit threshold stand, and many artefacts and code comments cite PRJ-004 for them. A partial supersession changes only what is overturned.

## Implications

- **PRJ-004** gains this line at the top of its body, before its Context:

  > **Partially superseded by [PRJ-015](PRJ-015-https-install-form.md).** The install names the repository's public HTTPS URL, `uv tool install git+https://github.com/aleskalfas/project-kit.git@latest`, and needs no credential. Overturned: the SSH form of the canonical command in the Decision; the frontend paragraph's sentence keeping HTTPS for token users; the SSH command in "Why git URL beats `curl … | bash`"; "Why SSH is the recommended URL form"; the premise that an install needs the person's GitHub auth, in "Why git URL beats every registry option" and the private-registry alternative; and, in the Implications, that an install authenticates with an SSH key or a token, that a pipeline needs an SSH deploy key or a token, and the promise to document that pattern. Kept: pkit adds no credential surface, and a private repository's credential in a pipeline is its project's own concern (PRJ-015 point 3). The rest of PRJ-004 stands.

  PRJ-004's text stays as it is under that line. Point 4 changes nothing PRJ-004 decides, so the line does not name it.
- **The CLI reference's section on installing pkit** is the home of the documented lines, and names what a machine that reaches github.com over SSH alone configures. The line `pkit init` prints follows the URL compiled into the tool (ADR-090), and a test holds it equal to the CLI reference's, as before. Every other place that gives an install line follows point 1.
- **ADR-040 stands.** A private source's credential, which it rests on, is still an SSH key the machine holds or a token in its git credential store, as point 3 keeps for a private repository. pkit still adds no credential surface, and that credential in a pipeline is still its project's concern.
- **The analysis anchored on PRJ-004.** About thirty artefacts anchor PRJ-004 whole, and the line at its top flags each one. The change answers them all, and edits those whose text names SSH or a credential the install no longer needs. UC-048 is among them: the operator reaches the repository over HTTPS with no credential, step 1 names the HTTPS form, and variant 1a keeps its letter and says a token serves a fork kept in a private repository. Its anchors add this record. ADR-090 gives REQ-031's measure.
- **Revisit** when the repository's visibility changes, or when github.com starts to ask a credential of an anonymous HTTPS fetch.
- **No migration.** No installed state changes shape. What becomes of a pkit installed over SSH is the tool's side (ADR-090).
- **Stands on** PRJ-004, accepted, and the decisions README's rule on refining an accepted record.
