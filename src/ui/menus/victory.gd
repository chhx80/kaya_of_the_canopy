extends Node2D
## Shown after the final door. Rolls the totals and returns to the title.

var _t := 0.0
var _input := InputState.new()
var _busy := false
var _bg: Texture2D = null

func _ready() -> void:
	_bg = load("res://assets/sprites/title_bg.png")
	AudioManager.music("victory")
	SaveManager.add_score(Game.score)
	SaveManager.save()

func _physics_process(delta: float) -> void:
	_t += delta
	_input.poll()
	if _t > 1.0 and not _busy and (_input.jump_pressed or _input.attack_pressed):
		_busy = true
		Game.goto_title()
	queue_redraw()

func _draw() -> void:
	var W := float(Screen.W)
	if _bg:
		draw_texture(_bg, Vector2.ZERO, Color(0.75, 0.8, 0.85))
	PixelFont.draw_centered(self, W * 0.5, 44.0, "THE CANOPY", Color(1, 0.86, 0.33), 2, 2)
	PixelFont.draw_centered(self, W * 0.5, 68.0, "IS QUIET AGAIN", Color(1, 0.86, 0.33), 2, 2)
	PixelFont.draw_centered(self, W * 0.5, 116.0, "GEMS  %03d" % Game.gems, Color(0.62, 0.86, 0.9), 1, 1)
	PixelFont.draw_centered(self, W * 0.5, 132.0, "SCORE %06d" % Game.score, Color(0.96, 0.86, 0.4), 1, 1)
	PixelFont.draw_centered(self, W * 0.5, 148.0, "LIVES %d" % Game.lives, Color(0.85, 0.88, 0.82), 1, 1)
	if fmod(_t, 1.0) < 0.65:
		PixelFont.draw_centered(self, W * 0.5, 196.0, "PRESS JUMP", Color(0.85, 0.88, 0.82), 1, 1)
