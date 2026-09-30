extends Node2D
## Shown when the last grey door on the overworld turns green — Game.complete_level
## decides that, and until M5 nothing did, so this screen existed and was never
## reachable. Rolls the totals and returns to the title, where CONTINUE puts the
## player back on the hub with all 25 doors open: finishing the game is not the
## end of the save file.
##
## The words used to be "THE CANOPY / IS QUIET AGAIN", written when the canopy was
## the whole game. Kaya ends it five worlds from home, standing in a room lit by
## the thing she just put out, so the last line is the way back rather than the
## place she is.

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
	PixelFont.draw_centered(self, W * 0.5, 40.0, "THE NEST IS COLD", Color(1, 0.86, 0.33), 2, 2)
	PixelFont.draw_centered(self, W * 0.5, 64.0, "KAYA COMES HOME", Color(1, 0.86, 0.33), 2, 2)
	PixelFont.draw_centered(self, W * 0.5, 92.0, "FIVE WORLDS BEHIND HER",
		Color(0.62, 0.86, 0.9), 1, 1)
	PixelFont.draw_centered(self, W * 0.5, 116.0, "GEMS  %03d" % Game.gems, Color(0.62, 0.86, 0.9), 1, 1)
	PixelFont.draw_centered(self, W * 0.5, 132.0, "SCORE %06d" % Game.score, Color(0.96, 0.86, 0.4), 1, 1)
	PixelFont.draw_centered(self, W * 0.5, 148.0, "LIVES %d" % Game.lives, Color(0.85, 0.88, 0.82), 1, 1)
	if fmod(_t, 1.0) < 0.65:
		PixelFont.draw_centered(self, W * 0.5, 196.0, "PRESS JUMP", Color(0.85, 0.88, 0.82), 1, 1)
