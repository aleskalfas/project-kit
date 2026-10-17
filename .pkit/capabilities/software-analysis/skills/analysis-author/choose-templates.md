# Choosing each kind's parts

Adopting the capability includes choosing each kind's parts: the structure its template shows (DEC-001 point 1). The shipped parts are a starting point you review, never a default you skip. So choose a kind's parts before you write its first artefact, or its first record.

Go one kind at a time, in the order you write them: the actor, the use case, the journey, the term, then the record. For each kind you review its shipped parts, fill a candidate with one of your own examples, and choose. Each kind ends with its shipped parts kept, or with your relabels and additions in your `structures.yaml`.

**The choice is the project's.** An agent following this sub-procedure shows the person each filled candidate and the entries it proposes. It writes an entry or a rule only once the person accepts it.

## Before the first kind

Find the rule set of your own that inherits `SAN`. Installing the capability creates one, `ANALYSIS`, where none of yours inherits `SAN` already. Where install created none, write it as the README's "Where `SAN` binds: a set of your own" shows (COR-051). The format rule binds on an artefact only through such a set. Without it, `pkit analysis validate --preview` shows nothing of an artefact's structure. A record's structure is checked always.

## 1. Review the kind's shipped parts

- **The template** of the kind, in the capability's `templates` folder, is its structure rendered. It shows every part in its order, each with its hint and its example. A record's template shows each part's example alone, since a record has no hints.
- **The README's "The artefacts"** shows each kind filled.
- **The README's "Each kind's structure"** lists the parts that may read `None.`, and each part's form.

## 2. Fill a candidate with one of your own examples

A template read empty hides what each part asks of a writer. So judge the parts filled, with a case of your own.

- **Choose the example.** Take a real case from your project: a role, a goal, a path or a word you would write anyway. Prefer one that gives most parts something to say, such as a use case with other actors and variants. If it is unusual, fill a second, ordinary one too.
- **Stamp it and fill it** as the kind's sub-procedure says: `actor.md`, `use-case.md`, `journey.md`, `term.md` or `revalidation-record.md`. Fill each part as its hint says.
  - **A journey** needs two use cases of its actor, so stamp a second use case first. It can be your ordinary example.
  - **A revalidation record** has no hints, since its stamp writes every part from its command line. Stamp it for a revalidation of your own that has something to say, such as a change you plan to what a candidate describes.
- **Commit nothing yet.** The kind's sub-procedure ends in a commit, but a candidate waits until step 6. Once committed, its id is taken for good.
- **Check it** with `pkit analysis validate --preview`, and read what it says of your candidate. While the format rule is proposed, the preview shows an artefact against its kind's structure where the rule would bind.

## 3. Judge each part

Read the filled candidate part by part, as its reader will.

- Did your example fill the part without strain?
- Does the part only repeat another part, or a record it cites?
- Is something your project needs to say left with no part for it?
- Does a label or a hint not fit your project, such as its language or its voice?

A part that reads `None.` in your example may still earn its place: `None.` says the writer considered it.

## 4. Choose

Choose one of these for the kind, or several. Nothing lets you drop, loosen or reorder a shipped part. The README's "A project's own structures" gives the shape of each entry, where it goes and when it binds.

- **Keep the shipped parts.** You write nothing for the kind.
- **Relabel a part, or replace a hint and its example.** Write it under the kind's `relabel`, or its `front-matter` for a field. This needs no rule, since a label and a hint tighten nothing.
- **Add a part of your own,** to an artefact kind. Write a group under the kind's `tighten`, naming the rule of your own set that asks for the part. Write the rule first, proposed.
  - The part binds once its rule and the format rule are both accepted, where both bind.
  - An added part is stamped into every new artefact of the kind, with its hint. So add one only where your examples show it recurs.
  - A group may also close the kind's list of labels, where its parts hold no labels of their own.
  - A revalidation record takes no added part, since no rule binds on a record.
- **Propose a change to a shipped part you find wrong.** It is a change to the capability, so file it with `pkit report change-request`, through the `report-author` skill. Keep the part meanwhile.

Your entries go in `.pkit/capabilities/software-analysis/project/structures.yaml`, a file of your own that sync never touches.

## 5. Fill the candidate again

Do this if you wrote any entry in step 4.

1. **Check the file** with `pkit validate`, and mend each error it reports on it.
2. **Set the first candidate aside.** Move it out of the analysis, to a file you do not commit, such as one in the agent workspace. You compare the two below. Out of the analysis, a candidate never committed holds no id.
   - **A term** is an entry of the glossary. Copy the entry out, then delete it, or the glossary itself where its stamp created the file.
3. **Stamp the candidate again**, as before. The stamp writes your parts, each added part's hint naming its rule. An actor or a term gets the same id. A use case or a journey gets the next free number.
4. **Fill it, and check it** with `pkit analysis validate --preview`. The preview places a part whose rule is still proposed where that rule would bind.
5. **Compare the two candidates,** filled, side by side. Keep the entries that read better, and repeat from step 1 if you change them.

## 6. End the kind

The kind's parts are now chosen: the shipped parts kept, or your relabels and additions in your `structures.yaml`.

- **The candidate.** Keep it if it describes your project truly: an artefact you would write anyway, or a revalidation that happened. It is then the kind's first artefact, or its first record. Delete any other before you commit, so it takes no id.
- **A candidate set aside** in step 5 is deleted too.
- **Commit** your `structures.yaml` and the candidate you keep, per COR-008.

Then go to the next kind.
