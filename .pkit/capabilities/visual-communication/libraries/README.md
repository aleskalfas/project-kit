# The versions being built of the libraries the capability ships

Each folder here is the version being built of a library the capability ships, such as `foundations/`. Every change to the library goes into it. Its released versions, and the record of them, lie apart, under `../releases/<library>/` ([The libraries the capability ships](../files.md#the-libraries-the-capability-ships)).

## Every change here declares at least a patch of the capability

A change to a version the capability ships declares at least a `patch` of `visual-communication` in its changeset, never `none` (visual-communication DEC-013 point 4). So does the release of a version, which adds one under `../releases/`: `pkit visual release <library> --shipped` writes its changeset.

Why:

- **A project can observe it.** `pkit visual add` copies a library as the capability ships it, so a change to its files reaches each project that brings it in.
- **It must move the capability's version.** A version is released only where no change has touched it since the release that wrote the capability's current version (DEC-013 point 1). A patch makes the next release move that version, and carry the change.
- **A change declared to move nothing puts the library's release off.** The next release ships it under the capability's version as it was, so the library's release refuses until a later release moves that version. A patch changeset for the capability is the way out.

**So does every change of the capability that adds a tool, a field or an accepted value,** wherever in the capability it lies (visual-communication DEC-014 point 2). A project's own library names, as the release it needs, the capability's version installed when it was released. That number covers what the library uses only where each such change moved the capability's version.

Choose `minor` or `major` as for any change of the capability. The library's own version is another number, in its `library.yaml`: raise it where the change needs a higher one (DEC-013 point 3).

## How parallel changes meet

Changes to a library here, and its releases, meet as visual-communication DEC-013 point 4 decides:

- **Two changes that raise the number alike** write the same line of `library.yaml`, so they meet only where they change one file differently. Two that raise it differently meet on that line: the higher holds, and the second to merge reads the version again after its rebase.
- **A library's release, and a change to the library merged beside it.** Whichever lands second fails the capability's own checks. A change that lands after the release finds the version here carrying a released number while it differs from that version, and fails until it raises the number. A release that lands after the change finds a change since the release that wrote the capability's version, and fails. Make the release again after the next release that moves the capability's version.
- **A library's release, and a release of the capability.** A release of the capability may land between a library release's branch and its merge. It may have shipped, under the number the library's release fixes, files a change put here and a later change took back, which a look at the history made only on the branch would miss. So the checks read the history up to the change that brings the library's release in. Where no change touched the version here since the release it names, the library's release passes though the capability's release landed, and names that older version of the capability.
- **Releases of two libraries** add two places under `../releases/` and change two records, so they meet nowhere. A base and a library built on it may each need the other's new version, as when the base's next version removes an experimental component the library's newest release uses, and the library's next version uses what the base adds. Release both in one change, the base first, and the checks read them together.

## The capability's own checks

`tests/test_visual_communication_shipped_libraries.py` holds them (DEC-013 point 6). The default branch's required checks run them on each change as it would merge, and a project's validation never runs them. Each reads a version in full, through the routine a release reads it through, so every component, a brand's tokens and its fonts are read, whether a piece places them or not. They check that:

1. **Each released version** under `../releases/` matches the hash its record keeps, and the engine reads its files. Any other finding in a released version is printed, and fails nothing.
2. **Every released version was untouched since the release it names:** no change touched the version here between the release step's change that wrote that version of the capability and the change that brings the release onto the default branch, that change included.
3. **The newest released versions read together,** each on the newest released version of each major it builds on, so a new project can lock them together.
4. **Each version here reads and checks clean** on the versions here of its bases. A finding in it fails.
5. **A version here that carries a released number** differs from that released version only in the release it needs, and none carries a number below the newest released one.
6. **A version here breaks nothing its major promises:** the release's comparison with the newest released version of its major finds no break. An addition fails nothing, since whether a change is a patch or a minor is the owner's judgement.

## What the released versions cost

Each release adds its version whole under `../releases/`, and nothing removes it (DEC-013 point 2). The methodology carries every capability's folder in each of its distributions, its wheel and its source archive, whether a project installs the capability or not. git stores a file that stays the same once; the distributions hold it once in each version.

- **The first releases.** The foundations' 1.0.0 holds about 10 KB, the starter's 1.0.0 about 38 KB, and the neutral brand's 1.0.0 about 620 KB, almost all of it the fonts the brand commits (DEC-004 point 9), which compression barely shrinks.
- **When to weigh DEC-013 again:** once the released versions of the libraries the capability ships pass 10 MB together.
- **The remedy then weighed.** A shipped brand names its fonts by hash, as DEC-004 point 9 lets a brand name a font it may not ship. The capability holds each font once, apart from the versions, and `pkit visual add` copies each font into the location's font folder (DEC-002 point 1). Each font is then held once, not once in each version. It changes those two points, and the library copy of DEC-001 point 11, a released version held whole, so it waits for the need.
