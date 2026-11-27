# The lean-business test sample

`.repo/` holds a small project's ideas, which the lean-business tests read and copy. It lies in a hidden folder so that neither the data validation of `pkit validate` nor the lean-business check reads its files as this repository's own ideas: a copy of a document, such as a fixture, keeps an id of its own or lies outside the scope validation reads (COR-029 point 6), and that scope skips every hidden folder (the CLI README, the `data` row of `pkit validate`'s members).
