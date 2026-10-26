---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/doc-examples/scripts/**
        - .pkit/capabilities/doc-examples/schemas/**
        - .pkit/capabilities/doc-examples/permissions/**
        - .pkit/capabilities/doc-examples/package.yaml
      record: ["doc-examples:DEC-001", COR-001, COR-010, COR-017, COR-028, COR-030, COR-050, COR-055, COR-056, "living-docs:DEC-001", "living-docs:DEC-002"]
      artefact: [".pkit/permissions/README.md#grants-and-verdicts"]
---

# doc-examples capability

A page that shows a command and what it prints makes a claim about your software's behaviour. Its anchors flag it when what it anchors changes, but not when code it never names changes what the command prints. This capability runs each such example as a test, so the example fails your checks wherever the change comes from. Install it when your pages show console output.

The rule is in [doc-examples:DEC-001-console-examples-as-tests]. This page states the contract a page is written against, which is the capability's versioned surface ("Changes to the contract" below).

<!-- pkit:contents -->
- [What this capability ships](#what-this-capability-ships)
- [Adopter setup](#adopter-setup)
- [A page's examples](#a-pages-examples)
- [How a fence runs](#how-a-fence-runs)
- [What is compared](#what-is-compared)
- [Placeholders](#placeholders)
- [The configuration](#the-configuration)
- [The run](#the-run)
- [An update](#an-update)
- [The guards, and what the run confines](#the-guards-and-what-the-run-confines)
- [In CI](#in-ci)
- [The permission model](#the-permission-model)
- [Validation](#validation)
- [Changes to the contract](#changes-to-the-contract)
- [Not yet](#not-yet)
- [Citing this capability's decisions](#citing-this-capabilitys-decisions)
- [Dependencies](#dependencies)
<!-- /pkit:contents -->

## What this capability ships

- `decisions/DEC-001-console-examples-as-tests.md`: how a page's console examples run as tests
- `scripts/run-examples.py`: the run, a program you start by its path ("The run" below)
- `scripts/pages.py`: `pkit doc-examples pages`, which lists the pages the run reads
- `scripts/validate.py`: `pkit doc-examples validate`, which checks the run's configuration and the form of each fence ("Validation" below)
- `schemas/config.yaml` and `schemas/config.schema.json`: the shape of your configuration ("The configuration" below)
- `permissions/privilege-catalog.yaml`: the privilege `doc-examples:run-examples`, which recognizes a call to the run ("The permission model" below)

## Adopter setup

1. Install the capability:

   ```
   pkit capabilities install doc-examples
   ```

2. Say how the run builds your scratch project, in `.pkit/capabilities/doc-examples/project/config.yaml` ("The configuration" below). Examples that need nothing installed need no setup.
3. Show each example in a `console` fence on a page ("A page's examples" below).
4. Run the examples, and write the output the page lacks with `--update` ("An update" below):

   ```
   python3 .pkit/capabilities/doc-examples/scripts/run-examples.py --update
   ```

5. Once your pages pass, make the run a check your CI runs ("In CI" below).

## A page's examples

A page shows a command after the prompt `$ `, and what it prints below it, in a `console` fence:

````markdown
```console
$ mytool --version
mytool <VERSION>
$ mytool greet world
Hello, world!
```
````

- **Which pages:** the documents of the types your configuration names under `types`. Without `types`, the pages are the documents of living-docs' page type, `living-docs:page`, where living-docs is installed.
  - **A page is a document,** never an entry of a collection. A document is an artefact only where it has front matter and lies in a declared place (COR-050 point 1). So a file you want run needs both, even a top-level README.
  - **A page of your own kind:** give the place that holds such pages a type of your own in `friction.places`, and name that type (COR-056 point 2).
  - **What the default misses:** living-docs also counts as a page a document of no type that declares its page kind outside every root. The default misses such a page until you type its place.
- **Which fences:** a fenced block whose info string's first word is `console`, wherever Markdown nests it, in a list item or a block quote too. A fence of any other language never runs.
- **Another name for a shell session:** a fence named `shell-session`, `shellsession`, `sh-session`, `bash-session`, `tcshcon`, `doscon`, `ps1con` or `pwsh-session` never runs. The run and validation report it, and it fails nothing.
- **How a fence reads:** a line that opens with `$ ` is a command. The lines after it, up to the next command, are its output. A line before the first command, or a fence with no command, fails the fence.
- **A command that cannot run as a test:** put it in a fence of its shell's language, such as `sh`, with no output.

## How a fence runs

- **One shell for a fence:** a fence's commands run in order, in one POSIX shell, `/bin/sh`, from the scratch project's root. So a `cd` or a variable carries over to the next command, as it does for a reader who types them. Each command's input is closed.
- **The scratch project:** your setup step builds it once for each run ("The configuration" below). Each fence starts from the project and its home as the setup left them, at the same paths, and from an empty temporary folder. So no fence sees what another left.
- **The environment:** a command gets an environment the run builds, and nothing else of yours. It holds your `PATH` behind the folders you name, the variables you name, and the settings the run fixes.
  - **The settings the run fixes:** `HOME`, the scratch home, and `TMPDIR`, the temporary folder. Then `LANG=C`, `LC_ALL=C`, `TERM=dumb` and `NO_COLOR=1`.
  - **The run's value wins** over a variable you name with one of these names, or with `PATH`.
  - **No tool reads your configuration** through `HOME`, since `HOME` is the scratch home.
- **The limits:** a command of a page may run 60 seconds, which `--timeout` changes, and print 1 MiB. A command of the setup step or of a placeholder may run 600 seconds, which `--setup-timeout` changes.
  - **A command past a limit** is stopped, with every process left in the fence's shell. So is the command running when you interrupt the run.
  - **A stopped command** fails its fence, and the fence's later commands do not run.
  - **A command that ends the shell,** such as `exit`, does the same to the fence's later commands.

## What is compared

- **The output:** what each command printed, its standard output and error together, in the order it wrote them to one pipe, with no terminal.
- **Left out on both sides:** the spaces that end a line, and the blank lines that end the output.
- **The exit status** is not compared. A page that means a status shows it, as `$ mytool check; echo $?` does.
- **What varies:** before comparing, the run writes a placeholder in place of each text that varies from run to run ("Placeholders" below).

## Placeholders

The run's placeholders take lower-case names, and yours take upper-case names, such as `<VERSION>`. So a placeholder the run adds later never takes the name of one of yours.

- **The run's folders,** wherever a command prints one:
  - `<project>`: the scratch project
  - `<home>`: the scratch project's home
  - `<tmp>`: the fence's temporary folder
  - `<scratch>`: the run's scratch area, which holds the three
  - `<repository>`: your repository
- **Any text:** in a page's output, `<any>` stands for any text within one line.
- **Yours:** each placeholder you declare stands for the one line its command prints ("The configuration" below).
- **A value of yours:** where a variable takes your value, the run writes that value as the variable's name in upper case, such as `<GH_TOKEN>`. So an update never writes your value into a page. An empty value is written nowhere.

How a text is matched:

- **The longest text first:** the run replaces every text in one pass, the longest first. So no text is replaced inside a longer one, or inside a placeholder already written.
- **A folder, anywhere:** a folder is replaced wherever it stands, both as the run names it and with its links resolved.
- **Your text and your values, where they stand whole:** never as part of a longer word or number.
  - A text that opens with a digit stands whole unless a digit or a dot comes before it. One that ends with a digit stands whole unless a digit, or a dot and a digit, come after it. So `1.2.3` is replaced in `v1.2.3`, but not in `11.2.3` or `1.2.3.4`.
  - A text that opens or ends with a letter or an underscore stands whole unless a letter, a digit or an underscore comes beside it on that side. So `acme` is replaced in `acme-cli`, but not in `acme_cli` or `acmes`.
  - A text that opens or ends with any other character has no condition on that side.

## The configuration

Your configuration is `.pkit/capabilities/doc-examples/project/config.yaml`, in the capability's project tier, which a sync never touches. Its shape is `schemas/config.schema.json`, and every key is optional:

```yaml
pkit_schema: doc-examples:config
schema_version: 1

types: [living-docs:page]

setup:
  - git config --global user.name "Doc Examples"
  - git init -q
  - python3 -m venv .venv
  - .venv/bin/pip install --quiet "$DOC_EXAMPLES_REPOSITORY"

path: [<project>/.venv/bin]

environment:
  GIT_CONFIG_GLOBAL: <home>/.gitconfig
  PIP_CACHE_DIR: <scratch>/pip-cache
  GH_TOKEN:

placeholders:
  VERSION: cat "$DOC_EXAMPLES_REPOSITORY/VERSION"
```

- **`types`:** the types whose documents are your pages: a component's type in full, or a bare type of your own that a place gives ("A page's examples" above).
- **`setup`:** the commands that build the scratch project. They run once for each run, in order, in one shell, in an empty folder with a home of its own.
  - **Your repository's path** is in `DOC_EXAMPLES_REPOSITORY`, for these commands and the placeholders' commands alone.
  - **A command that fails,** or writes in your repository, stops the run before any page's command runs.
  - **A build that writes beside its sources,** such as one that leaves an `egg-info` folder, writes in your repository. Copy the sources into the scratch project first, and build from the copy.
- **`path`:** the folders put before your `PATH`, in order.
- **`environment`:** the variables every command gets, each with a value or with none.
  - **A value** may name the run's folders by their placeholders, such as `<scratch>/pip-cache`.
  - **No value** takes your value of that name, and the variable is left out where you have none.
- **`placeholders`:** each name in upper case, with the command that prints the one line of text it stands for, such as your product's version.
  - **When it runs:** once, after the setup step, in the scratch project.
  - **A command that fails,** or prints no text or more than one line, stops the run before any page's command runs.

## The run

From your repository's root:

```
python3 .pkit/capabilities/doc-examples/scripts/run-examples.py              # every page
python3 .pkit/capabilities/doc-examples/scripts/run-examples.py README.md    # the pages named
python3 .pkit/capabilities/doc-examples/scripts/run-examples.py --update     # write new output
```

- **What it needs:** Python 3.10 or later, with its standard library alone, and a POSIX system. It reads the pages and your configuration through `pkit doc-examples pages --json`, so it needs `pkit` on `PATH`.
- **Its options:** the pages to run, `--update`, `--timeout SECONDS` and `--setup-timeout SECONDS`. A page named that is not among the pages stops the run.
- **Its report:** each finding at its page's line, with a diff of the page's output and the run's, then a summary line. The report shows a control character as an escape, and a value of yours as its placeholder.
- **Its exit statuses:**
  - `0`: every fence matches, no page holds one, or `--update` wrote every output that differed
  - `1`: a fence fails
  - `2`: the run cannot start: a selection it cannot read, a setup step or a placeholder's command that fails, or a page it cannot read

## An update

`--update` writes each command's new output into its page, and keeps each line of the page's output that still matches, `<any>` included. Review the new output as any change to the page (living-docs DEC-002 point 6).

- **What it never writes:** output with a line that would read as a command or close the fence, so nothing a command prints becomes a command of the next run. Nor output with a line that holds `<any>`, which the next run would read as any text. Nor output with a control character, such as a carriage return or a terminal escape, or with a value of yours anywhere in a line.
- **When it writes:** only once every page's commands have run with no write in the repository. A page that changed since the run read it is not written, and the run reports it.

## The guards, and what the run confines

- **Every command:** the guards hold for each command the run starts, whether of the setup step, of a placeholder or of a page.
- **A write in the repository:** the run lists each file and folder of your repository before the setup step and after each command, and compares each list with the one before it. It lists them again once a fence's shell is stopped, and before it writes any page. So a write by a process a command left is seen too.
  - **A path added, removed or changed** fails the test and stops the run, and no page is updated.
  - **Left out:** the repository's git directory, since any process that reads the repository's state may write there. So is what lies inside a folder that holds a repository of its own, such as a linked worktree. The folder itself is listed, so a new one is seen.
  - **Another process's write** in the repository is taken for the command's that ran when the run saw it.
- **The scratch area** lies outside the repository, in the system's temporary folder, and is removed after the run.
- **What it confines:** nothing. A command runs as you, and reads and reaches what you can, the network included. The guards keep a mistaken page from harming your checkout, and stop no command written to do harm.
- **So a page's commands are code your project runs,** and so are the setup step and the placeholders' commands. Review a change that adds or alters one as you review a change to a test.

## In CI

Run the program by its path from the repository's root, beside your tests, with `pkit` installed and `pkit sync` run. `pkit sync` provisions the CLI's queries, `pages` among them. A GitHub Actions step:

```yaml
- name: Console examples
  run: python3 .pkit/capabilities/doc-examples/scripts/run-examples.py
```

Add the step once your pages pass, after an update has written their output and you have reviewed it. A person runs the same program at a desk, on every page or on the pages named.

## The permission model

**The run's commands lie below the permission model.** The permission model decides each call an agent or the operator makes through a harness (COR-028). It decides the call that starts the run, and never a command the run starts. So whatever allows that call allows every command of the setup step, the placeholders and the pages.

- **No shipped grant allows the run:** the run is no command of `pkit`, so no grant of the CLI allows a call to it. Nor does any other grant the methodology ships, nor the core settings an adapter merges into your harness. Your harness's own rules decide such a call.
- **A privilege of its own:** `doc-examples:run-examples` recognizes the call by the program's path relative to the folder the call runs in, alone or after `python3` or `python`. No grant of it ships. To let an agent run your pages' examples, grant it by name in `.pkit/permissions/project/grants.yaml`:

  ```yaml
  - subject: agent:docs-writer
    privilege: '[privilege-catalog:doc-examples:run-examples]'
    effect: allow
  ```

- **What a grant of it reaches:** the permission model sees no folder in such a path, and reads a leading `cd` as no change of folder. So a grant also allows a program at that relative path under any folder the grantee can enter, one it wrote included. Grant it only to whom you would let run a program of its own.
- **Grants that reach the run anyway:** a grant of a wrapper that runs any program, such as `uv run`, allows the run through that wrapper. So does a grant of a version-control command whose hook starts the run.
- **A sandbox:** inside an operating-system sandbox, the run's commands are confined as the call is. Where the call runs outside one, so do they.

## Validation

`pkit doc-examples validate` checks your configuration and the form of each fence. `pkit validate` runs it as its member `doc-examples:examples` (COR-055 point 3).

- **Errors,** which fail validation, are what would stop the run or fail a fence before its first command:
  - a selection the run cannot read: no `types` and no living-docs, or a type no installed component declares and no place of yours gives
  - a placeholder of yours whose name is not in upper case
  - two placeholders of your form with one name, such as a variable that takes your value under the name of a placeholder of yours
  - a fence that cannot be read
  - a configuration of another shape
- **A warning,** which fails nothing: a fence under another name for a shell session.

`pkit doc-examples pages` lists the pages the run reads. It refuses, naming the fix, where your configuration holds an error.

## Changes to the contract

What this page documents of the fences, how a fence runs, what is compared, the placeholders, the configuration and an update is the capability's versioned surface. So are the run's exit statuses, path and options (DEC-001 point 6).

- **A breaking change:** a change that would fail a page that passed, or pass a page that failed, is a new major of the capability (COR-010). A fix that brings the run back to this contract is no breaking change.
- **Your pages after a breaking change:** where they can be rewritten mechanically, as for a renamed placeholder, the release ships a migration that rewrites them. Otherwise its notes say what to change, and the run's failures show where.
- **The program's path and options only grow:** your CI names them, and no migration reaches your CI. So the path never changes, and no option is removed or given another meaning.

## Not yet

**No results are kept.** A run's result is its exit status and its report, which nothing keeps. So its results reach no connection point yet, such as living-docs' reading evidence (living-docs DEC-001 point 7). A record of its own will decide where kept results live.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[doc-examples:DEC-001-console-examples-as-tests]`. Other capabilities and adopter content use the same form.

## Dependencies

- **Backbone:** `>=1.149.0,<2.0.0`.
- **living-docs,** optional: its page type is the default selection (COR-030). Without it, name your pages' types.
- **uv,** which runs the CLI's two queries.
