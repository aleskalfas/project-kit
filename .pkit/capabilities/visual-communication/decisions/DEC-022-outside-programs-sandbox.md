---
id: DEC-022
title: An outside program keeps its own sandbox, and the capability asks the permission model for no grant and no way out
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** some commands of the capability start a program of another tool, such as a browser. Such a program runs where the command that starts it runs, and keeps its own sandbox on. For it, the capability asks the permission model for no grant inside the session's sandbox, and opens no way out of that sandbox. So an agent whose commands run in that sandbox does not see the HTML renderer's page. It gets the page file, and the SVG renderer's images of the same scene. A run on one Mac showed why, in a stand-in for the harness's sandbox. There the browser stopped at once, and the system refuses a sandbox inside a sandbox. It drew only with its own sandbox off, in a sandbox opened past the harness's. Where a sandbox stops the program, the command stops, says why, and names a person's ways on. The same holds for a program a producer calls.

## Context

[project-kit#2775](https://github.com/aleskalfas/project-kit/issues/2775) asks what the permission model adds for an outside program the capability starts, a browser first (COR-028). It hoped an agent working in a sandbox would then see the page a reader gets. Until this is settled, the viewing step leaves alone the sandbox the browser sets on its own parts ([visual-communication:DEC-020-html-page-drawing] point 8). The first real producer takes the same answer for the programs it calls ([visual-communication:DEC-006-work-outside-the-engine-and-outputs], Implications).

Three terms:
- An *outside program* is a program of another tool that a command of the capability starts, such as a browser ([visual-communication:DEC-002-files-and-validation] point 8).
- The *box* is the sandbox the harness gives a session, which the permission model manages. The operating system holds each command of the session's shell to the files and hosts the box allows ([pkit:ADR-004] point 2).
- A program's *own sandbox* is the one it sets on its own parts. A browser sets one on the processes that read a page.

### The permission model today

- **One box for the session.** What it allows one command, it allows every command of the session (ADR-004 point 5).
- **Two kinds of allowance.** A *narrowing* one makes the box usable and widens no reach, such as a cache folder to write. A *widening* one lowers the boundary ([pkit:ADR-008] point 1). The model's schema for confinement toolkits has kinds for paths, sockets and hosts, and none for a system service.
- **Two ways out of the box.**
  - A *widening* runs a command outside it. A person applies one only by a gesture of their own, on one machine, never in a committed file (ADR-008 point 4). The model applies one itself only where the platform requires it, once it has checked the need ([pkit:ADR-027]). It reports each.
  - The *harness's escape* reruns one command outside the box, a separate key on a separate layer ([pkit:ADR-028] point 3). The *autonomy posture*, the model's setting for unattended work, seals it. Outside that posture it stays open, as a person's stopgap (ADR-028 point 5).
- **On macOS, `uv` runs outside.** The platform requires it, so the model excludes `uv` ([pkit:ADR-014] point 2). A command run as `uv run pkit` runs outside with it, and `pkit` typed alone does not, as the model's toolkit for `uv` notes. Once a fixed `uv` ships, `uv` runs inside again (ADR-014 point 4).
- **Agent runs.** A confined agent run takes that exclusion of `uv` too ([pkit:ADR-066] point 6). A builder's run takes no exclusion. On macOS, one that needs `uv` is refused while `uv` cannot run in the box ([pkit:ADR-073] point 3).

### What the run showed

The run used one Mac, macOS 26.6.2, Chrome 157, and Claude Code 2.1.319 as the harness. Each plain run drew a small page of text over SVG shapes, which asks an outside host for one picture. Chrome was started as the viewing step starts it: headless, with a throwaway profile. The module that draws a page file through a browser then drew its own planted page ([project-kit#2784](https://github.com/aleskalfas/project-kit/issues/2784), at its branch's head, `77dc7695`).

**A stand-in for the box.** The session's own box was off: the project's settings leave it so, and its shell reached an outside host. The harness refused this session a run of its sandbox runtime alone, as code from outside. So the box was the harness's macOS profile, reassembled by hand from the text the harness carries. It took the project's settings: its folders to write, its paths denied to reads, and one host through the harness's proxy. It stands in for a run in a session's box, and does not replace one.

| Where it ran | Its own sandbox | What it did |
|---|---|---|
| No box | On | Drew in 1.1 s. The module started it once, named each planted fault, and drew its page, in 4.6 to 6.3 s |
| No box | Off | Drew the same bytes, in 0.9 s |
| The box | On, or off | Stopped within 0.3 s. The box refused the folder for the socket that keeps one browser to a profile. Chrome on macOS puts it in the system's temporary folder, whatever `TMPDIR` says |
| The box, granting that folder | On | Stopped in 0.2 s, when the box refused that socket |
| The box, granting the folder, its socket and the services refused | On | Crashed in 0.4 s on a check, after more services and system values were refused |
| The box, granting every service and system value at once | On | Its parts could not start their own sandbox, since the system refuses a second sandbox to a sandboxed process. It crashed in 5 s |
| The same | Off | Drew the same bytes as with no box, in 1.0 s. The box refused its requests to outside hosts |

- **The module in the box.** It stopped before the browser started: the box refused the way the module hands the browser its pipes. With that granted, it stopped where the browser did. Its stop did not say that a sandbox stopped it.
- **What reached the network, with no box.** In the plain runs, the page's own request went out. The module refused both requests its planted page makes. In every run, the browser also reached two of its maker's hosts on its own, despite its flags against background requests.
- **What the browser wrote, with no box.** Its profile, some 220 files, in the folder given. A lock folder and a copy of itself in the system's temporary folder, both removed at a clean exit. Its crash database's settings, in the person's own Chrome folder, where a crash writes its dumps too. The box refused the copy and the crash database.
- **What it left.** No process. The two runs that crashed each left the lock folder, with a socket and a link. No clean run left one.
- **`uv` in the box.** `uv` 0.13.0 ran one command inside the reassembled box, past the denial that made 0.9.8 panic (ADR-014, Context).

**Not reached:** a session whose box is on, and the harness's sandbox runtime run alone. Linux and its box: the harness's text says that box turns off user namespaces where it can, and Chrome's own sandbox needs them. That was read, not run, as was Chrome on Linux refusing to run as root with its own sandbox on. A producer's browser, Chromium, Playwright's builds, and a second Mac.

## Decision

**The capability asks the permission model for no grant and no way out for an outside program it starts. The program runs where the command that starts it runs, and keeps its own sandbox on. Where the box stops such a program, the command gets no drawing from it: it stops, says why, and names a person's ways on. A producer's outside program is held the same way.**

### 1. The capability asks the permission model for no grant and no way out

- **No widening.** The capability asks the model for no allowance that widens reach on the program's behalf, and ships none.
- **No narrowing yet.** It ships no narrowing allowance either. A later record may add one for a program a run shows to need it, as a toolkit the capability ships ([pkit:ADR-015]). No narrowing set serves the browser (Rationale).
- **No way out.** No command of the capability runs itself or its program outside the box, and none asks the model to. Nor does it start the program through the system's launcher, or hand work to a copy already running.
- **The program runs where its command runs.** It takes the box of the command that starts it, or none. The model's own rules decide that, and the capability decides nothing of the box.

### 2. Outside the box, the capability asks for nothing more

- **With no box,** the program runs as the person's own. Nothing needs granting.
- **A person's ways out.** A person may run the command outside the box, by the model's widening for that command (ADR-008 point 4). Where the autonomy posture leaves the harness's escape open, a person may confirm its use for the command (ADR-028 point 5).
- **An agent asks, and never decides.** An agent takes neither way out on its own, and asks the person first. It runs the command in the form the project uses, and never changes that form to reach an exclusion.
- **Under an exclusion the model applies.** Where the model already runs the command outside the box, as it runs `uv` on macOS, the program runs outside with it (point 1). That is the model's way out, not one this record opens. Whether it should carry a browser is the model's to judge (Implications).
- **No report of which.** The capability cannot tell a command the model excluded from one run with no box. So the step's report does not say which held the browser.
- **What that leaves open.** Outside the box, only its own sandbox and the rules on its command hold the program. The model reports the command's exclusion, never the program it starts. A browser also reaches its maker's hosts, and writes in the person's own browser folder (Context).
- **A program may still not run.** Chrome run as root refuses to start with its own sandbox on, as a container may run it (Context). Point 4 holds there too.

### 3. The program keeps its own sandbox on

- **Never off.** The capability passes no flag that turns off or weakens the sandbox of any of the program's processes, or merges them into one. It passes none its maker marks unsafe, and none that lets a page read past its own file. Its configuration has no setting for one.
- **A program a project names** is started as named, from a file the project reviews (DEC-020 point 7). What that program does is the project's own choice.
- **What it holds.** A browser reads files the project did not all write: a brand's faces, a producer's pictures, a piece's words. Its own sandbox keeps a fault in reading them inside the part that read them.
- **What off would open, outside the box.** Such a fault would act with the rights of the process that started the browser. Those are the person's: their files, their keys and their network.
- **And inside it.** It would act with the box's rights, which reach the clone. It could write a hook or a setting that a later command runs outside the box.
- **No box stands in for it.** On macOS, the system refuses a sandboxed browser a sandbox of its own (Context). So inside the box, the browser draws only with its own sandbox off.

### 4. Where a sandbox stops the program, the command stops and says why

- **Nothing partial.** The command keeps no output of the program's run. The viewing step leaves its page file and a report, and no image (DEC-020 point 8).
- **What it says.** It names the program and what the program said (DEC-020 point 8). Where the program's words show a sandbox, it says that a sandbox stopped the program.
- **The ways on.** It names the same work without the program, where there is one, such as the SVG renderer. It also names a person's two ways out of point 2: the model's widening, and the harness's escape where it stays open. It never names an exclusion as a way on.

### 5. A producer's outside program is held the same way

- **Points 1 to 4 hold** for each outside program a producer calls, such as a browser that draws a 3D scene. A producer runs through a command of the capability (DEC-006 point 1).
- **No host.** Drawing needs no network (DEC-002 point 8), so the box needs to allow such a program none. That binds the outside program, not a service a producer declares under DEC-002 point 8.
- **Over a pipe, never a port.** The program is driven over a pipe, never over a port that listens, since any process on the machine can reach a port.
- **Its inputs are handed to it,** as files its driver serves over that pipe, or as `data:` addresses. So no page reads past its own file (point 3).
- **In the box, the picture waits.** A picture whose program cannot run there is not made again. While stale, it asks for attention ([visual-communication:DEC-006-work-outside-the-engine-and-outputs] point 8), and an export stops on it (DEC-006 point 7). A person makes it outside the box.
- **Not this record's to close.** Whether a producer's command is one the platform requires outside the box is the permission model's question, at its own bar of evidence (ADR-027).
- **A helper is the project's.** A helper runs as the project's own script, under the project's own permission model (DEC-006 point 1). So this record does not bind what a helper starts.

## Rationale

**Why the capability asks the model for nothing.** The box serves the whole session, so an allowance for one program reaches every command (ADR-004 point 5). On macOS the browser asked first for a socket in the person's temporary folder, then for more of the system's services than the box names. Even with every one granted, it could not keep its own sandbox. So no allowance serves the browser under point 3. For another program the need is unknown, so the record waits for a run that shows one.

**Why the program's own sandbox stays on.** It is the layer that holds a fault in reading a face or a picture. Outside the box it is the only layer. Inside the box on macOS, the browser runs only with it off, in a box opened past what the harness allows. That trade loses two layers for one image.

**Why the ways on are a person's.** The model keeps each way out of the box a person's, or its own where the platform requires one. A second way, owned by a capability, would split that decision. So the stop names only a person's ways, never the model's exclusion. A build in the box still has the page file and the SVG renderer's images (DEC-020 point 8).

**Why one rule for the step and for producers.** Both start an outside program from a command of the capability, under the same box, and both read files the project did not all write. A producer has no other way to make its picture, so the record leaves the model free to judge its command (point 5). No producer's browser was run, so its own test may find that point 3 cannot hold for it.

**The cost.** An agent whose step runs in the box never sees the HTML renderer's page, which #2775 hoped it would. A builder's run is one, since it takes no exclusion (ADR-073 point 3). By the harness's text, so is a session on Linux whose box is on, read and not run (Context). The page draws where the step's command runs outside the box. That is a person's terminal, a session with no box, or a command the model excludes. Which commands the model excludes is its own to say, and changes as `uv` does (ADR-014 point 4). A producer's picture waits in the same places, until a person makes it (point 5).

### Alternatives considered

- **A set of allowances for the browser, which the model's setup applies.** Rejected. No narrowing set lets the browser keep its own sandbox in the box.
- **An exclusion of the step's command that the model requires and applies, as it does for `uv`.** Not asked of the model. Which commands join that class is the model's to decide, in a record of its own, as [pkit:ADR-030] added `gh`. Its test asks for a small reach. Outside the box, a browser reaches its maker's hosts and the person's browser folder (ADR-030 point 5).
- **A refusal to draw where only an exclusion for another program carries the command out of the box.** Not taken. The capability cannot tell such a command from one run with no box. The exclusion's reach is the model's to judge, and an issue asks it (Implications).
- **The browser's own sandbox off, where a project's configuration says the session runs in a box.** Rejected. On macOS the box would still need opening past what the harness allows. A fault would also reach the clone (point 3).
- **A drawing service a person starts outside the box, which reads page files from the workspace.** Rejected. It listens on a port any process can reach, and it is a way out of the box the model does not see.
- **Playwright's headless shell.** Not taken. In the test behind DEC-020, it stopped on its own sandbox inside a box, and drew only with that sandbox off.

## Implications

- **Edits to accepted records,** made once this record is accepted, each citing it. Accepting this record accepts them (COR-066 point 5). The edit to DEC-020 point 8 narrows a promise, from "the step says so" to where the browser's words show a sandbox:
  - **DEC-020's plain terms, "a build in a sandbox cannot see such a page yet".** It comes to say that such a build does not see the page, as this record decides.
  - **DEC-020 point 8, "A sandbox may stop the browser."** It comes to say that the step never turns off the browser's own sandbox. The step says a sandbox stopped the browser where the browser's words show one, and otherwise names what it said. Its stop names a person's ways on, of this record's point 4, beside the SVG renderer. The clause on #2775 and the sentence "That Task lies in version 1 of the capability" go.
  - **DEC-020 point 8, "That leaves a build in a sandbox."** Its last sentence comes to say that the browser's look falls to a session whose step runs outside the sandbox.
  - **DEC-020's Revisit** loses its item on #2775 settling what the permission model adds.
  - **DEC-015 point 2, "The browser."** Its last sentence comes to say that the capability asks the permission model for no grant and no way out for such a program. The program keeps its own sandbox on.
  - **DEC-006 point 1, "Who starts it."** It gains a sentence: what a sandbox grants a producer's outside program is decided in this record.
  - **DEC-006's Implications, the bullet on the first real producer.** Its last sentence comes to say that this record decides what holds for the outside programs a producer or the viewing step calls.
  - **DEC-002 point 8, "Outside programs on the path that needs them."** It gains a sentence: what a sandbox grants such a program is decided in this record.
- **The module that draws a page file through a browser** (#2784) settles what the run found:
  - In a session whose box is on, it checks the way it hands the browser its pipes.
  - Its stop says that a sandbox stopped the browser from the browser's words. The words this run gave were a refused folder for the socket, and a sandbox that could not start. Asking the system instead would be a facility of the backbone or the adapter, not the capability's own code.
- **The Task that builds the step's browser half** ([project-kit#2785](https://github.com/aleskalfas/project-kit/issues/2785)) names the ways on in its stop (point 4). The capability's README and its reference on outputs follow there.
- **The first real producer** ([project-kit#2575](https://github.com/aleskalfas/project-kit/issues/2575)) takes points 1 to 5 as decided. Three things follow for it:
  - A driver that starts Chromium with its sandbox off by default, as Playwright does, must turn it on. One that speaks over a port by default, as Puppeteer does, must take its pipe.
  - Its tests that start a real browser stop inside a builder's run and its checks ([pkit:ADR-073] point 5). They skip there with a stated reason, or need no browser.
  - Whether its command should be one the platform requires outside the box is a question for the permission model (point 5).
- **An issue of its own carries two findings to the permission model's maintainers:**
  - `uv` 0.13.0 ran one command in the reassembled box. Whether it is the fixed release ADR-014 point 4 waits for is theirs to check (ADR-027 point 1).
  - On macOS, a browser that `uv run pkit` starts runs outside the box under the exclusion of `uv`. So it does in a confined agent run (ADR-066 point 6). It reaches its maker's hosts and writes in the person's browser folder, and no report names it.
- **Revisit this record:**
  - if a session whose box is on, or the harness's sandbox runtime alone, shows otherwise than the stand-in
  - if a run on Linux finds a box that holds the browser with its own sandbox on
  - if a producer's program cannot draw with its own sandbox on
  - if the model gains an allowance that lets the browser keep its own sandbox in the box
  - if a harness lets a sandboxed process start a sandbox of its own
