---
id: DEC-024
title: An outside program keeps its own sandbox on, and leaves the session's sandbox only with the command that starts it
status: proposed
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** some commands of the capability start a program of another tool, such as a browser. Such a program keeps its own sandbox on, where it has one. The browser cannot run that way inside the sandbox the harness gives a session. So a look that needs it runs outside, through the narrowest opening the permission model has: an exclusion of the one viewing command, which a person applies on their own machine. The capability names it only where a test shows the harness holds it to that command. The whole command then runs outside. A command inside the sandbox can change what the look runs, so on that machine it can get code run outside the sandbox. The page reaches no network. Where no browser can run, the look stops, says why, and names the ways on: a run outside the sandbox, a build pipeline's drawings, and the SVG renderer's pages. A program a producer calls follows the same rules.

## Context

[project-kit#2775](https://github.com/aleskalfas/project-kit/issues/2775) asks what the permission model adds for an outside program the capability starts, a browser first (COR-028). It hoped an agent working in a sandbox would then see the page a reader gets. The viewing step stops where a sandbox stops the browser ([visual-communication:DEC-020-html-page-drawing] point 8). The first real producer takes the same answer for the programs it calls ([visual-communication:DEC-006-work-outside-the-engine-and-outputs], Implications).

Six terms:
- An *outside program* is a program of another tool that a command of the capability starts, such as a browser ([visual-communication:DEC-002-files-and-validation] point 8).
- A *look* is one run of the viewing step's command, `pkit visual look` ([visual-communication:DEC-015-viewing-step-and-reviewer] point 1). It is no visual style here.
- The *box* is the sandbox the harness gives a session, which the permission model manages. The operating system holds each command of the session's shell to the files the box allows ([pkit:ADR-004] point 2). Its list of hosts bounds only a well-behaved program, and is no security boundary ([pkit:ADR-015], Context).
- A program's *own sandbox* is the one it sets on its own parts. A browser sets one on the processes that read a page.
- An *exclusion* lets one command, and all it starts, run outside the box ([pkit:ADR-008] point 4).
- The *autonomy posture* is the model's setting for unattended work ([pkit:ADR-028]).

### The permission model, as its records state it

- **One box for the session.** What it allows one command, it allows every command of the session, an exclusion aside (ADR-004 point 5; ADR-015, Context).
- **Two kinds of allowance.** A *narrowing* one makes the box usable and widens no reach, such as a cache folder to write. A *widening* one lowers the boundary (ADR-008 point 1).
- **The exclusion is the one widening for a command.** A person applies it on one machine with `pkit permissions sandbox exclude`. It lands in that machine's own settings, never in a committed file, and the model reports it (ADR-008 point 4). It names a command by its opening words, as an agent run's excluded commands are named (the Claude Code adapter's README).
- **Confinement toolkits.** A toolkit is data: the allowances one tool needs in the box, each marked narrowing or widening (ADR-008 point 1). The model ships some, and a project may add its own. A capability ships its own as a fragment (ADR-015), and the model has no read of one ([pkit:ADR-016] point 5).
- **Exclusions the model applies itself.** It applies one only where the platform requires it, once it has checked the need ([pkit:ADR-027], [pkit:ADR-030]). A command joins that set by a record of the model's, past a test of three parts (ADR-030 point 5).
- **The harness's escape** reruns any one command outside the box, a separate key on a separate layer. The autonomy posture seals it, and elsewhere it stays a person's stopgap ([pkit:ADR-028] points 3 and 5).
- **On macOS, the model keeps the box off.** Its command that turns the box on leaves it off there, and says why. In June 2026, version 2.1.193 of the harness ran excluded commands inside the box all the same ([project-kit#312](https://github.com/aleskalfas/project-kit/issues/312)). Where the model excludes `uv`, a command run as `uv run pkit` runs outside with it ([pkit:ADR-014] point 2).
- **Agent runs.** A confined agent run excludes only the commands that start `uv`, on macOS, while `uv` needs it ([pkit:ADR-066] point 6). A builder's run takes no exclusion, and a build that needs one the platform requires is refused at its start ([pkit:ADR-073] point 3).

### What the run showed

The run used one Mac, macOS 26.6.2, Chrome 157, and Claude Code 2.1.319 as the harness. Each plain run drew a small page of text over SVG shapes, which asks an outside host for one picture. Chrome was started as the viewing step starts it: headless, with a throwaway profile. The module that draws a page file through a browser then drew its own planted page ([project-kit#2784](https://github.com/aleskalfas/project-kit/issues/2784), at its branch's head, `77dc7695`).

**A stand-in for the box.** The session's own box was off: the project's settings leave it so, and its shell reached an outside host. The harness refused this session a run of its sandbox runtime alone, as code from outside. So the box was the harness's macOS profile, reassembled by hand from the text the harness carries. It took the project's settings: its folders to write, its paths denied to reads, and one host through the harness's proxy. It stands in for a run in a session's box, and does not replace one. A run in a session whose box is on is still to confirm it, in the opening's Task (Implications).

| Where it ran | Its own sandbox | What it did |
|---|---|---|
| No box | On | Drew in 1.1 s. The module started it once, named each planted fault, and drew its page, in 4.6 to 6.3 s |
| No box | Off | Drew the same bytes, in 0.9 s |
| The box | On, or off | Stopped within 0.3 s. The box refused the folder for the socket that keeps one browser to a profile. Chrome on macOS puts it in the system's temporary folder, whatever `TMPDIR` says |
| The box, granting that folder | On | Stopped in 0.2 s, when the box refused that socket |
| The box, granting the folder, its socket and the services refused | On | Crashed in 0.4 s on a check, after more services and system values were refused |
| The box, granting every service and system value at once | On | Its parts could not start their own sandbox, since the system refuses a second sandbox to a sandboxed process. It crashed in 5 s |
| The same | Off | Drew the same bytes as with no box, in 1.0 s. The box refused its requests to outside hosts |

- **The module in the box.** It stopped before the browser started: the box refused the way the module hands the browser its pipes. With that granted, it stopped where the browser did.
- **What reached the network, with no box.** In the plain runs, the page's own request went out. The module refused both requests its planted page makes. In every run, the browser also reached two of its maker's hosts on its own, despite its flags against background requests.
- **What the browser wrote, with no box.** Its profile, some 220 files, in the folder given. A lock folder and a copy of itself in the system's temporary folder, both removed at a clean exit. Its crash database's settings, in the person's own Chrome folder, where a crash writes its dumps too.
- **What it left.** No process. The two runs that crashed each left the lock folder, with a socket and a link. No clean run left one.
- **`uv` in the box.** `uv` 0.13.0 ran one command inside the reassembled box, past the denial that made 0.9.8 panic (ADR-014, Context). #312 found the same in the harness's own box, at version 2.1.193 of the harness.
- **On a pipeline's Linux runner,** the module's tests started a real Chrome, with no box, while #2784 was built.

**Not reached:** a session whose box is on, the harness's sandbox runtime run alone, and whether version 2.1.319 honours an exclusion. Linux and its box: the harness's text says that box turns off user namespaces where it can, and Chrome's own sandbox needs them. That was read, not run, as was Chrome on Linux refusing to run as root with its own sandbox on. A producer's browser, Chromium, Playwright's builds, and a second Mac.

## Decision

**An outside program the capability starts keeps its own sandbox on. Where the box stops it, the capability's way out is an exclusion of the command that starts it, which a person applies. The capability names that exclusion only where a test shows the harness holds it to that command. The page reaches no network. Where no browser can run, a look stops, says why, and names the ways on. Every other outside program is held the same way.**

### 1. The program keeps its own sandbox on

- **Never off.** The capability passes no flag that turns off or weakens the sandbox of any of the program's processes, or merges them into one. It passes none its maker marks unsafe, and none that lets a page read past its own file. Its configuration has no setting for one.
- **A program a project names** is started as named, from a file the project reviews (DEC-020 point 7). What that program does is the project's own choice.
- **What it holds.** A browser reads files the project did not all write: a brand's faces, a producer's pictures, a piece's words. Its own sandbox keeps a fault in reading them inside the part that read them.
- **Outside the box, it is the only layer.** Turned off there, such a fault would act with the person's rights: their files, their keys and their network.

### 2. Where a look needs the browser, its command may run outside the box

- **The opening.** It is an exclusion of the viewing command from the box, in each form the methodology documents for it, such as `pkit visual look`.
- **Named only where the harness holds it.** The capability names the exclusion only once a test shows two things. The harness runs the viewing command outside the box in each such form, and runs no other command outside under it. Otherwise a look's stop names only the other ways on of point 4.
- **Named by the capability.** Where it is named, the capability names the exclusion in a look's stop and in its pages, with the model's command that applies it.
- **Before the model's answer.** The model leaves an exclusion's reach to the person who applies it (ADR-008 point 4). So the capability may name its exclusion before the model answers what such a reach means for its own exclusions (Implications). The stop says what the exclusion lets out. Once the model reads a capability's toolkit (ADR-016 point 5), the capability declares it there too, marked widening, with what it lets out (ADR-008 points 1 and 6).
- **Applied by a person.** A person applies it on one machine, since it is a widening (ADR-008 point 4). Applying it accepts the reach below, on that machine. Where no adapter of the harness realises an exclusion, the other ways on of point 4 stand.
- **The whole command runs outside, with all it starts.** That includes everything the command reads as code or configuration from a folder the box writes. Examples:
  - the backbone's and the capability's scripts, and the project's configuration, which names the browser, in the clone
  - the files `uv run` reads there, such as the project's own package and its lock
  - on Linux, `uv`'s cache, which holds the environment the look's script runs in, and which the box writes for `uv`
  - a folder on the path `uv run` sets, the project's environment first
- **So the opening reaches past the command.** On a machine where it stands, the box no longer bounds a command that can write those files. That command can change what the next look runs outside the box. Under the autonomy posture, that look runs with no prompt. The permission hook judges the command's words, never what the command runs. So for any command that can write the clone, the exclusion reopens what the autonomy posture seals (ADR-028).
- **No argument chooses what runs.** No argument of the viewing command names code or configuration for it to run, as no flag names a browser (DEC-020 point 7).
- **No browser found on the command path inside the clone.** Where the step looks for a browser by name on the command path, it skips the folders inside the clone, such as the project's environment. That is defence in depth only, since the scripts themselves can be written.
- **Every run of the command.** The exclusion covers each run of the viewing command, including one of the SVG renderer's pages, which needs no browser.
- **What the browser reaches outside.** There the box's limits on hosts and folders do not hold. The browser reached two of its maker's hosts on its own, despite its flags. It wrote its crash database's settings in the person's own browser folder (Context).
- **No other way out.** No command of the capability asks for the harness's escape, which reruns any command outside the box (ADR-028). None starts the program through the system's launcher, or hands work to a copy already running.
- **The model's own way out.** Where the model already runs the command outside, as under its exclusion of `uv` on macOS, the program runs outside with it. That is the model's way out, not this record's.
- **No report of which.** The step cannot tell a run under an exclusion from one with no box. So its report does not say whether a box held the browser. The model's own report names each exclusion.

### 3. The page reaches no network

- **Every request refused.** The step refuses each request but the page file's own and a `data:` address, and names it (DEC-020 point 6). That holds inside the box and outside it.
- **Over a pipe, never a port.** The program is driven over a pipe, never over a port that listens, since any process on the machine can reach a port.

### 4. Where no browser can run, a look stops and names the ways on

- **Nothing partial.** The step keeps no output of the program's run. It leaves its page file and a report, and no image (DEC-020 point 8).
- **What it says.** It names the program and what the program said (DEC-020 point 8). Where the program's words show a sandbox, it says that a sandbox stopped the program.
- **The ways on.** It names these:
  - the same look, run outside the box: a single time in a person's own terminal, or under the exclusion of point 2 where point 2 names it. The stop then gives the command that applies the exclusion, addressed to a person, with one line on what it lets out.
  - a build pipeline's drawings, where the project's pipeline runs the look on a runner with a browser. The stop names them as a way a project may take, with no setting to say whether it does. They show a pushed commit, not the working tree.
  - the SVG renderer's pages, which show the layout, never this page
- **Never named.** The stop never names the harness's escape. Nor does it name any exclusion wider than the viewing command that would carry the look out, such as of `pkit`, or the model's exclusion of `uv` on macOS.
- **A browser that refuses its own sandbox.** Chrome run as root refuses to start with its own sandbox on, as a container may run it (Context). The step tells this apart from a sandbox that stopped it. It says so, and leaves out the exclusion, which does not help there.

### 5. An agent asks, and never opens the way itself

- **The person decides.** An agent never applies the exclusion, and never reaches for the harness's escape for a look. Where a look stops on a sandbox, it asks the person, naming the ways on of point 4.
- **The command as the project writes it.** An agent runs the command in the form the project uses. It never changes that form to reach an exclusion, such as `uv run` where the model excludes `uv`.
- **What holds it.** Only this rule, where an agent reads it: in the look's stop, and in the capability's skill that guides building a piece. The capability's reviewer, reading a folder a stop left, passes the ways on to whoever asked it. No deny of the model's stops an agent from running the command that applies an exclusion. Whether the box lets a command write the settings it lands in is the harness's. The model's report shows an exclusion once it is applied.
- **An agent run the model confines** takes only the exclusions the model's own rules give it (ADR-066 point 6, ADR-073 point 3). Where its look stops, the pipeline's drawings and the SVG renderer's pages remain.

### 6. Every other outside program is held the same way

- **Points 1 to 5 hold** for each outside program another command starts, such as a program that writes a PDF, or one a producer calls to draw a 3D scene. A producer runs through a command of the capability (DEC-006 point 1).
- **Its own opening.** Its opening is an exclusion of its own command, named and applied as point 2 says. The capability names it only once a run shows the box stops that program.
- **None for a program with no sandbox of its own.** Outside the box nothing would hold a fault in what such a program reads. So the capability names no exclusion for its command.
- **No host for what it is handed.** Drawing needs no network (DEC-002 point 8), so nothing the command hands the program reaches one, as point 3 holds for the page. Outside the box, nothing holds the program's own requests, which its own run reports, as the opening's Task does the browser's. That binds the outside program, not a service a producer declares under DEC-002 point 8.
- **Only what it is handed.** The program reads only the inputs its command hands it, such as files its driver serves over the pipe, or `data:` addresses (point 3, DEC-020 point 6).
- **Where it cannot run, the picture waits.** A picture whose program cannot run is not made there. Where it never ran, the piece has no picture yet. A stale one asks for attention while stale (DEC-006 point 8), and an export stops on it (DEC-006 point 7). A person makes it where the program runs.
- **A helper is the project's.** A helper runs as the project's own script, under the project's own permission model (DEC-006 point 1). So this record does not bind what a helper starts.

## Rationale

**Why the browser runs outside the box, and the box is not widened for it.** The box serves the whole session, so an allowance for one program reaches every command (ADR-004 point 5). In the stand-in, the browser asked first for a socket in the system's temporary folder. It then asked for more of the system's services than the box names. Even with every one granted, it could not start its own sandbox, since macOS refuses a sandbox inside a sandbox. So no allowance in the box serves a browser that keeps its own sandbox on. Outside the box, it drew at once with its own sandbox on. These runs were on macOS, where the model keeps the box off (Context). On Linux, where the box is on, the harness's text gives another cause, which was read, not run.

**Why the exclusion of one command.** It is the model's one way to let a single command out. Every other command still runs in the box, though one that can write the clone can change what the look runs (point 2). The model keeps the exclusion on one machine and reports it, and a person can take it back. The harness's escape lets any command out directly, and the autonomy posture seals it.

**Why the capability names it, and a person applies it.** The model keeps each widening a person's, or its own where the platform requires one (ADR-008 point 4, ADR-027). A capability that applied its own would split that decision. Named in the stop and the pages, and later in a toolkit, it is shown with what it lets out before a person applies it. A toolkit waits for the model, since a read of a capability's toolkit is the model's to build.

**Why the browser's own sandbox stays on.** It is the layer that holds a fault in reading a face or a picture. Outside the box it is the only layer, and Chrome's makers advise against running without it.

**Why a build pipeline is the backup.** A hosted pipeline's Linux runner runs a real Chrome with no session's box around it, as the module's tests found (Context). So a session that cannot draw the page can read the pipeline's drawings of a pushed commit.

**Why one rule for every outside program.** Each starts from a command of the capability, under the same box, and reads files the project did not all write. No producer's browser was run, so its own test may find that point 1 cannot hold for it.

**The cost.** On a machine where the opening stands, a command that can write the clone can get code run outside the box, under the autonomy posture with no prompt (point 2). Outside the box, the browser reaches its maker's hosts and the person's browser folder. Once the exclusion is applied, a look of the SVG renderer's pages runs outside too. An agent run the model confines, a builder's among them, gets no opening (ADR-073 point 3). The harness may also ignore the exclusion, as version 2.1.193 did (#312). Until the opening's Task shows otherwise, a session in the box gets the pipeline's drawings and the SVG renderer's pages.

### Alternatives considered

- **The capability asks for nothing, so an agent in the box never sees the page.** Rejected by whoever maintains the capability. The capability should let the browser run where a look needs it, and that must be possible to do and to test.
- **The browser's own sandbox off, inside the box.** Rejected by whoever maintains the capability. In the stand-in it drew only in a box opened past what the harness allows, and Chrome's makers advise against it. A fault would act with the box's rights, which reach the clone.
- **A container or a virtual machine for each run.** Rejected by whoever maintains the capability. Starting one needs Docker let out of the box too, the widening with the largest reach the model names (ADR-030 point 5).
- **A set of narrowing allowances for the browser.** Rejected. None lets the browser keep its own sandbox in the box (Context).
- **The harness's escape for each look.** Rejected. It lets any command out, not one, and the autonomy posture seals it (ADR-028).
- **The exclusion among those the model applies itself, as for `uv` and `gh`.** Not asked here. Which commands join that set is the model's to decide, in a record of its own, past its own test (ADR-030 point 5).
- **A toolkit of the capability's now, with the model's read of it built in the capability's Task.** Not taken. How the model finds a capability's toolkit, and which wins over a project's, are the model's to decide.
- **An excluded command whose code the box cannot write,** as an agent run's excluded commands are held (ADR-066 point 6). Not taken. The box writes the clone and, on Linux, `uv`'s cache, and the model offers no copy of a command kept apart from both.
- **A command of its own for the browser half.** Not taken. It would keep the SVG renderer's looks in the box. But it would run the same scripts, configuration and environment outside the box. So it would change which looks run outside, not what one of them lets out.
- **A drawing service a person starts outside the box, which reads page files from the workspace.** Rejected. It listens on a port any process can reach, and it is a way out of the box the model does not see.
- **Playwright's headless shell.** Not taken. In the test behind DEC-020, it stopped on its own sandbox inside a box, and drew only with that sandbox off.

## Implications

- **Edits to accepted records,** made once this record is accepted, each with a pointer to it as the refinement. Accepting this record accepts them (COR-066 point 5). The edit to DEC-020 point 8 narrows a promise, from "the step says so" to where the browser's words show a sandbox:
  - **DEC-020's plain terms, "So a build in a sandbox cannot see such a page yet".** It comes to say that a session's sandbox stops the browser. The step runs outside it where a person lets the step's command out, as DEC-024 point 2 allows, the browser's own sandbox on. An agent run the model confines does not see such a page.
  - **DEC-020 point 8, "It names what is missing".** Its last sentence comes to say that the stop names the ways on of DEC-024 point 4, the SVG renderer among them.
  - **DEC-020 point 8, "A sandbox may stop the browser."** It comes to say that the step never turns off the browser's own sandbox. The step says a sandbox stopped the browser where the browser's words show one, and otherwise names what it said. The clause on #2775 and the sentence "That Task lies in version 1 of the capability" go.
  - **DEC-020 point 8, "That leaves a build in a sandbox."** It comes to say that such a build gets the file, the same scene through the SVG renderer, and a build pipeline's drawings. The browser's look falls to a run outside the sandbox: a session with none, the viewing command let out of it as DEC-024 point 2 allows, or a pipeline.
  - **DEC-020 point 7, "A browser of the Chromium family."** It gains a sentence: where the step looks for a browser by name on the command path, it skips the folders inside the clone.
  - **DEC-020's Revisit** loses its item on #2775 settling what the permission model adds.
  - **DEC-015 point 2, "The browser."** Its last sentence comes to say that the browser keeps its own sandbox on. Where a session's sandbox stops it, it runs outside where a person lets the viewing command out, as DEC-024 point 2 allows.
  - **DEC-006 point 1, "Who starts it."** It gains a sentence: a producer's outside programs keep their own sandbox on, where they have one. Where a session's sandbox stops them, they leave it only through an exclusion of the producer's command.
  - **DEC-006's Implications, the bullet on the first real producer.** Its last sentence comes to say that it takes from DEC-024 point 6 how the outside programs a producer calls are held.
  - **DEC-002 point 8, "Outside programs on the path that needs them."** It gains a sentence: such a program keeps its own sandbox on, where it has one. Where a session's sandbox stops it, it leaves it only through an exclusion of its command.
- **The opening's Task.** A Task of its own builds the opening and its test, once the step's browser half lands ([project-kit#2785](https://github.com/aleskalfas/project-kit/issues/2785)). Its parts that need no exclusion:
  - **The stop.** It names the ways on of point 4. It tells a browser run as root apart from a sandbox. A test holds that it names no other exclusion and no escape. The browser module's note on #2775 goes.
  - **The search.** Where the step looks for a browser by name on the command path, it skips folders inside the clone (point 2).
  - **The browser's own reach.** The Task tries flags that keep the browser's own requests and its crash database in, such as a proxy that leads nowhere. None may touch its sandbox (point 1).
  - **The pipeline.** The pipeline where the capability is authored draws the HTML renderer's pages on its Linux runner, and keeps them with the run.
  - **Where an agent reads the rule.** The capability's skill that guides building a piece carries point 5. Its reviewer's definition says to pass a stop's ways on to whoever asked it.
  - **The pages.** The capability's README and its reference on outputs say what a look's stop names. They also say how a project's pipeline draws the pages.
- **The opening's parts that wait on the harness.** The stop names the exclusion, and the pages say how to apply it, only once this test passes (point 2). It runs on Linux, in a box the model turns on, under the autonomy posture's sealed retry. The exclusion is applied with the model's command, in each documented form:
  - **It holds:** a look runs outside the box. The browser draws with its own sandbox on, and the page's requests are refused. Without the exclusion, the look stops and names the ways on.
  - **It holds no more:** with the exclusion applied, other commands stay in the box, such as another command of the group, or one whose name begins with the viewing command's. Nor does a look in another form carry more out, such as a compound command.
  - **It records** which hosts and folders the browser reached outside the box. The model's text says version 2.1.193 ran excluded commands inside the box (#312).
  - **A failure ends it.** Where the harness ignores the exclusion, the stop names only the other ways on. Where it matches more than the command, or only by a first word, no narrow opening exists. Point 4 forbids naming a wider exclusion, so the stop names only the other ways on, and this record is revisited.
  - **macOS too,** with the box turned on by hand and no exclusion of `uv`, once the model keeps the box on there.
- **A toolkit, once the model reads a capability's.** The capability declares the exclusion in a toolkit of its own then, marked widening, with what it lets out (point 2). How the model reads it is a change of the model's (ADR-015, ADR-016 point 5).
- **Findings for the permission model.** None is this record's to decide. Two meet the question of #312, on macOS and the model's exclusions, and go there:
  - An excluded command runs outside the box only where the harness honours its exclusions, which failed at version 2.1.193. No harness requirement states that property (COR-047), though the model's exclusions rest on it.
  - `uv` 0.13.0 ran inside the reassembled box (Context), as #312 found in the harness's own box.
- **An issue of its own** carries the other three to the permission model:
  - The model reads no capability's toolkit (ADR-016 point 5).
  - An exclusion of a command whose code lies where the box writes lets any command that writes it out of the box. That holds for the model's own exclusion of `uv`, while ADR-014 point 3 says all other commands stay confined.
  - No privilege of the model covers the command that applies an exclusion, so no deny can keep it from an agent.
- **The first real producer** ([project-kit#2575](https://github.com/aleskalfas/project-kit/issues/2575)) takes point 6 as decided. Three things follow for it:
  - A driver that starts Chromium with its sandbox off by default, as Playwright does, must turn it on. One that speaks over a port by default, as Puppeteer does, must take its pipe.
  - Its tests that start a real browser stop inside a builder's run and its checks (ADR-073 points 3 and 5). They skip there with a stated reason, or need no browser.
  - Its command's exclusion is named once a run of it shows the box stops its program (point 6).
- **Revisit this record:**
  - if the opening's Task finds that the harness ignores the exclusion, or that the browser cannot draw outside the box with its own sandbox on
  - if the harness matches the exclusion more widely than the command, or a form of the command carries another command outside the box
  - if a harness requirement of the model's comes to report on exclusions, or the model offers an excluded command kept apart from what the box writes
  - if the model's records on macOS and its exclusions change ([project-kit#312](https://github.com/aleskalfas/project-kit/issues/312))
  - if the model gains an allowance that lets the browser keep its own sandbox in the box
  - if a harness lets a sandboxed process start a sandbox of its own
  - if a run on Linux finds a box that holds the browser with its own sandbox on
  - if a producer's program cannot draw with its own sandbox on
  - if a record of the model's takes the viewing command into the exclusions it applies itself
