class_name WakeRule
extends RefCounted
## When an ordinary enemy is awake, decided by distance from the camera's view.
## Pure, so tests/test_camera.gd can drive every transition headless.
##
## THE RULE (decided in refit phase 2; see CHANGELOG.md):
##
## * An enemy is AWAKE while its body overlaps the view grown by the sleep
##   margin. Awake means thinking, moving, hurting and hittable — including just
##   off the screen edge, so a chaser that steps out of frame comes back.
## * Once its body is further out than that, it DESPAWNS: put back on its spawn,
##   hidden, not thinking, not hittable. Nothing acts unseen far away.
## * A despawned enemy RESPAWNS — fresh, at full health — when its spawn point
##   comes within the view grown by the wake margin. The wake margin sits outside
##   the screen, so it is already moving before the first pixel of it shows:
##   nothing sits frozen at the edge of the view.
## * But only once its spawn has first been out of range. An enemy that wandered
##   off while its spawn was on screen stays gone until that spawn scrolls away
##   and back; respawning it there would pop it into existence in plain sight.
## * Killed is killed, for the rest of the attempt (unchanged from the flip).
##
## Bosses do not use this. A boss is woken by its arena locking the camera —
## see Level._update_arena().

enum Act { STAY, DESPAWN, RESPAWN }

## `spawn_clear`: has the spawn been out of wake range since it last despawned.
static func decide(awake: bool, spawn_clear: bool, body_in_sleep_range: bool,
		spawn_in_wake_range: bool) -> Act:
	if awake:
		return Act.STAY if body_in_sleep_range else Act.DESPAWN
	if spawn_in_wake_range and spawn_clear:
		return Act.RESPAWN
	return Act.STAY

## What `spawn_clear` becomes after this tick's decision.
static func next_clear(act: Act, spawn_clear: bool, spawn_in_wake_range: bool) -> bool:
	match act:
		Act.DESPAWN:
			return not spawn_in_wake_range
		Act.RESPAWN:
			return false
	return spawn_clear or not spawn_in_wake_range
