# doc-examples capability

A page that shows a command and what it prints makes a claim about your software's behaviour. Its anchors flag it when what it anchors changes, but not when code it never names changes what the command prints. This capability runs each such example as a test, so the example fails your checks wherever the change comes from. Install it when your pages show console output.

The capability is being built. Its first record, [doc-examples:DEC-001-console-examples-as-tests](decisions/DEC-001-console-examples-as-tests.md), is proposed, and nothing it describes ships yet.

## What this capability ships

- `decisions/DEC-001-console-examples-as-tests.md`: how a page's console examples run as tests, proposed

## Adopter setup

Install:

```
pkit capabilities install doc-examples
```

Nothing more to set up yet.

## Citing this capability's decisions

Inside this capability's own content, cite decisions by their filename stem: `[doc-examples:DEC-001-console-examples-as-tests]`. Other capabilities and adopter content use the same form.

## Dependencies

None yet.
