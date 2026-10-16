# Creating a space

A space's definition holds the rules its pages follow: `LDOC`, inherited, and the space's own. Its scope selects the space's pages, so the rules bind on them as soon as it exists (DEC-001 point 2).

## 1. Is it a new audience?

The user and technical spaces get their definitions when the project adopts the method. Add a space only for an audience neither serves, such as the readers of an interface reference (DEC-001 point 1).

## 2. Meet the prerequisites

The scope is written from where the space's pages lie, so declare that first.

- **The roots are separate.** Two roots that are one folder give no space.
- **The places are declared.** Each place that holds the space's pages outside its root is declared under `places` in the friction key of `.pkit/project/config.yaml`. A place outside every root gives the page type, `{path: <place>, type: living-docs:page}`, since the definition selects by type.
- **Each place is assigned** to its space under `places` in `.pkit/capabilities/living-docs/project/config.yaml`.

These are edits of the configuration, so an agent asks the person first. A space the project adds has no root of its own: its pages lie in the places assigned to it.

## 3. Review the scope

```
pkit living-docs new space <space> [--set <NAME>] --dry-run
```

It prints the definition and the configuration as they would be written. The scope's `paths` name the space's root and the places assigned to it. Its `exclude` leaves out a root nested in it and each place in it assigned to another space. The set's name defaults to the space's id in upper case. Name another with `--set` where that one is taken.

## 4. Stamp it

```
pkit living-docs new space <space> [--set <NAME>]
```

It writes the definition, names it as the space's `definition` in the configuration, and records the definitions location the first time. It refuses a write that breaks validation, such as a place the scope would miss, and puts everything back. It then reports each page of the space that the space's rules fail. Fix those pages next.

It refuses, too, when the check cannot read what it judges once the rules bind. An example is a readers point that does not resolve while the space's pages name readers. Mend that first: `pkit validate` names the fix under `connections`.

For the user space, it writes the space's one rule of its own, reader paths stay unbroken, as accepted. Tell the person that merging the change accepts that rule (COR-051 point 4).

## 5. Add the space's own rules when they are needed

Add a rule only when the space needs one (RS-LDOC-006). Each rule is `RS-<SET>-NNN` with its status, its origin, its anchors and a body section headed by its id and title. An accepted rule added later needs a new major of the set. That changes what binds through the set's pin (COR-051 point 7).

## 6. Name the entry point

Stamp the space's entry page with `page.md`, then name it as the space's `entry-point` in the capability's configuration.

## 7. Check and commit

Run the checks in the shared framing's "After stamping", then commit.
