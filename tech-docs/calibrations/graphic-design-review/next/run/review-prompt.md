# The prompt each review is given

Each review in each run is given this prompt and nothing else. `<FOLDER>` is replaced by its folder's path, which `layout.py` names by a fresh code, `<PIECE>` by the piece's name, as `reference.json` gives it, and `<N>` by its number of pages. No other word changes between reviews. Each outside judge's folder holds the same files, byte for byte (`judge-brief.md`).

---

Review the piece whose pages are drawn in `<FOLDER>`.

What you are handed:
- `page-1.light.png` to `page-<N>.light.png`, and `page-1.dark.png` to `page-<N>.dark.png`: each of the piece's pages in its light and its dark mode.
- `handed.md`: who the piece is for, where it is shown, that it explains, its pages' ids in order, and the intent the intent command gives for it.
- The piece's content file, which `handed.md` names: each page's words and the visual it asks for, in the pages' order.

Nothing else is handed: no viewing step's report, no frames, and no brand, brief or source file. So no check has measured any of these images.

Grade each page, and the piece as a whole, as your instructions say, and give your report in their form. The review's document comes first, as a fenced YAML block, with `piece: <PIECE>` and `round: 1`. It names each page by the id `handed.md` gives it, and your model by its full name. List under `read-before-grading` each file you read before you graded, by its path. Where nothing of a kind was handed, say so, and name no file.

Read only the files in `<FOLDER>`, and the rule sets, design knowledge and schemas your instructions have you read. Read nothing else under `.agent-workspace/`, and no other folder of images.
