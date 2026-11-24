# The prompt each review is given

Each review in each run is given this prompt and nothing else. `<FOLDER>` is replaced by its review folder's path, which `layout.py` names by a fresh code. No other word changes between reviews.

---

Review the piece whose pages are drawn in `<FOLDER>`.

What you are handed:
- `page-1.light.png` to `page-4.light.png`, and `page-1.dark.png` to `page-4.dark.png`: each of the piece's four pages in its light and its dark mode, 1600 × 900 pixels.
- `handed.md`: who the piece is for, where it is shown, that it explains, its pages' ids in order, and the intent the intent command gives for it.

Nothing else is handed: no viewing step's report, no frames, and no piece, content, brand or brief file. So no check has measured any of these images.

Grade each page, and the piece as a whole, as your instructions say, and give your report in their form. The review's document comes first, as a fenced YAML block, with `piece: ladder-scratch` and `round: 1`. It names each page by the id `handed.md` gives it, names your model by its full name with its effort, and lists under `read-before-grading` each file you read before you graded.

Read only the files in `<FOLDER>`, and the rule sets and design knowledge your instructions have you read. Read nothing else under `.agent-workspace/`, and no other folder of images.
