---
id: UC-xxx
title: Land a change on the default branch
status: active
actor: ACT-developer
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/pull_request_landing.py
        - src/project_kit/friction_check.py
        - src/project_kit/session_guard.py
      record: [COR-009, COR-050, COR-055, ADR-061]
      artefact: [ACT-developer]
---

# UC-xxx — Land a change on the default branch

The developer runs `pkit validate` and the change check, `pkit friction check`, on the change's branch. Once both pass, they push the branch and open a pull request titled `<type>(<scope>): <description>`. The CI pipeline runs the checks the project requires. The merge authoriser is shown the change check's list of the answers the change wrote, word for word, and authorises the merge.

The developer then runs `pkit pull-request land <n> --head <sha> --subject "<title>"`, naming the commit the checks passed on. The system checks that the base's merge queue squashes, with the pull request's title and body as the commit's. It hands the pull request to the queue, pinned to that commit, and waits until it merges. Last, the developer deletes the head branch with `pkit pull-request delete-branch`, which deletes it only at the head that merged.

A developer who works alone may commit straight to the default branch instead, with a conventional message, once the same checks pass. Where an agent wrote answers, the developer sees the change check's list before committing. On a base with no merge queue, the system squash-merges directly, and the commit's body is still the repository's default (#1220).

A push after the checks stops the landing: the system takes the pull request out of the queue, and the checks run again. A queue that does not squash is refused before anything is sent. In a repository other than the session's, the guard asks first, or refuses where nobody can answer. A branch that moved after the merge, or that another pull request uses, is kept.

When the queue drops the pull request, the developer lands it again, with `--allow-dropped-head` where no new commit is needed. When the wait runs out, or a request gets no usable answer, running the landing again picks up where it stood. A failing check, an outdated base or an answer written after the authorisation sends the developer back to the checks or to the merge authoriser. A project that requires no check on its pull requests skips the pipeline's run.
