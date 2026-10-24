---
id: UC-024
title: See what a capability would connect to before I install it
status: active
actor: ACT-adopter
other-actors: []
after:
  - [UC-014, UC-049]
  - [UC-015, UC-048, environment]
requirements:
  - REQ-005
  - REQ-010
  - REQ-011
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/capability_plans.py
        - src/project_kit/status.py
        - src/project_kit/capabilities.py
      record:
        - COR-053#8
        - ADR-065#7
      artefact:
        - ACT-adopter
        - REQ-005
        - REQ-010
        - REQ-011
    revalidated:
      at: 2026-10-24T19:00:51Z
      outcome: unchanged
      unchanged-because: "As #2003 asks, the collision prompts now refuse an answer piped in off a terminal. Showing a capability's connections asks nothing, so the steps hold."
---

# UC-024 — See what a capability would connect to before I install it

**Goal:** See, before I install a capability, what it would connect to in my project and which conflicts I would have to resolve.

**Other actors:** None.

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-015 or UC-048, or Environment:** The [capability](../../../glossary.md#term-capability--capability)'s [package metadata](../../../glossary.md#term-package-metadata--package-metadata) is on the machine. The project authors the capability, or the [distribution](../../../glossary.md#term-distribution--distribution) of the running CLI ships it (COR-053 [point](../../../glossary.md#term-point--point) 8).

**Assumptions:** None.

**Trigger:** The adopter considers a [capability](../../../glossary.md#term-capability--capability) for the [project](../../../glossary.md#term-project--project), by its name or from a suggestion the status [report](../../../glossary.md#term-report--report) gives.

**Main path:**

1. The adopter runs `pkit status`.
2. Where the [project](../../../glossary.md#term-project--project)'s wiring has an unmet need, the [system](../../../glossary.md#term-system--system) suggests each [capability](../../../glossary.md#term-capability--capability) of the local catalogue that would meet it. It never uses the network (REQ-011). Such a need is a [data point](../../../glossary.md#term-data-point--data-point) nothing fills, a [role](../../../glossary.md#term-role--role) nobody provides or an upstream not installed.
3. The system prints `suggested          <n> from local catalogues (nothing is installed):`, then a line for each, such as `<point> (unfilled point): <name> (kit-shipped) contributes to it at version 1`. Each line names `pkit capabilities show <name>`, and a suggestion installs nothing (COR-053 [point](../../../glossary.md#term-point--point) 8).
4. The adopter runs `pkit capabilities show <name>`.
5. The system finds the capability in the local catalogue: installed, authored in the project, or shipped with the running CLI. It reads the capability's [package metadata](../../../glossary.md#term-package-metadata--package-metadata) alone.
6. The system prints the roles the capability provides, the data points it accepts and offers, and its extensions. Under `What connects here`, it gives the wiring the project would have with the capability installed.
7. The adopter runs `pkit capabilities install <name> --plan`.
8. The system computes the plan with the wiring resolver that builds the live wiring, over the project with the capability installed (COR-053 point 8). It prints `Install plan — capability '<name>' v<version> (<origin>)`, and that nothing is written.
9. The plan lists the connections the [install](../../../glossary.md#term-install--install) would make and break, the role conflicts to resolve and what the capability needs. It also lists the [findings](../../../glossary.md#term-finding--finding) the install would add, and those it would resolve.
10. The system writes nothing (REQ-005).

**Variants:**

- **1a.** The adopter knows the [capability](../../../glossary.md#term-capability--capability) already, and the path goes on at step 4.
- **2a.** The wiring has no unmet need, or no capability of the local catalogue meets one. The [system](../../../glossary.md#term-system--system) suggests nothing, and the path goes on at step 4.
- **4a.** The adopter passes `--json`, to `pkit capabilities show` or to the plan. The system prints the same view as a JSON document.
- **5a.** The local catalogue holds no capability of that name. The system refuses, saying where it looked and naming `pkit capabilities list`, and writes nothing. The use case ends.
- **7a.** The capability is installed already. The system refuses, naming `pkit capabilities upgrade <name>`, and the use case ends.
- **7b.** The capability is authored in the [project](../../../glossary.md#term-project--project), and does not ship with the running CLI. The plan refuses, since the [install](../../../glossary.md#term-install--install) takes only a capability that ships. Step 6 has shown its wiring, and UC-016 registers it.
- **7c.** The project is not the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository). The running CLI is at another [version](../../../glossary.md#term-version--version) than the project records, or a [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete. The plan stops as the install would (UC-023 variant 1c), names the remedy, and writes nothing (REQ-010).
- **9a.** A [role](../../../glossary.md#term-role--role) the capability provides is provided by another installed capability already. The plan lists the conflict as `<role> is provided by <providers> and none is selected; select one:`, with the command for each choice. After the install, the adopter chooses as UC-025 says.

**Postconditions:** The adopter knows, before installing, what the [capability](../../../glossary.md#term-capability--capability) would connect to in the [project](../../../glossary.md#term-project--project), what it needs and which conflicts the [install](../../../glossary.md#term-install--install) would leave. Nothing in the project has changed.

**Minimal guarantees:**

- Neither command writes anything, and a suggestion is never an action (COR-053 [point](../../../glossary.md#term-point--point) 8 and `capability_plans.py`).
- Under a CLI at another [version](../../../glossary.md#term-version--version) than the [project](../../../glossary.md#term-project--project) records, the plan stops, and never shows another [release](../../../glossary.md#term-release--release)'s wiring (ADR-065 point 7).
