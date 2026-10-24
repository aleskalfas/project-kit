---
id: DEC-057
title: project-management exists so a team runs its projects' work on GitHub by one rulebook, which agents carry out on a person's authority
status: accepted
date: 2026-10-24
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The capability's README tells an adopter when to install it. In its words, a team wants one rulebook for its work across several projects, not habits each project invents again. It wants AI agents to file, check and move its issues by that rulebook, and it works on GitHub.

Most of the capability's records decide one part of that rulebook, such as the hierarchy of issues or the states an issue moves through. The README's opening says what the capability does, but no record states what it is for. So whatever describes the capability, such as a page that introduces it or an analysis of it, has no reviewed statement of its purpose to anchor. This record gives one.

## Decision

**project-management exists to give a team one rulebook for the work of all its projects on GitHub, from planning an outcome to landing the changes that deliver it. Its rules are held as data, and its commands carry them out. So AI agents file, check and move the work by them, while a person authorises each step that commits the team, such as filing an EPIC, scheduling work or landing a change.**

This record decides no new behaviour. It states what the capability is for, from what its README and its records already say. How each part works is decided elsewhere:
- The rules describe mechanisms, and each project's values come from its own configuration. So one rulebook serves every project that installs the capability ([project-management:DEC-002-team-wide-generic-scope]).
- An EPIC states an outcome, and the work that delivers it is filed under it ([project-management:DEC-004-six-level-hierarchy]).
- The rules run as commands that read the schemas, in place of an agent's reading of prose ([project-management:DEC-020-methodology-as-executable-commands]).
- The capability's agent files and moves the work on a person's direction, and only a person in the PM role has an EPIC filed ([project-management:DEC-008-pm-and-implementer-roles]).
- A person schedules work, and authorises each close and each landing. The agent moves the work in between ([project-management:DEC-006-state-machine-and-cascade]).
- Reviewers' verdicts gate the merge ([project-management:DEC-027-review-modes]), and the authorisation to merge stays the person's ([project-management:DEC-055-pr-lists-answers]).
- The rules name GitHub's primitives directly, such as issues, sub-issues and Milestones ([project-management:DEC-003-github-bound-substrate]).

## Rationale

**Why one rulebook, rather than each project's own habits.** Rules each project invents again diverge, and an improvement made in one never reaches the others. Every project installs one shared capability, whose content holds mechanisms and leaves values to the project, so the rules stay the same in each ([project-management:DEC-002-team-wide-generic-scope]). Held as schemas that commands read, the rules are enforced by the commands, rather than by an agent's reading of prose ([project-management:DEC-020-methodology-as-executable-commands]).

**Why agents carry it out, and a person authorises.** With an agent doing the filing and the moving, no person has to become "the one who types", and anyone can direct the agent ([project-management:DEC-008-pm-and-implementer-roles]). Only a person commits the team: to an outcome, to scheduled work, and to a change that lands ([project-management:DEC-008-pm-and-implementer-roles], [project-management:DEC-006-state-machine-and-cascade] and [project-management:DEC-055-pr-lists-answers]). So the agent does the work in between, and the person holds both ends.

**Why GitHub.** Every project the rulebook targeted when it was written lived on GitHub, and GitHub's own primitives carry much of it ([project-management:DEC-003-github-bound-substrate]). Naming the purpose in GitHub's terms says plainly whom the capability serves.

**Why a record of the capability's own.** The statement concerns this capability alone, and it ships with it. So it belongs among the capability's records, not with any one project's.

## Implications

- **Whatever describes the capability's purpose,** such as an analysis of it, can anchor this record instead of stating a purpose of its own. A change to this record then flags each such description.
