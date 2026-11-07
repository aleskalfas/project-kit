---
id: DEC-024
title: An outside program keeps its own sandbox on, and leaves the session's sandbox only through a tool agents cannot change
status: accepted
date: 2026-11-07
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** some commands of the capability start a program of another tool, such as a browser. Such a program keeps its own sandbox on, where it has one. In a stand-in for the sandbox the harness gives a session, on a Mac, the browser could not run that way. Nothing of the capability's is let out of that sandbox until a tool agents cannot change exists. Letting a command out lets out all it runs, and a command inside the sandbox could change that code. Meanwhile, a project's build pipeline may draw each piece's HTML pages on every change and keep the pictures, and an agent reads those. A person may still draw a page on their own machine, outside the sandbox. An agent never lets a command out itself, and asks a person instead. A session with no sandbox draws the page as it runs any command. Later, in three steps, one small drawing tool may run outside the sandbox, once the permission model's own record lets it out. A person installs it where no agent can change it. An agent on a person's machine then draws pages itself, and code an agent changes still runs inside. No date is promised, since the first step waits on the harness's makers. The page reaches no network, and a program a producer calls follows the same rules.

## Context

[project-kit#2775](https://github.com/aleskalfas/project-kit/issues/2775) asks what the permission model adds for an outside program the capability starts, a browser first (COR-028). It hoped an agent working in a sandbox would then see the page a reader gets. The viewing step stops where a sandbox stops the browser ([visual-communication:DEC-020-html-page-drawing] point 8). The first real producer takes the same answer for the programs it calls ([visual-communication:DEC-006-work-outside-the-engine-and-outputs], Implications).

Seven terms:
- An *outside program* is a program of another tool that a command of the capability starts, such as a browser ([visual-communication:DEC-002-files-and-validation] point 8).
- A *look* is one run of the viewing step ([visual-communication:DEC-015-viewing-step-and-reviewer] point 1), by its command, `pkit visual look`. Here it never means a visual style.
- The *box* is the sandbox the harness gives a session, which the permission model manages. The operating system holds each command of the session's shell to the files the box allows ([pkit:ADR-004] point 2). Its list of hosts bounds only a well-behaved program, and is no security boundary ([pkit:ADR-015], Context).
- The *stand-in* is the box's macOS profile, reassembled by hand, which the run below used in place of a session's box.
- A program's *own sandbox* is the one it sets on its own parts. A browser sets one on the processes that read a page.
- An *exclusion* lets one command, and all it starts, run outside the box ([pkit:ADR-008] point 4).
- The *autonomy posture* is the model's setting under which confined commands run with no prompt, whether or not anyone watches ([pkit:ADR-028]).

### The permission model, as its records and its code state it

- **One box for the session.** What it allows one command, it allows every command of the session, an exclusion aside (ADR-004 point 5; ADR-015, Context).
- **Kinds of allowance.** A *narrowing* one makes the box usable and widens no reach, such as a cache folder to write. A *widening* one lowers the boundary (ADR-008 point 1). A named host to reach is narrowing, but always reported (ADR-008 point 7).
- **The exclusion is the one widening for a command.** A person applies it on one machine with `pkit permissions sandbox exclude`. It lands in that machine's own settings, never in a committed file, and the model reports it (ADR-008 point 4). It names a command by its opening words, as an agent run's excluded commands are named (the Claude Code adapter's README).
- **Confinement toolkits.** A toolkit is data: the allowances one tool needs in the box, each marked narrowing or widening (ADR-008 point 1). The model ships some, and a project may add its own. A capability may declare its own as a fragment (ADR-015), but no part of the model reads one ([pkit:ADR-016] point 5).
- **Exclusions the model applies itself.** It applies one only where the platform requires it, once it has checked the need ([pkit:ADR-027], [pkit:ADR-030]). A command joins that set by a record of the model's, past a test of three parts (ADR-030 point 5).
- **The harness's escape** reruns any one command outside the box, a separate key on a separate layer. The autonomy posture seals it, and elsewhere it stays a person's stopgap ([pkit:ADR-028] points 3 and 5).
- **On macOS, the model's code keeps the box off.** `pkit permissions sandbox enable` turns it off there where it finds it on, and says why ([project-kit#312](https://github.com/aleskalfas/project-kit/issues/312), [project-kit#313](https://github.com/aleskalfas/project-kit/issues/313)). It names two causes: the harness's exclusions do nothing there, and the box's read-deny on `gh`'s folder breaks `gh`, `pkit` and `git push`. That departs from [pkit:ADR-014], under which macOS autonomy stands with the box on and `pkit` and `uv` excluded (point 2). In June 2026, version 2.1.193 of the harness ran excluded commands inside the box all the same (#312).
- **The model's exclusion of `uv`.** Where the model excludes `uv`, a command run as `uv run pkit` runs outside with it (ADR-014 point 2).
- **Agent runs.** A confined agent run excludes only the commands that start `uv`, on macOS, while `uv` needs it ([pkit:ADR-066] point 6). There, nothing the run's shell writes becomes code or configuration that an excluded command runs, and no host is allowed. A builder's run takes no exclusion, and reaches none of the code host's hosts ([pkit:ADR-073] point 3).

### What the run showed

The run used one Mac, macOS 26.6.2, Chrome 157, and Claude Code 2.1.319 as the harness. Each plain run drew a small page of text over SVG shapes, which asks an outside host for one picture. Chrome was started as the viewing step starts it: headless, with a throwaway profile. The module that draws a page file through a browser then drew its own planted page ([project-kit#2784](https://github.com/aleskalfas/project-kit/issues/2784), at its branch's head, `77dc7695`, which landed squashed as `69955a30`).

**The stand-in.** The session's own box was off: the project's settings leave it so, and its shell reached an outside host. The harness would not run its sandbox runtime on its own for this session, treating it as code from outside. So the stand-in was the harness's macOS profile, reassembled by hand from the text the harness carries. It took the project's settings: its folders to write, its paths denied to reads, and one host through the harness's proxy. It stands in for a run in a session's box, and does not replace one. A run in a session whose box is on is still to confirm it, in the drawing tool's Task (Implications).

| Where it ran | Its own sandbox | What it did |
|---|---|---|
| No box | On | Drew in 1.1 s. The module started it once, named each planted fault, and drew its page, in 4.6 to 6.3 s |
| No box | Off | Drew the same bytes, in 0.9 s |
| The stand-in | On, or off | Stopped within 0.3 s. The stand-in refused the folder for the socket that keeps one browser to a profile. Chrome on macOS puts it in the system's temporary folder, whatever `TMPDIR` says |
| The stand-in, granting that folder | On | Stopped in 0.2 s, when the stand-in refused that socket |
| The stand-in, granting the folder, its socket and the services refused | On | Crashed in 0.4 s on a check, after more services and system values were refused |
| The stand-in, granting every service and system value at once | On | Its parts could not start their own sandbox, since the system refuses a second sandbox to a sandboxed process. It crashed in 5 s |
| The same | Off | Drew the same bytes as with no box, in 1.0 s. The stand-in refused its requests to outside hosts |

- **The module in the stand-in.** It stopped before the browser started: the stand-in refused the way the module hands the browser its pipes. With that granted, it stopped where the browser did.
- **What reached the network, with no box.** In the plain runs, the page's own request went out. The module refused both requests its planted page makes. In every run, the browser also reached two of its maker's hosts on its own, despite its flags against background requests.
- **What the browser wrote, with no box.** Its profile, some 220 files, in the folder given. A lock folder and a copy of itself in the system's temporary folder, both removed at a clean exit. Its crash database's settings, in the person's own Chrome folder, where a crash writes its dumps too.
- **What it left.** No process. The two runs that crashed each left the lock folder, with a socket and a link. No clean run left one.
- **`uv` in the stand-in.** `uv` 0.13.0 ran one command inside the stand-in, past the denial that made 0.9.8 panic (ADR-014, Context). #312 found the same in the harness's own box, at version 2.1.193 of the harness.
- **On a pipeline's Linux runner,** the module's tests started a real Chrome, with no box, while #2784 was built.

**Not reached:** a session whose box is on, the harness's sandbox runtime run alone, and whether version 2.1.319 honours an exclusion. Linux and its box: the harness's text says that box turns off user namespaces where it can, and Chrome's own sandbox needs them. That was read, not run, as was Chrome on Linux refusing to run as root with its own sandbox on. A producer's browser, Chromium, Playwright's builds, and a second Mac.

### What an exclusion of the viewing command would let out

A person could apply one with the model's command. It would let out this:
- **The whole command, with all it starts** (ADR-008 point 4). That includes all it reads as code or configuration from a folder the box writes:
  - the backbone's and the capability's scripts, and the project's configuration, which names the browser, all in the clone
  - the files `uv run` reads there, such as the project's own package and its lock
  - on Linux, `uv`'s cache, which holds the environment the look's script runs in, and which the box writes for `uv`
- **So it reaches past the command.** On a machine where the exclusion stands, a command that can write those files changes what the next look runs outside the box. The permission hook judges a command's words, never what the command runs (ADR-004 point 1). Under the autonomy posture that look runs with no prompt. The posture seals the harness's escape (ADR-028), and leaves this way out open.
- **The harness says so too.** Its documentation warns that an exclusion covering a script an agent can change lets the agent run that script outside the box (ADR-066, Context).

## Decision

**An outside program the capability starts keeps its own sandbox on. Until a tool agents cannot change is let out, nothing of the capability's leaves the session's sandbox. Where the sandbox stops a look, the step says why and names the ways on: a build pipeline's drawings, a person's own run, and the SVG renderer's pages. The page reaches no network. The capability relies on one way out alone: a drawing tool a person installs where no agent can change it, once a record of the model's lets it out. Every other outside program is held the same way.**

### 1. The program keeps its own sandbox on

- **Never off.** The capability passes no flag that turns off or weakens the sandbox of any of the program's processes, or merges them into one. It passes none its maker marks unsafe, and none that lets a page read past its own file. Its configuration has no setting for one.
- **A program a project names** is started as named, from a file the project reviews (DEC-020 point 7). What that program does is the project's own choice.
- **What it holds.** A browser reads files the project did not all write: a brand's faces, a producer's pictures, a piece's words. Its own sandbox keeps a fault in reading them inside the part that read them.
- **Outside the box, it is the only layer.** Turned off there, such a fault would act with the person's rights: their files, their keys and their network.

### 2. Until point 7's third step, nothing of the capability's leaves the box

- **No exclusion.** The capability names no exclusion from the box, for the viewing command or any other. It declares none in a toolkit. A look's stop and the capability's pages name none.
- **No allowance of any kind.** The capability declares no allowance in the box. A host that a project's fetch of a pipeline's drawings needs is that project's own allowance, which the model classes (ADR-008 point 7).
- **No escape.** No command of the capability asks for the harness's escape, which reruns any one command outside the box (ADR-028). None starts the program through the system's launcher, or hands work to a copy already running.
- **Where no box holds the look.** A session with no box runs a look as it runs any command. So does a command the model already runs outside the box, as under its exclusion of `uv`. The browser draws there, its own sandbox on. That is the session's state or the model's way out, not this record's, and nothing of the capability's names it or rests on it.
- **No report of which.** The step cannot tell whether a box held the browser, so its report does not say. The model's own report names each exclusion.

### 3. The page reaches no network

- **Every request refused.** The step refuses each request but the page file's own and a `data:` address, and names it (DEC-020 point 6). That holds inside the box and outside it.
- **What the step does not see.** The browser's own requests, such as to its maker's hosts, reach out where nothing else holds them (Context). So does any request the browser does not hand the step. That holds in a person's run and in a pipeline. Point 7's tool holds them too.
- **Over a pipe, never a port.** The program is driven over a pipe, never over a port that listens, since any process on the machine can reach a port.

### 4. Where no browser can run, a look stops and names the ways on

- **Nothing partial.** The step keeps no output of the program's run. It leaves its page file and a report, and no image (DEC-020 point 8).
- **What it says.** It names the program and what the program said (DEC-020 point 8). Where the program's words show a sandbox, it says that a sandbox stopped the program.
- **The ways on.** It names these:
  - a build pipeline's drawings of the piece's pages (point 5), as a way a project may take. They show a pushed commit, not the working tree.
  - the same look, run outside the box by a person, such as a single time in their own terminal. It runs the clone's scripts as they stand, with that person's rights. This line is addressed to a person (point 6).
  - the SVG renderer's pages, which show the layout, never this page
- **Never named.** The stop never names the harness's escape. Nor does it name an exclusion that would carry the look out of the box, such as of the viewing command, of `pkit`, or the model's exclusion of `uv`.
- **A browser that refuses its own sandbox.** Chrome run as root refuses to start with its own sandbox on, as a container may run it (Context). The step tells this apart from a sandbox that stopped it, and says so.

### 5. A build pipeline may draw each piece's HTML pages

- **Where a project's pipeline draws them.** A build pipeline on a runner with a browser can run the look through the HTML renderer on each piece. It does so on every change it checks, such as a pull request. The pipeline where the capability is authored found a real Chrome on its Linux runner, with no session's box around it (Context).
- **The same rules.** The browser keeps its own sandbox on there, and the page reaches no network as point 3 says (points 1 and 3).
- **No standing reach.** The job runs the change's own scripts, which an agent may have written. So it holds no secret, and its token only reads.
- **Kept for agents.** The pipeline keeps each look's images and its report with the run. An agent that cannot draw the page in its session fetches and reads those, where it can reach the run. They show the commit the run drew, not the working tree.
- **The project's choice.** The capability's pages say what a pipeline runs for this, under which name it keeps the pictures, and how an agent fetches them. A project's pipeline takes it up as the project chooses. No setting of the capability's says whether it does.

### 6. An agent asks, and never opens the way itself

- **The person decides.** An agent never applies an exclusion from the box, since a widening is a person's gesture (ADR-008 point 4). Nor does it use the harness's escape on its own. Where a look stops on a sandbox, it reads a pipeline's drawings where it can reach them. Otherwise, or where it needs the working tree drawn, it asks a person, naming the ways on of point 4.
- **A person's run is read, not redrawn.** Where a person ran the look outside the box, the agent reads the folder that run left. It never runs the look over it, since a run replaces that folder (DEC-020 point 5).
- **The command as the project writes it.** An agent runs the command in the form the project uses. It never changes that form to slip out of the box, such as to `uv run` where the model excludes `uv`.
- **Where the rule is carried.** The capability's loaded rule set carries this point, so it binds every session wherever the capability is installed (COR-070 point 1). A look's stop and the capability's skill that guides building a piece repeat it where an agent meets the case. The capability's reviewer, reading a folder a stop left, passes the ways on to whoever asked it.
- **An agent run the model confines** takes only the exclusions the model's own rules give it, and reaches no host of a pipeline's (ADR-066 point 6, ADR-073 point 3). Where its look stops, only the SVG renderer's pages remain in the run. Whoever started the run may read a pipeline's drawings once its commits are pushed.

### 7. The capability relies on one way out: a drawing tool that agents cannot change

- **Three steps, in order.** Each waits on the one before it. No date is promised, since the first waits on the harness's makers.
- **Step 1, the test the capability waits for.** A test of the permission model's shows that the harness lets out exactly one named program, with what it starts, and no other command. No form the test tries carries another command out with it, or reaches more through it. The forms include a compound command, a redirection, an expansion in its arguments, a variable set before it, and a name that begins with the program's.
- **Step 2, the drawing tool.** A small program, apart from every project's clone:
  - **An outside program.** To the capability, the tool is an outside program (DEC-002 point 8). The methodology installs it on no machine, and a command checks for it and names what is missing. No sync, upgrade or migration of the methodology reaches it.
  - **Installed once by a person,** like any program, in a folder the box cannot write. A new version arrives only when a person installs it.
  - **No clone's code changes it.** That holds for code a person runs outside the box too, such as a look (point 4). So no code of a clone changes what the tool runs or reads as configuration, the browser it starts included. How the tool is placed and installed so is its Task's.
  - **What it does.** It takes a page file and returns its pictures, with the browser's own sandbox on. The browser reaches no host, its own requests included (point 3). What a look reads of a page holds of the tool's pictures too (DEC-020 points 6 and 7).
  - **What it reads.** It reads only a page the renderer marked, and returns nothing of any other file. So no file the box denies a read reaches the clone through it.
  - **What the clone can do to it.** Outside the browser's own sandbox, it runs no code and reads no configuration from a folder the box writes. Nothing a command passes it chooses what it runs. It writes its pictures as new files, under fixed names, in a folder it makes, following no link.
  - **A command of its own.** A program that a command inside the box starts stays inside the box. So a look leaves the page as a file and stops. The tool runs as a command of its own, and a later look reads back its pictures.
  - **Left to a later record.** Where DEC-020's reads lie for the tool is decided by a later record of the capability's (Implications).
- **Step 3, the model's record.** The capability relies on an exclusion of the tool only once a record of the model's lets it out. That record rests on step 1's test, and names the tool so that no other program can take its name. The capability asks the model for nothing else. That record decides how the exclusion is applied and reported, which runs take it, and what grant lets the tool's call run (ADR-004 point 1).
- **Then.** An agent on a person's machine draws pages itself, through the tool. Code an agent changes still runs inside the box. An agent run the model confines draws through it only where that record gives it the tool. A look's stop names the tool among the ways on of point 4.
- **Until then,** point 2 holds.

### 8. Every other outside program is held the same way

- **Points 1, 2, 3 and 6 hold** for each outside program another command starts, such as a program that writes a PDF, or one a producer calls to draw a 3D scene. A producer runs through a command of the capability (DEC-006 point 1). Where such a program cannot run, its command names what is missing, and never the escape or an exclusion (point 4).
- **Its way out.** It leaves the box only as point 7's tool does: inside a tool of its own, held as step 2 says. A record of the model's lets that tool out, past step 1's test. The capability builds one only once a run shows the box stops that program.
- **None for a program with no sandbox of its own.** Outside the box nothing would hold a fault in what such a program reads. So no tool of the capability's carries it out of the box.
- **No host for what it is handed.** Drawing needs no network (DEC-002 point 8), so nothing the command hands the program reaches one, as point 3 holds for the page. Outside the box, nothing holds the program's own requests, which a run of it records. That binds the outside program, not a service a producer declares under DEC-002 point 8.
- **Only what it is handed.** The program reads only the inputs its command hands it, such as files its driver serves over the pipe, or `data:` addresses (point 3, DEC-020 point 6).
- **Where it cannot run, the picture waits.** A picture whose program cannot run is not made there. Where it never ran, the piece has no picture yet. A stale one asks for attention while stale (DEC-006 point 8), and an export stops on it (DEC-006 point 7). A person makes it where the program runs.
- **A helper is the project's.** A helper runs as the project's own script, under the project's own permission model (DEC-006 point 1). So this record does not bind what a helper starts.

## Rationale

**Why nothing leaves the box until then.** An exclusion of the viewing command lets out the clone's scripts and settings with it (Context). Any command that can write the clone would then change what the next look runs outside the box, with no prompt under the autonomy posture. Whoever maintains the capability chose to wait, and to let something out only once it is code agents cannot change.

**Why a person's own run stays a way on.** It runs the same scripts with the person's rights, as the exclusion would. But it is that person's act, once, and no standing opening that every later look goes through.

**Where this bites.** A session with no box draws a look as it runs any command. Where the model excludes `uv`, a look run through `uv` already runs outside the box, with the reach Context gives. So this record bites only where a box holds the look, and there a pipeline's drawings serve.

**Why the box is not widened for the browser.** The box serves the whole session, so an allowance for one program reaches every command (ADR-004 point 5). In the stand-in, the browser asked first for a socket in the system's temporary folder. It then asked for more of the system's services than the box names. Even with every one granted, it could not start its own sandbox, since macOS refuses a sandbox inside a sandbox.

So on macOS no allowance in the box serves a browser that keeps its own sandbox on. Outside the box, it drew at once with its own sandbox on. On Linux, the harness's text gives another cause, which was read, not run (Revisit).

**Why the browser's own sandbox stays on.** It is the layer that holds a fault in reading a face or a picture. Outside the box it is the only layer, and Chrome's makers advise against running without it.

**Why a build pipeline's drawings in the meantime.** A runner with a browser and no session's box around it draws the page a reader gets, as the pipeline where the capability is authored found (Context). Nothing is let out on any person's machine. An agent reads those pictures of a pushed commit. The job runs the change's own scripts, so it gets no standing reach (point 5).

**Why a tool agents cannot change.** What runs outside the box must be code a person chose, not code a command in the box can change. A tool a person installs where no clone's code can change it runs only what that person installed. The clone hands it a page, which the browser reads inside its own sandbox, with no network. A confined agent run holds its excluded commands the same way (ADR-066 point 6).

**Why the tool is an outside program.** The methodology's own tool, `pkit`, lies where the person's account writes, and an upgrade replaces it ([pkit:ADR-033], [pkit:ADR-063]). Step 2 forbids both. So the tool stands apart from the methodology's lifecycle, as any outside program does. ADR-066 point 6 holds code outside what the shell writes, and no record holds it outside what the person's own rights write.

**Why a loaded rule holds the agent.** No deny of the model's stops an agent from running the command that applies an exclusion. Whether the box lets a command write the settings it lands in is the harness's. So only a rule each session loads holds an agent from it (COR-070 point 5).

**Why the three steps, in that order.** Without step 1, an exclusion may hold nothing, as at version 2.1.193 of Claude Code (#312), or let out more than the tool. Without step 2, an exclusion lets out code the box writes, as the viewing command's would. So step 3 waits on both. The model decides it, since each widening is the model's to govern (ADR-008 point 4).

**Why one rule for every outside program.** Each starts from a command of the capability, under the same box, and reads files the project did not all write. No producer's browser was run, so its own test may find that point 1 cannot hold for it.

**The cost.** Until step 3, no agent in a session's box draws the page itself. It reads a pipeline's pictures of a pushed commit, a run later, or asks a person. A project whose pipeline runs no browser has only a person's run and the SVG renderer's pages. A run the model confines, a builder's among them, has only the SVG renderer's pages, and after step 3 gets the tool only where the model's record gives it.

Step 1 waits on the harness's makers, so no date is promised. Outside the box, in a person's run or a pipeline, the browser reaches its maker's hosts and writes in the person's browser folder (Context).

### Alternatives considered

- **An exclusion of the viewing command, which a person applies on their own machine.** Rejected by whoever maintains the capability. It lets out the whole command: the clone's scripts and settings, and on Linux `uv`'s cache (Context). Any command that can write them changes what the next look runs outside the box. Under the autonomy posture that happens with no prompt, through a way out the posture's seal leaves open.
- **The capability asks for nothing, so an agent in the box never sees the page.** Rejected. An agent should see the page a reader gets: through a pipeline's drawings until step 3, and through the tool after it.
- **The browser's own sandbox off, inside the box.** Rejected by whoever maintains the capability. In the stand-in it drew only in a box opened past what the harness allows, and Chrome's makers advise against it. A fault would act with the box's rights, which reach the clone.
- **A container or a virtual machine for each run, started from the box.** Rejected by whoever maintains the capability. Starting one needs Docker let out of the box too, the widening with the largest reach the model names (ADR-030 point 5).
- **A container or a virtual machine that point 7's tool starts, outside the box.** Not decided here. It would add a layer beyond the browser's own sandbox, and step 2's Task may weigh it.
- **A set of narrowing allowances for the browser.** Rejected. None let the browser keep its own sandbox in the stand-in on macOS (Context). On Linux this was read, not run (Revisit).
- **The harness's escape for each look.** Rejected. It lets any command out, not one, and the autonomy posture seals it (ADR-028).
- **The viewing command among the exclusions the model applies itself, as for `uv` and `gh`.** Rejected. It would let out what the viewing command's exclusion lets out, with no person's gesture. Which commands join that set is the model's to decide, past its own test (ADR-030 point 5).
- **A command of its own for the browser half, let out of the box.** Rejected. It would run the same scripts, configuration and environment from the clone. So it would change which looks run outside the box, not what one of them lets out.
- **A drawing service a person starts outside the box, which reads page files from the workspace.** Rejected. It listens on a port any process can reach, and it is a way out of the box the model does not see. Point 7's tool listens on nothing, and a record of the model's lets it out.
- **A drawing watcher a person starts outside the box, which draws the page files that land in a folder.** Not taken. It needs no exclusion, but it is a way out of the box the model neither sees nor reports. While it runs, it draws whatever any command puts there.
- **Playwright's headless shell.** Not taken. In the test behind DEC-020, it stopped on its own sandbox inside a box, and drew only with that sandbox off.

## Implications

- **Edits to accepted records,** made once this record is accepted, each with a pointer to it as the refinement. Accepting this record accepts them (COR-066 point 5). The edit to DEC-020 point 8 narrows a promise, from "the step says so" to where the browser's words show a sandbox:
  - **DEC-020's plain terms, "So a build in a sandbox cannot see such a page yet".** It comes to say that a session's sandbox stops the browser, and that the step leaves it only as DEC-024 allows. So a session in a sandbox reads a build pipeline's drawings of such a page where it can reach them, or asks a person to draw it. Otherwise it has the SVG renderer's pages.
  - **DEC-020 point 8, "It names what is missing".** Its last sentence comes to say that the stop names the ways on of DEC-024 point 4: a build pipeline's drawings, a person's run outside the sandbox, and the SVG renderer.
  - **DEC-020 point 8, "A sandbox may stop the browser."** It comes to say that the step never turns off the browser's own sandbox. The step says a sandbox stopped the browser where the browser's words show one, and otherwise names what the browser said. The clause on #2775 and the sentence "That Task lies in version 1 of the capability" go.
  - **DEC-020 point 8, "That leaves a build in a sandbox."** It comes to say that such a build gets the file and the same scene through the SVG renderer and resvg. Where it can reach them, it also gets a build pipeline's drawings of a pushed commit. The browser's look falls to a pipeline's run, a person's run, a session with no sandbox, or, after DEC-024 point 7's third step, the drawing tool.
  - **DEC-020's Revisit** loses its item on #2775 settling what the permission model adds.
  - **DEC-015 point 2, "The browser."** Its last sentence comes to say that the browser keeps its own sandbox on, and leaves a session's sandbox only as DEC-024 allows.
  - **DEC-015 point 7, "Nothing unseen reads as clean."** It gains a sentence: on a folder a stop left, the reviewer passes the ways on that the stop names to whoever asked it.
  - **DEC-006 point 1, "Who starts it."** It gains a sentence: a producer's outside programs keep their own sandbox on, where they have one, and leave a session's sandbox only as DEC-024 point 8 allows.
  - **DEC-006's Implications, the bullet on the first real producer.** Its last sentence comes to say that it takes from DEC-024 point 8 how the outside programs a producer calls are held.
  - **DEC-002 point 8, "Outside programs on the path that needs them."** It gains a sentence: such a program keeps its own sandbox on, where it has one, and leaves a session's sandbox only as DEC-024 allows.
- **A Task for the pipeline's drawings and the stop,** building on the step's browser half, which has landed ([project-kit#2785](https://github.com/aleskalfas/project-kit/issues/2785)):
  - **The stop** names the ways on of point 4, in place of the stop's words that landed there, and tells a browser run as root apart from a sandbox. A test holds that it names no exclusion and no escape. The browser module's note on #2775 goes.
  - **The loaded rule set.** The capability's first loaded rule set carries point 6, each rule's origin citing this record (COR-070 point 1).
  - **The pipeline.** The pipeline where the capability is authored draws each piece's pages through the HTML renderer on every pull request, and keeps them with the run (point 5).
  - **The fetch.** The capability's pages and its skill say how an agent fetches the pictures of a change's head, and a test tries that fetch from inside a box.
  - **Where an agent meets the rule.** The capability's skill that guides building a piece repeats point 6. Its reviewer's definition says to pass a stop's ways on to whoever asked it.
  - **The pages.** The capability's README and its reference on outputs say what a look's stop names, and what a project's pipeline runs to draw the pages.
- **A Task of the permission model's for step 1,** under #312. It declares what an exclusion must let out as a harness requirement (COR-047), and a probe observes it in each form it tries. No harness requirement states that property, though the model's exclusions rest on it.
- **A Task for steps 2 and 3,** once step 1's test passes. It builds the drawing tool, its release and its install. It proposes the model's record that lets out only the tool. Its test runs in a session whose box is on: in the box the look stops, and under the exclusion the tool draws, reaching no host.
  - **The capability's record it makes** decides where DEC-020's reads lie for the tool (point 7). It makes the edits that follow to DEC-002 point 8, DEC-015 point 2 and DEC-020 points 7 and 9.
  - **A browser the tool carries** would overturn in part DEC-020 point 7's "installs and pins none", which that record would say.
- **Findings for the permission model,** none this record's to decide, go with the Tasks of steps 1 and 3. They are what an exclusion lets out from where the box writes, the model's own exclusion of `uv` among them, and `uv` 0.13.0 in the stand-in. They are also the model's read of a capability's toolkit, and that no privilege covers the command that applies an exclusion.
- **The first real producer** ([project-kit#2575](https://github.com/aleskalfas/project-kit/issues/2575)) takes point 8 as decided. Three things follow for it:
  - A driver that starts Chromium with its sandbox off by default, as Playwright does, must turn it on. One that speaks over a port by default, as Puppeteer does, must take its pipe.
  - Its tests that start a real browser stop inside a builder's run and its checks (ADR-073 points 3 and 5). They skip there with a stated reason, or need no browser.
  - Its program leaves a session's box only through a tool of its own, after step 1's test, once a run of it shows the box stops it (point 8).
- **Revisit this record:**
  - when step 1's test passes on a harness, or finds that a harness cannot let out one program alone
  - when step 2's tool is built, or its build finds that the clone must change what it runs, or that DEC-020's reads cannot hold of its pictures
  - when the model's record of step 3 is accepted, or refused
  - if an agent in a session's box cannot fetch a pipeline's drawings
  - if the model's records or its code on macOS and its exclusions change (#312)
  - if the model offers an excluded command kept apart from what the box writes
  - if the model gains an allowance that lets the browser keep its own sandbox in the box
  - if a harness lets a sandboxed process start a sandbox of its own
  - if a run on Linux finds a box that holds the browser with its own sandbox on
  - if the browser cannot draw in a pipeline, or outside the box, with its own sandbox on
  - if a producer's program cannot draw with its own sandbox on
