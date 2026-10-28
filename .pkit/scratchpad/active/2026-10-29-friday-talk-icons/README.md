# Icons

Role icons for the diagram sketches, made by a script from Carbon pictograms and recoloured to the board's role colours.

- Source: `@carbon/pictograms` 12.85.0 (npm, via cdn.jsdelivr.net), licence Apache-2.0, IBM Carbon Design System.
- Pictograms: `code` → `code.png` (role_code), `review-checklist` → `checks.png` (role_checks), `robot` → `agents.png` (role_agents), `person--01` → `people.png` (role_people).
- Colour: each SVG's fill set to its role colour from the map's theme; rendered to 384 px PNG with rsvg-convert.
- Reader icons (added 2026-09-30, same package and version): `data--scientist` → `experimenter.png` (role_experimenter #8A3800), `access-management` → `admin.png` (role_admin #00539A); rendered at 384 px by `build_three_parts.py`.
- Flow icons (added 2026-09-30 for slide 10 and the phase slides, same package and version): `analyze--code` → `check.png` (role_checks), `report` → `report.png` (role_neutral), `documentation` → `rules.png` (role_neutral), `continuous--integration` → `merge.png` (role_neutral), `distribution--ledger` → `debt.png` (role_neutral), `calendar` → `schedule.png` (role_neutral), `calendar` → `schedule-muted.png` (text_helper), `upload--01` → `push.png` (role_neutral), `systems-devops--code` → `pr.png` (role_neutral), `code` → `repo.png` (role_code), `code` → `fix.png` (role_agents); actor icons rendered at 384 px, artefact icons at 256 px, by `make_flow_icons.py`.
- Project logo (added 2026-10-01 for the cover, D31): `mockingbird-logo.png` rendered from the mockingbird repo's own `docs/assets/bird-blue.svg` (the file behind https://github.ibm.com/ai-platform-incubation/mockingbird/blob/main/docs/assets/bird-blue.svg), colours unchanged, at 512 px high (1048 × 512) with rsvg-convert, drawn at 262 × 128 on the cover.
