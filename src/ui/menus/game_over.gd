extends Node2D
## Shown when the last life is gone. Press jump to return to the title.

var _t := 0.0
var _input := InputState.new()
var _busy := false

func _ready() -> void:
	AudioManager.music("")
	AudioManager.play("game_over")
	SaveManager.add_score(Game.score)
	SaveManager.save()

func _physics_process(delta: float) -> void:
	_t += delta
	_input.poll()
	if _t > 0.6 and not _busy and (_input.jump_pressed or _input.attack_pressed):
		_busy = true
		Game.goto_title()
	queue_redraw()

func _draw() -> void:
	var W := float(Screen.W)
	draw_rect(Rect2(Vector2.ZERO, Vector2(Screen.W, Screen.H)), Color(0.05, 0.04, 0.06))
	PixelFont.draw_centered(self, W * 0.5, 78.0, "GAME OVER", Color(0.75, 0.29, 0.23), 3, 2)
	PixelFont.draw_centered(self, W * 0.5, 126.0, "SCORE %06d" % Game.score,
		Color(0.96, 0.86, 0.4), 1, 1)
	PixelFont.draw_centered(self, W * 0.5, 142.0,
		"BEST  %06d" % int(SaveManager.data.get("best_score", 0)), Color(0.6, 0.66, 0.6), 1, 1)
	if fmod(_t, 1.0) < 0.65:
		PixelFont.draw_centered(self, W * 0.5, 184.0, "PRESS JUMP", Color(0.85, 0.88, 0.82), 1, 1)
