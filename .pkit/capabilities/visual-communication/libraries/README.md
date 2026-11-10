# The versions being built of the libraries the capability ships

Each folder here is the version being built of a library the capability ships, such as `foundations/`. Every change to the library goes into it. Its released versions, and the record of them, lie apart, under `../releases/<library>/` ([The libraries the capability ships](../files.md#the-libraries-the-capability-ships)).

## Every change here declares at least a patch of the capability

A change to a version the capability ships declares at least a `patch` of `visual-communication` in its changeset, never `none` (visual-communication DEC-013 point 4). So does the release of a version, which adds one under `../releases/`: `pkit visual release <library> --shipped` writes its changeset (DEC-013 point 2).

Why:

- **A project can observe it.** `pkit visual add` copies a library as the capability ships it, so a change to its files reaches each project that brings it in.
- **It must move the capability's version.** A version is released only where no change has touched it since the release that wrote the capability's current version (DEC-013 point 1). A patch makes the next release move that version, and carry the change.
- **A change declared to move nothing puts the library's release off.** The next release ships it under the capability's version as it was, so the library's release refuses until a later release moves that version. A patch changeset for the capability is the way out.

**So does every change of the capability that adds a tool, a field or an accepted value,** wherever in the capability it lies (visual-communication DEC-014 point 2). A project's own library names, as the release it needs, the capability's version installed when it was released. That number covers what the library uses only where each such change moved the capability's version.

Choose `minor` or `major` as for any change of the capability. The library's own version is another number, in its `library.yaml`: raise it where the change needs a higher one (DEC-013 point 3).
