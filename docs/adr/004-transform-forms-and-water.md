# ADR 004 — Leaving the water as a fish

**Status:** accepted

## Context
`data/forms/fish.json` gives the fish an air timer. The original rule, taken
from the plan, was "dies out of water". Two things were wrong with it in play.

**It was unreachable anyway.** The fish's surface hop reached 12.5 px against a
bank one tile (16 px) high, so a fish could not leave the water at all. THE
WATERWAY was a dead end for anyone who used the fish pad — which is every player,
since the pad sits five tiles from the spawn and the level is called THE
WATERWAY. The level was only completable by ignoring its central mechanic.

**Dying was the wrong failure.** A player who beaches themselves has not been
taught the rule. Losing a life to it reads as a bug, which is exactly how it was
reported.

## Decision
1. The surface hop clears a one-tile bank with margin (apex 24.5 px). Beaching
   yourself is now possible and is the intended way out of the channel.
2. Running out of air **reverts to Kaya** instead of killing her. The meter still
   creates the pressure, and a `pad_human` is still the fast, deliberate way
   back — it just is not the only one.
3. The behaviour is data-driven: `out_of_water` is `"revert"` or `"die"`, so a
   later level can make a specific pool lethal without changing code.

## Consequences
- No transform can strand the player. That is the invariant worth keeping: a
  form you cannot leave is a soft-lock wearing a costume.
- Two integration tests cover it — that the hop clears the bank, and that
  running out of air turns Kaya back rather than killing her.
- The air meter is now a *timer for convenience* rather than a death clock. If a
  later level wants real danger it can set `out_of_water: "die"` deliberately,
  with the mechanic taught first.
