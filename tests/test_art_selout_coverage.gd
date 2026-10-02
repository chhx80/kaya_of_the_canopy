extends TestCase
## Phase E, docs/plan-art-motion.md: selout coverage — "a test that every
## sprite sheet the generators produce went through the selout pass."
##
## The smallest honest mechanism, per the plan's own instruction: not a pixel
## probe (selective_outline() already has one of those, scoped to a single
## before/after diff at build time — see tools/art/sprites.py's Phase C
## report) but a build-path record. `tools/art/palette.py::sheet()` now logs
## every call's name and its `selout` flag into `SELOUT_LOG`, and
## `write_selout_manifest()` (called last in `tools/gen_art.py::main()`, after
## every builder has run) dumps it to `assets/selout_manifest.json`. This test
## reads that file back — it cannot drift from what the generator actually
## did, because it IS what the generator did, not an inference from pixels.
##
## Every character sheet (the four player forms, eight non-boss enemies, five
## bosses) is on the CHARACTER allowlist and must read `true`. The four icon
## sheets (blade, pickups, props, projectiles) are excluded on purpose — Phase
## C's own docstring in `palette.py::sheet()` names them — and must read
## `false`, so a sheet quietly added to that exclusion list is still visible
## here rather than invisible by merging into "not mentioned at all".
## `test_the_manifest_has_no_stragglers()` closes the last gap: a sheet that
## is neither on the allow- nor the exclude-list (a new generator forgot
## both) fails loudly instead of passing by omission.

const MANIFEST := "res://assets/selout_manifest.json"

const CHARACTER_SHEETS: Array[String] = [
	"kaya_human", "kaya_frog", "kaya_fish", "kaya_bird",
	"enemy_walker", "enemy_jumper", "enemy_shooter", "enemy_swimmer",
	"enemy_charger", "enemy_dropper", "enemy_flyer",
	"boss_grove", "boss_stormcrest", "boss_tide_maw", "boss_brood_queen",
	"boss_obsidian_heart",
]

## Named in tools/art/palette.py::sheet()'s own docstring as the deliberate
## exclusion: small icon sheets, not silhouettes against a background.
const EXCLUDED_SHEETS: Array[String] = ["blade", "pickups", "props", "projectiles"]

var _manifest: Dictionary = {}

func before_each() -> void:
	if not _manifest.is_empty():
		return
	var raw := FileAccess.get_file_as_string(MANIFEST)
	ok(not raw.is_empty(), "%s must exist — run tools/genart.sh" % MANIFEST)
	var parsed: Variant = JSON.parse_string(raw)
	if parsed is Dictionary:
		_manifest = (parsed as Dictionary).get("sheets", {})

func test_every_character_sheet_went_through_selout() -> void:
	for name: String in CHARACTER_SHEETS:
		ok(_manifest.has(name), "manifest has no entry for '%s'" % name)
		if not _manifest.has(name):
			continue
		ok(bool(_manifest[name]), "'%s' did not go through selective_outline()" % name)

func test_every_excluded_sheet_is_deliberately_not_selout() -> void:
	for name: String in EXCLUDED_SHEETS:
		ok(_manifest.has(name), "manifest has no entry for '%s'" % name)
		if not _manifest.has(name):
			continue
		not_ok(bool(_manifest[name]),
			"'%s' is on the deliberate exclusion list but now reads selout=true — \
update EXCLUDED_SHEETS if that was an intentional change" % name)

## No sheet the generator produces may be silent about selout: every key in
## the manifest has to be on one list or the other, so a new sheet always
## states which bucket it falls in.
func test_the_manifest_has_no_stragglers() -> void:
	for name: String in _manifest.keys():
		ok(CHARACTER_SHEETS.has(name) or EXCLUDED_SHEETS.has(name),
			"'%s' is in the manifest but on neither the character nor the \
excluded list — classify it in tests/test_art_selout_coverage.gd" % name)

func test_the_allowlists_match_the_manifest_exactly() -> void:
	eq(CHARACTER_SHEETS.size() + EXCLUDED_SHEETS.size(), _manifest.size(),
		"CHARACTER_SHEETS + EXCLUDED_SHEETS must account for every sheet the \
generator produced — a sheet was added or removed without updating this test")
