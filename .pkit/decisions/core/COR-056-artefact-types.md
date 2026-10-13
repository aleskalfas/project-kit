---
id: COR-056
title: An artefact's type is declared by its owner, on the place that holds it
status: accepted
date: 2026-10-11
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

One folder often holds artefacts of different sorts. A documentation root (COR-049) may hold pages, decision records, the entries of an analysis and rules. A rule set says which artefacts its rules reach (COR-051 point 2). Selecting them by the paths of their files alone cannot tell these apart. A set meant for pages must list each page, or exclude every other owner's folder. A folder that some component adds later then joins it without a word.

What an artefact is could be inferred from the fields it carries. But two documents can carry the same fields and still be different things. A page and the template it was made from carry the same fields. A project may also use a field of the same name for its own purpose. Inference fails silently in both directions, as inferred anchors do (COR-050, Rationale).

The places declared to hold anchored artefacts (COR-050 point 1) already say most of what an artefact is. A component that declares a place for its glossary knows that every entry there is a term. Each place is declared by the owner of what it holds. So the owner can say, on the place, what the artefacts in it are.

## Decision

**An artefact may have one *type*: a declared name for what it is. Each component declares its types in a type registry, and whoever declares a place may name a type on it. The backbone resolves every artefact's type from the places that match its file, and gives every rule the backbone's type for rules. It gives one answer that every reader shares. Friction never reads a type.**

### 1. What a type is

A type is one declared name for what an artefact is. An artefact has one type, or none.
- **Its name.** A component's type is written `<component>:<name>`, and the backbone's are written `backbone:<name>`. A project's own are bare, as a project rule set is cited bare (COR-051 point 6). A bare type holds no `:`. No type's name holds `/`, which stays free for sub-types (Alternatives considered).
- **An entry takes the type its file's place gives.** A place matches files, not entries. So the type a place gives reaches every entry of a collection file it matches, each entry subject to point 4. Rules are the one exception: every rule takes the backbone's type for rules (point 3).
- **No type.** An artefact that is no rule, and that no typed place gives a type, has none. A file outside every place holds no artefact, and neither does a held document (COR-050 point 1), so neither has a type.

### 2. Who declares it

Each owner declares its own types, and whoever declares a place may name a type on it.
- **A component's type registry.** A component declares its types in a *type registry*, under `types` in the `friction` block of its package metadata. Each entry has a description. It also says whether a project may give the type to its own places, and an entry that does not say admits no project place.
- **A kind field.** A registry entry may also name the type's *kind field*. That is one of the artefact's own fields, in which an artefact of the type declares its kind. Here a *kind* is the type's owner's word for one variety of the type, never an anchor kind (COR-050 point 2). Point 4 says how a kind field gates the type.
- **The backbone's types.** The backbone declares its own types, and the one answer lists them beside the type registries (point 6). The backbone gives them without any place, and no place may name one.
- **A component's places.** A component names a type of its own type registry on a place it declares in its package metadata, under the key `type`. A place that names a type its registry does not declare gives no type. The project cannot mend a component's package metadata, so that is reported and does not fail (COR-055 point 1).
- **The project's places.** In the backbone configuration, a place written as a bare path gives no type, and one written `{path, type}` gives that type. The type is a bare type of the project's own, or a component's type whose registry admits project places. A project declares its own type by giving it on one of its places. A project's own type has no registry entry, so it names no kind field.
- **Names that would collide.** A bare project type equal to the name of a type the backbone or an installed component declares is refused (Rationale).
- **A component named in the configuration.** A project place that gives a component's type names an installed component (COR-048 point 2). It fails validation unless that component is installed, declares the type and admits project places. Uninstalling a component offers, with consent, to take its types off the project's places, as COR-048 point 2 asks. The places stay, untyped. The uninstall plan also reports each rule set whose scope names one of its types. Such a scope fails validation until the project mends the set (COR-051 point 2).

### 3. How the backbone resolves it

The backbone takes an artefact's type from the places that match its file. It finds those places as COR-050 point 1 does. It takes types only from package metadata and the backbone configuration, never from a component's own configuration. Of the artefact itself, it reads only a kind field (point 4).
- **A rule is `backbone:rule`.** Every rule, an entry of a rule-set file (COR-051 point 2), takes the backbone's type for rules, whatever place matches its file.
- **A project place yields to a component's place.** A place is *root-wide* when it equals or encloses a documentation root (COR-050 point 1). It then reaches every document the root could hold. Where a component's own place that is not root-wide matches a file, no project place gives that file a type. This holds whether the component's place is typed or not. A typed project place that yields so is reported, and does not fail.
- **A root-wide place comes last.** A typed root-wide place yields to every typed place that is not root-wide.
- **Otherwise the most specific place wins,** whoever declares it, and the same order ranks root-wide places among themselves. A place's *literal part* is its path up to its first wildcard. A folder's literal part is its path followed by `/`. A glob that is a folder followed by `/**` alone is read as that folder. The longer literal part, counted in characters, wins. At equal length, an exact file beats a glob, and a glob beats a folder.
- **A tie fails validation, where the project can mend it.** Two typed places that match one file, rank equal and give it different types are a *tie*. A tie between places that only components declare is reported and does not fail. The project cannot mend it in its own files (COR-055 point 1).
- **One component's place over another's.** One component's typed place may outrank another component's own place that is not root-wide, and give a file of it a type. That is reported, and the type stands. Within one component, nothing is reported.
- **An untyped place gives no type.** Apart from keeping project places off a component's files, it takes no part: it shadows no other place.
- **A tie counts as each type in contention.** While a tie stands, the artefact counts as each of the tied types. A type with a kind field counts only where the artefact declares its kind (point 4). So every rule set whose scope selects one of them still reaches it.
- **What a type that fails validation gives.** A value the configuration's schema refuses gives no type, and readers warn, as COR-048 point 4 says. A component's type that a project place or a scope names, and that no installed component's type registry declares, gives no type either. Its kind field is unknown, and validation fails. Any other type that fails validation still counts until the declaration is mended. So nothing a scope selects drops out of it without a word.

### 4. How a kind field gates the type

A kind field (point 2) is one of the artefact's own fields, outside the methodology's container (COR-050 point 1).
- **The declaration decides.** Where the winning place (point 3) gives a type with a kind field, an artefact takes the type only when it declares its kind there. Otherwise it has no type. A less specific place does not type it instead.
- **Documents and entries alike.** A document declares its kind in its front matter, and an entry among its own fields.
- **The kinds are the owner's.** The backbone reads only whether the field is present and not empty, never which kind it names.

### 5. Limits

- **Friction never reads a type.** No friction check (COR-050) reads one. A type changes no anchor, no revalidation and no answer.
- **A type changes neither what counts as an artefact nor its content.** The places alone decide which files hold artefacts (COR-050 point 1). A type is declared on a place, outside every artefact. So giving a place a type, or changing it, changes no artefact's content and flags nothing anchored to it. A kind field is one of the artefact's own fields, so declaring a kind there changes its content, like any other edit of its fields.

### 6. One answer

For each artefact, the backbone answers with its type and the place that gave it, or the backbone for a rule. In a tie, it gives every type in contention, each with its place. It lists the type registries and the backbone's own types beside that answer. A component's checks and every other reader take the type from that answer, and the backbone applies a rule set's scope with it. None resolves a type itself.

### 7. Where types live, and when that changes

Types sit on the places that components and the project declare under the anchors-and-friction record (COR-050 point 1). The type registry sits beside those places, in the same block. Friction reads neither. A place is the one declaration of where artefacts are, and a second list of places would drift from it. A core record may come to define one more concept on places, beside friction's own and types. Then places and the type registry move into a functionality of their own.

## Rationale

**Why a type is declared, never inferred.** Two artefacts can carry the same fields and be different things. A rule meant for one would then reach the other. A declared type is a claim its owner made, and validation can check it. Where nobody declared one, the artefact has none, which is honest.

**Why on the place.** A place already says, for most artefacts, what they are. A type field in every artefact would repeat that on each one. Declared once on the place, the type cannot disagree among the artefacts of one place.

**Why a kind field.** One place may hold artefacts of a type beside documents that are not of it, or not yet. A documentation root, for example, may hold pages beside documents nobody has yet said are pages. Typing the whole root would make each of those a page, and rules meant for pages would reach it. So where one place holds artefacts of many sorts, the artefact's own declaration decides. This is not inference: the type's owner names one field as the declaration, and the artefact makes it or does not. A project may use that field for a purpose of its own in such a place. It then gives that folder a type of its own, which outranks a root-wide place. The kinds are the owner's vocabulary, so the backbone reads only that a kind is declared. No less specific place types an artefact that declines the winning type, so a component's place never hands an artefact to a broader one.

**Why a type's name carries its owner.** Two components may each have a type called `page`. With the owner in the name, they never collide. A project's own types are bare, as its own rule sets are. A bare project type equal to the backbone's or a component's type name is refused. Otherwise a project that left out the prefix would mean that type and silently make another, which no scope would notice.

**Why a type registry.** A type named on a project place, or in a rule set's scope, must be checked against something. Without a registry, a misspelt type would select nothing, without a word. A project's own types are checked against the places that give them, which is where a project declares them. The registry also says whether a project may use the type on its own places. A component that checks only its own places would otherwise have its type given to files it never checks. So an entry that does not say admits none.

**Why a project place yields to a component's place.** A component's artefacts stay its own, and so do the checks it runs on them. A project place that gave them another type would take them from it. If a more specific project place failed validation for taking them, whether a configuration failed would turn on how two owners spelt their places. A project place also has no way to leave files out. So a component place with a short literal part would make almost every typed project folder fail. Yielding keeps the component's artefacts its own, and the report tells the project. An untyped component place keeps its files too. So a component that later types its places changes nothing for the project's places.

**Why a root-wide place comes last, and otherwise the narrower place wins.** A root holds everything beneath it, so typing it says least about any one file. Of two places that match one file, the one with the longer literal part names fewer folders, so it was written for fewer files. At equal length, a glob matches only some of the files a folder holds, so the glob is the narrower. One place spelt two ways ranks the same, since a folder and the same folder followed by `/**` match the same files.

**Why a tie fails, and why it counts as each type.** A silent choice between two declared types would hide which rules reach an artefact. Until the declarations are mended, the artefact counts as each type in contention. Every rule set that selects any of them still reaches it. So a tie never takes rules off an artefact without a word. A tie between two components' places fails nothing, since the project cannot mend it in its own files. It is reported, and the artefact still counts as each type. One component's place that types another's artefacts is reported for the same reason. Its type stands, since the project cannot change it.

**Why a type that fails validation mostly still counts.** A type that is well formed and known keeps counting until it is mended. So a scope that selects it keeps reaching the artefact while validation names the fault. A value the schema refuses is read as every invalid value of the configuration is read. A type that no type registry declares has no known kind field. Counting it would type every document in the place, which is the reach the kind field exists to prevent. So it gives no type, and validation fails on it and on any scope that names it.

**Why one answer.** Components that each resolved types would disagree wherever their places overlap. One answer, given by the backbone, is the same for every reader. It also names the place that gave the type, so nobody takes the type from a different place.

**Why friction never reads a type.** Friction asks whether an artefact still holds against what makes it true. That question is the same whatever the artefact is. If friction read types, a changed declaration on one place would become a change to every artefact under it.

**Why types sit on friction's places, though an audience attribute did not.** Every key of the backbone configuration is owned by a record that defines it, and a component adds no key there (COR-048 point 2). For that reason, a documentation component rejected an audience attribute on each entry of the friction key ([living-docs:DEC-001-living-docs-discipline], Alternatives considered). That attribute would have been the component's own field in a key the core owns. A type differs in who defines the field. A core record defines it and refines the record that owns the key. A component's type on a project place is still a value the component named. But it carries its owner's name, and a value that names an installed component is a case COR-048 point 2 already provides for. So that rejection stands for what it rejected, a component's own field on a core key, and does not reach a type. The type registry sits in the same block as the places. So the values a place may name are declared beside the places that name them.

**Why core.** Rule sets select by type, and components that must not depend on one another each declare types. One resolution must serve them all. Nothing here names a discipline. The consumers are designed alongside, not guessed, so the usual wait for a pattern to recur (COR-007) is not applied.

### Alternatives considered

- **Selecting by the fields an artefact carries.** Rejected. Different documents carry the same fields, so a selection over fields infers what a document is.
- **Paths and exclusions alone.** Rejected. A set meant for one sort of artefact would exclude every other owner's folder under a root. A folder that a component adds later would join the set unseen.
- **Every document in a root taking the root's type.** Rejected. A document nobody has classified would take the type, and the rules meant for that type would reach it.
- **A type field in every artefact.** Rejected. It costs a field on every artefact, where one place already says what most of them are. The kind field keeps the artefact's own declaration for the places that hold artefacts of many sorts.
- **The owner of a place as its type.** Rejected. A project owns places of every sort, so naming the owner says nothing about what a place holds.
- **Each component inferring types when it runs.** Rejected. It is inference again, and components would answer differently where their places overlap.
- **A project place that takes a component's artefact failing validation.** Rejected. Whether it failed would turn on how the two owners spelt their places. A project also could not leave a component's files out of a broad place. The yield, with its report, keeps the signal.
- **Several types per artefact, each matching place adding its own.** Rejected. A root's type would reach every component artefact beneath it, which one answer with an order of places prevents.
- **A rule typed by whatever place matches its file.** Rejected. A rule would take the type of a place around it, and rules meant for that type would reach rules.
- **A less specific place typing an artefact that declines the winning type.** Rejected. An artefact in a component's place would fall through to a broader place, such as a root, and take a type its owner never meant.
- **A type registry of the project's own.** Not taken. The project declares its types on the places that give them, and validation checks a scope against those places. A registry would be a second list of the same names. The cost is that a misspelt bare type on a place makes a new type. A scope that names the intended type then misses that place's artefacts, unless no place gives the intended type, which fails the scope.
- **A finding for a typed place that types no artefact.** Not taken. A new place, or one whose artefacts have not yet declared their kind, types nothing for a while, and a finding would be noise.
- **Sub-types now**, such as a page's kind read from the kind field. Not taken now. No selection needs one yet. The kinds are the owner's vocabulary, so the backbone could not tell a misspelt sub-type from one that no artefact has yet.
- **Places in a functionality of their own now.** Not taken now. Types are the only concept beside friction's on places, and moving places is a surface change of its own. Point 7 says when it is due.

## Implications

- **The backbone ships** the type registry and a place's type in the package-metadata schema, and the typed place in the configuration schema. It also ships the resolution and its validation findings. It gives the one answer of point 6 in the machine-readable output of its reading commands.
- **Components that keep artefacts** may declare types and name them on their places. A component that tells its artefacts apart by other means can read the type from the one answer instead.
- **A component's release** may add a place, retype one, add a kind field, or withdraw a type or its admission of project places. Each changes which artefacts a project's scopes select, so each is a surface change of the component (COR-010).
- **Withdrawing or renaming a type** that a project may name breaks the project's state, so the release ships a migration with it (COR-010). The migration may rename the type on the project's places, a write the anchors-and-friction record names (COR-048 point 5). A scope that still names the old type fails validation, which names the fix.
- **Projects** may give types to their own places. A rule set that selects by type reaches only artefacts that some place types. So a project types its places before its sets rely on their types. A typed place is a new form of a place, so a project that writes one needs a backbone that knows it.
- **An install plan** reports a component that would bring a type whose name a bare project type already uses. The project renames its own type before it installs the component, or its validation fails.
- **Two records are refined in place,** atomically with this record's acceptance.
  - The anchors-and-friction record's points 1 and 14 admit a type on a place (COR-050). Point 14 also names the two writes this record adds. The uninstall takes a component's types off the project's places, and a component's migration may rename one there.
  - The rule-set record's scope also selects by `types`, and needs `paths` or `types`, so a scope may give `types` alone (COR-051 point 2).
- **Nothing that exists changes.** An untyped place keeps its meaning, and the type registry, a place's type and a scope's `types` are all optional additions. So no migration is due (COR-010).
- **The references** for package metadata, the backbone configuration and the schemas document the keys and their shapes.
