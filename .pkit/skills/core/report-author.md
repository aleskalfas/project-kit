---
name: report-author
description: Help a user compose and file a well-formed bug, change-request, or feedback report to the upstream project-kit repo via `pkit report`. Use when someone wants to report a problem or share feedback about pkit and would benefit from an agent drawing out a clear, actionable description.
metadata:
  wraps_command: pkit report
reads:
  records:
    - PRJ-008
    - ADR-047
  paths:
    - .pkit/cli/README.md
---

# Composing a report to project-kit

`pkit report` is the built-in adopter→project-kit feedback channel (per the report-command decision, PRJ-008; cross-repo realization ADR-047). It files a **bug** (something is broken), a **change-request** (a concrete desired change — templated: motivation / desired behaviour / current workaround), or **feedback** (an idea, friction, or rough edge) as an issue on the upstream project-kit repo — *not* the adopter's own tracker — with a redacted environment block attached automatically.

Your job with this skill is to turn a user's rough "this is annoying" or "X broke" into a report a maintainer can act on without a round-trip, then file it through the command. You are the formulation help — the user should not have to know how to write a good bug report.

## When to invoke this skill

- The user says something broke, is confusing, or could be better about pkit itself (the methodology tooling), and wants it reported upstream.
- The user asks to file feedback / a bug / a feature idea about pkit.
- A maintainer wants to file a report **on behalf of** someone who gave feedback informally (e.g. over chat).

Do **not** use this for issues in the *adopter's own* project — those go to the adopter's own tracker via the project-management capability. This channel is only for reporting about pkit upstream.

## 1. Pick the kind: bug vs change-request vs feedback

Decide with the user which shape fits — one question, not a form:

- **bug** — something behaves wrong, errors, or contradicts its documented behaviour. The reader needs to reproduce and fix it.
- **change-request** — a concrete desired change to behaviour or surface: the user can say what they want different and why. Structured (motivation / desired behaviour / current workaround); filed as `pkit report change-request …` (#639).
- **feedback** — a rough edge, a missing affordance, a confusing name, an idea too unshaped to be a change-request yet. There may be nothing "broken"; the value is the signal.

When unsure between change-request and feedback, ask whether the user can state the desired behaviour concretely — yes ⇒ change-request; otherwise default to **feedback** (no repro burden, easy to reclassify).

## 2. Draw out the description (one question at a time)

Interview the user to fill the gaps — ask the *single* most valuable missing thing per turn (per the one-decision-at-a-time discipline), not a questionnaire. Stop as soon as the report is actionable; don't over-interrogate.

For a **bug**, aim to capture:

- **What happened** — the observed behaviour, in the user's words.
- **What they expected** instead.
- **How to trigger it** — the command or action, and any preconditions. Even a rough "I ran `pkit sync` right after upgrading" is worth a lot.
- **When it started** — always, or after some change (an upgrade, a new capability)?

For **feedback**, aim to capture:

- **The friction or the idea** — what is clumsy, missing, or confusing.
- **The context** — what the user was trying to do when they hit it.
- **Why it matters** to them — the underlying need, so a maintainer can solve the real problem rather than the literal request.

You do **not** need to ask for versions, OS, or which capabilities are installed — the command attaches a redacted environment block automatically.

## 3. Redaction awareness

The environment block is redacted **by construction** — it carries pkit + capability versions, adapter, and OS/arch only; home paths are stripped and incubated (private) capability names are withheld unless `--include-private` is passed. You do not manage that.

What you **do** watch: the **prose you compose** is not redacted. Before filing, make sure the description carries no secrets, tokens, absolute home paths, or private repo/capability names the user wouldn't want in a public issue. If the user pasted something sensitive, paraphrase it out.

## 4. Draft the title and body, and confirm

- **Title** — a short, specific summary. "Bug: `pkit sync` overwrites a project-authored skill" beats "sync is broken".
- **Body** — the prose you drew out, organised (for a bug: what happened / expected / repro / when-started; for feedback: friction / context / why-it-matters). Tight prose, no ceremony.

Show the user the title and body before filing. This is their report under their identity.

## 5. File it

Invoke the command with the composed title and body:

```
pkit report bug --title "<title>" --body "<body>"
```

(or `pkit report feedback …`). Behaviour to convey to the user:

- **URL-first by default** — the command prints a prefilled GitHub new-issue URL. It works with **no `gh` auth**; opening it lands the user on the issue form with everything filled, and the **browser submit is the review gate**. This is the safe default.
- **`--file`** posts directly via `gh` (when authenticated), behind an interactive **target-naming confirm** ("posts a PUBLIC issue to `<owner/repo>` under your identity"). Use only when the user is ready to publish.
- **`--yes` / autonomy never auto-posts** — it degrades to the draft URL (the deliberate `--yes` asymmetry). Never try to force a post under automation; hand back the URL.

## 6. Filing on behalf of someone

If a maintainer is filing feedback someone gave them informally, add `--on-behalf-of @login`. The report is filed under the *invoker's* identity with a "Reported for @login" attribution — attribution, not authorship. The beneficiary can then track it: `pkit report` lists reports filed *for* them (marked `filed for you`), not only ones they authored.

## 7. After filing: tracking

Tell the user they can follow their report:

- `pkit report` — lists their reports (authored and attributed) with each one's state.
- `pkit report --tree` — the same, with the fixing issues (`## Tracked by`) nested under each.
- `pkit report show <N>` — one report's detail: the latest maintainer comment and the issues that will fix it, each with its state.

That closes the loop — the user reports once and watches it move, without leaving the CLI.
