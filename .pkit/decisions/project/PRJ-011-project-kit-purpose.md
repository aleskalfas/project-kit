---
id: PRJ-011
title: project-kit exists so a way of working with AI agents is written once and kept current in every project that installs it
status: accepted
date: 2026-10-22
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A project that works with AI agents builds a way of working for them, such as how it records decisions and which rules its agents follow. Where each project builds it by hand, the same work is repeated in every project, the decision system included. Each version comes out different, and some work better than others. An improvement made in one project never reaches the others.

Work that recurs like this is worth carrying in something made once, and the methodology holds that as a principle of its own ([COR-007](../core/COR-007-pattern-extraction.md)). The [README](../../../README.md#why) tells adopters the same story. Yet no record says that this is what project-kit is for. This record does, so that what project-kit writes about itself can rest on one statement of it.

## Decision

**project-kit exists to write a way of working with AI agents once, as a methodology, and to keep it current in every project that installs it. A project installs the methodology like a dependency and upgrades it like one. So an improvement made once at the methodology's source reaches the shared part of every such project, at its first upgrade to a release that carries it.**

How this works is decided elsewhere:
- Each file in a project belongs either to the methodology or to the project, never to both ([the no-shared-files invariant](../README.md#the-no-shared-files-invariant)).
- The methodology's files reach a project and are kept current there ([COR-001](../core/COR-001-content-mechanisms.md)).
- A project stays at its version until it moves to another ([COR-059](../core/COR-059-version-transition.md)).

## Rationale

**Why spread one way of working, rather than improve each project's own.** Improving each project's setup on its own repeats the same work in every project. The results still diverge, and a lesson learned in one stays there. The way of working with AI agents recurs in every project that uses them, so it is worth making once ([COR-007](../core/COR-007-pattern-extraction.md)).

**Why a dependency, not a copy.** A way of working handed out as a template, or as a guide each project copies, gives every project the same start. From then on each copy is the project's own, mixed with its edits, so no later improvement can reach it. The core's own content faced the same choice: without propagation, it would be a scaffold applied once ([COR-001](../core/COR-001-content-mechanisms.md)). A dependency keeps the shared part apart from each project's own, at a version, so an upgrade can replace it.

**Why a project record.** Delivering a methodology as a dependency is a principle any project's methodology can hold, and the core's records already decide it ([COR-001](../core/COR-001-content-mechanisms.md), [COR-059](../core/COR-059-version-transition.md)). This record says why project-kit exists and whose problem it solves. A core record must hold for any project that adopts the methodology ([COR-014](../core/COR-014-universal-applicability.md)), and no adopting project needs this statement about project-kit. So it belongs with project-kit's own records.

## Implications

- **What project-kit writes about what it is for,** in its documents and its analysis, anchors this record rather than stating a purpose of its own. A change to this record then flags each of them.
