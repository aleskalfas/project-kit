---
id: PRJ-014
title: The release step answers the friction its version edits raise
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

A release rewrites version lines, and every document anchored on a file it rewrites then owes the friction check an answer. The release step writes those answers itself, as `unchanged`, for each document that states none of the versions the rewritten lines held. Every other document stays asked, and a person answers it on the release branch, as before. So a document that states a version the release changes is still asked about, while the many that only anchor a package file for what else it declares no longer cost each release a commit of answers written by hand.

## Context

`pkit release apply` writes the release: each moving component's version and the ranges a release moves, the backbone's version, and the self-host manifest's version lines ([PRJ-002](PRJ-002-version-bump-policy.md) points D3 and D4, [PRJ-007](PRJ-007-release-maintains-self-host-manifest.md)). Documents anchor a component's package metadata for what it declares: its commands, its places, its connections, its dependencies. A path anchor stands on the whole file (COR-050 point 5), so a release's rewrite of one line asks every such document for an answer.

Cutting 2.0.0 asked eight documents, and 2.1.0 fourteen. Each release answered them by hand, in a commit on the release branch, and most of those answers said one thing: the release rewrote only version lines, and the document states none of those versions. A few documents do state one, such as a library page saying which capability release the library needs. Whether such a statement still holds is a judgement for a person.

A release pull request may already carry the answers its writes need, in answer files it adds, and the changeset guard still reads it as a release ([#2381](https://github.com/aleskalfas/project-kit/issues/2381)). How those answers come to be made was left open.

## Decision

**After its version edits, the release step writes the answers those edits owe wherever it can check what the answer claims, and leaves every other answer to a person.**

### 1. What the release step answers

Once it has written, the release step runs the change check over its own writes, against the commit it started from. It writes an `unchanged` revalidation (COR-050 point 3) for each artefact the check asks about where all of these hold:

- **Only version lines.** Every anchor the check asks the artefact about is a path anchor. Every file of the release's diff that the anchor stands on is a version file whose changed lines are only lines the release rewrites. A version file is a component's version file, such as its package metadata, or the self-host manifest. Its version lines are a component's version, its range on the backbone, its ranges on other capabilities, and the manifest's version lines.
- **No version the lines held.** The artefact's content (COR-050 point 5) states none of the versions those lines held before the release and no longer hold. A version counts as stated wherever it stands as a whole version number, not as part of a longer one.
- **Nothing else.** The check finds nothing else of the artefact that fails.
- **No deferral, no answers made apart.** The artefact carries no live deferral and no two live revalidations.

Each answer goes in an answer file the release adds (COR-062 point 1), committed with the release's writes.

### 2. What its reason says

The answer's `unchanged-because` names each version file, each line the release rewrote there, as it stood and as the release wrote it, and the versions the artefact does not state. It claims nothing the step did not check.

### 3. What it leaves to a person

Every other artefact the check asks about stays asked, and the release step names each, with why:

- **One that states a version a rewritten line held.** Whether the statement still holds is a judgement the step cannot make.
- **One asked about another write, or another anchor.** That is a write of the release's that is no version line, such as the changelog or a consumed changeset, or an anchor of any other kind.
- **One with a live deferral.** A revalidation that kept the deferral would claim to answer what it postponed (COR-050 point 4), and one that dropped it would end the debt it shows.
- **One whose answers were made apart.** The next revalidation must judge their combined state (COR-062 point 7), which the step cannot.

A person answers each on the release branch before the release merges, as for any change.

### 4. Who checks the release's answers

The answers are those the check asks of the change the release step makes. COR-050 point 3 lets whoever makes a change write them without asking first. The release pull request's reviewer, the person who merges it, checks each against the change, from the change check's list of the change's answers, as point 3 asks of a reviewer. Before it ends, the step runs the check again, and takes back any answer of its own that the check does not accept or flags as replacing answers made apart.

## Rationale

**Why the release step writes them.** The answer these documents need is a fact about the release's own writes, and the step that wrote them knows those writes exactly. Fourteen answers saying the same thing on every release teach the habit COR-050 point 7 warns of, a revalidation made without reading. Writing them at the release puts each answer where its change is made, as [PRJ-007](PRJ-007-release-maintains-self-host-manifest.md) puts the manifest's versions there.

**Why the reason is still a judgement checked.** COR-050 point 3 calls `unchanged-because` the one judgement the check cannot supply, and the check still supplies none. The step writes a reason only where the judgement comes down to facts it can check: which lines it rewrote, and that the document states none of the versions they held. What is left is whether a document depends on a version it never writes out, as in "before its first major release". That stays with the reviewer, who reads every answer.

**Why the test errs toward asking.** A version that stands in a document for any reason, such as a library's release named in an example, leaves the document to a person. Such a false alarm costs one answer by hand, as every answer cost before. A missed dependence costs a stale document, so the test never guesses that a stated version means something else.

**Why not deferred or apart.** A deferral and answers made apart each carry a judgement no one has made yet. A revalidation on them would claim it, so the step leaves them to the next person who answers.

### Alternatives considered

- **An anchor on a package file does not count the release's version lines.** Rejected: it changes what a path anchor stands on (COR-050 point 5), a core decision binding every project, for one project's release step. It would also leave a document that states a version unasked, unless a new form of anchor named the lines.
- **Documents anchor narrower parts of package metadata.** Rejected: a path anchor names no part of a file (COR-050 point 2), and the documents need the file for what it declares beside the versions.
- **The release answers every artefact it asks about.** Rejected: the reason would not hold for a document that states a version, and the answer would be the blind bump COR-050 point 3 guards against.
- **Answers stay by hand.** Rejected: each release pays a commit of answers whose words barely change, the cost that prompted this record.

## Implications

- **`pkit release apply`** gains the answer step, after its writes, and says which artefacts it answered and which it left, each with why. A release with nothing to answer, or a project whose friction functionality holds no artefact, writes no answer file.
- **The changeset guard** stays as it is: it already reads a release diff with answer files it adds as a release, and an answer file is no surface (COR-062 point 2).
- **The release README** says how a release's answers are made, and the release use cases say the release writes them.
- **A backbone changeset** declares the change to `pkit release apply`, a `patch`.
- **No accepted record is edited.** This record stands on PRJ-002 points D3 and D4, PRJ-007, COR-050 points 3, 4 and 5, and COR-062 points 1 and 7, all accepted.
