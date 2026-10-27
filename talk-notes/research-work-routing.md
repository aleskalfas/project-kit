# Routing work to a set of workers: established patterns

How mature systems control (1) what any worker may take at all and (2) optional per-worker specialisation. Each claim links the system's own docs. Lines marked *inference* are mine.

## Pattern 1: named queues that workers subscribe to (Celery, Sidekiq, Temporal)

- **Unit:** a named queue. The producer routes each item at enqueue time, by call arguments, task attributes or a router table ([Celery routing](https://docs.celeryq.dev/en/stable/userguide/routing.html)).
- **Binding:** the worker lists the queues it consumes (`-Q`). In Temporal "any Worker can pick up any Task on a given Task Queue", so a queue's workers must be alike ([Temporal task queues](https://docs.temporal.io/task-queue)); specialising means another queue, up to one "for each Worker Process" ([Temporal task routing](https://docs.temporal.io/task-routing)).
- **Pitfalls:**
  - A Celery worker started without `-Q` "will consume from all queues defined in the task_queues setting" ([Celery workers](https://docs.celeryq.dev/en/stable/userguide/workers.html)).
  - Queues are created on demand in both systems ([Celery](https://docs.celeryq.dev/en/stable/userguide/routing.html), [Temporal](https://docs.temporal.io/task-queue)). *Inference:* a misspelt or renamed queue becomes a new, empty queue that no worker polls.
  - Under Sidekiq's strict ordering, a lower queue runs only when the higher ones are empty. Its docs advise no more than "a handful of queues per Sidekiq process" ([Sidekiq advanced options](https://github.com/sidekiq/sidekiq/wiki/Advanced-Options)).

## Pattern 2: an access gate plus label matching (GitHub Actions, Buildkite, GitLab, Jenkins)

- **Unit:** one pool of jobs. Each job carries requirements, and each worker carries labels.
- **Gate:** GitHub *runner groups* limit which repositories may use a set of runners ([runner groups](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access)). Buildkite's `queue` tag "can be used for isolating jobs and agents" ([Buildkite agent start](https://buildkite.com/docs/agent/v3/cli/reference/start)).
- **Narrowing:** a match needs every label: runners "that have all the labels that you specify", and with a group as well, "the runner must meet both requirements" ([choosing the runner](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job)). Buildkite and GitLab work the same way; a GitLab runner "must have all of the tags defined in the job" ([GitLab runners](https://docs.gitlab.com/ci/runners/configure_runners/)).
- **Reservation:** this is a separate switch. A Jenkins node set to "Only build jobs with label expressions matching this node" is kept for jobs that name it ([Jenkins usage help](https://raw.githubusercontent.com/jenkinsci/jenkins/master/war/src/main/webapp/help/system-config/master-slave/usage.html)). GitLab's "Run untagged jobs" checkbox decides whether a runner takes jobs that carry no tags.
- **Pitfalls:**
  - **Defaults are open.**
    - A Jenkins node defaults to "Use this node as much as possible" ([Jenkins messages](https://raw.githubusercontent.com/jenkinsci/jenkins/master/core/src/main/resources/hudson/model/Messages.properties)).
    - A GitHub runner registered without a group joins the default group automatically.
    - A Buildkite agent without a queue joins the default queue.
  - **Stuck work.** In GitLab, an untagged job that no runner accepts sits "stuck".
  - **Unchecked labels.** GitHub "does not validate" what a label claims about a runner. Unused labels are deleted within 24 hours ([labels](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/apply-labels)).

## Pattern 3: scheduler placement with attract and repel (Kubernetes)

- **Narrowing:** a `nodeSelector` (or required node affinity) places a pod only on nodes "that have each of the labels you specify". Preferred affinity is a soft version ([assigning pods](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)).
- **Reservation:** a taint makes a node repel pods that do not tolerate it ([taints](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)). The documented "Dedicated Nodes" recipe needs both halves. The taint keeps other pods off. A label plus required affinity makes the dedicated pods "*only* use the dedicated nodes".
- **Pitfall:** isolation labels must be ones the worker "cannot modify", or a compromised node labels itself into the workload ([assigning pods](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)).

## Pattern 4: a human commitment point, then pull (Kanban, Scrum, Linear)

- **Kanban:**
  - The commitment point is "the point at which the decision is made to start activities to deliver a work item" ([Kanban University glossary](https://kanban.university/glossary/)).
  - Replenishment is "reviewing the requested work items that fulfill the 'ready for delivery' criteria" (same glossary).
  - A pull system delivers "only when both demand exists and delivery capacity is available" (same glossary; see also the [Kanban Guide](https://kanbanguides.org/english/)).
- **Scrum:** items become "ready for selection". In Sprint Planning, the Developers "select items from the Product Backlog" into the Sprint Backlog, "a plan by and for the Developers" ([Scrum Guide](https://scrumguides.org/scrum-guide.html)).
- **Linear:** Triage is an inbox. Only *Accept* moves an issue into the team's workflow ([Linear triage](https://linear.app/docs/triage)).
- **Specialisation:** in all three it comes from who pulls; the selected set is not split.

## Multi-agent AI (documented systems)

- **Claude Code agent teams:** one shared task list. A teammate "picks up the next unassigned, unblocked task", with file locking on the claim. The only documented controls are assignment by the lead and dependencies; no per-teammate filter ([agent teams](https://code.claude.com/docs/en/agent-teams)).
- **GitHub Copilot coding agent:** a person pushes each task to it, for example from an issue. Nothing is pulled ([about coding agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent)).

## Distilled

1. **Gating and narrowing are separate layers.** GitHub: group, then labels, both required. Buildkite: queue, then tags. Kubernetes: taints repel, selectors attract. Kanban: one commitment point, then people specialise as they pull. No system I found puts "what may be taken at all" only in each worker's own declaration.
2. **Per-worker gating fails open.** Jenkins, Celery, GitHub and Buildkite all default an unconfigured worker to "take anything": the "seat added without a scope takes everything" failure.
3. **Named queues fit producer-side routing by kind of work, not a person curating a set.** They bring one homogeneous pool per queue, starvation under strict order, and silent empty queues after a typo.
4. **Reservation is a third, explicit switch.** Narrowing a specialist does not keep generalists off its work; that takes a taint, Jenkins's exclusive mode, or GitLab's "run untagged" turned off.

**Fit for "a person decides what is ready; workers pull; some specialise":** the evidence favours perspective B with layers.

- **One gate for the whole pool, set by the person** (a milestone as the commitment point, like Sprint selection or Linear's Accept), held once in committed configuration and failing closed: no gate, nothing taken.
- **Optional per-seat narrowing inside the pool,** where every condition must match.
- **Reservation only if needed, as an explicit opt-in.**

**Checks to carry over:**
- Warn when a gated item matches no seat (GitLab's stuck job).
- Check gate and label names against ones that exist (on-demand queues, labels deleted when unused).
- Keep the gate in configuration the worker cannot change (Kubernetes's isolation-label rule).
