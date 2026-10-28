# Dread Dice

**OmnisGM Homebrew · version 1.0 · an optional mechanic for d20 games**

Compatible with both editions of D&D 5e (SRD 5.1 and SRD 5.2.1) and with other games where a check is a d20 roll. Dread Dice are not official D&D rules: this is a standalone OmnisGM mechanic, and you don't need it to play by the core rules.

## For Players in Brief

When the GM says a check uses **dread dice**, draw a d20 blind from the shared bag and roll it instead of your usual d20. The check is resolved as normal.

- **Light die** — an ordinary check; the threat has nothing to do with it.
- **Dark die** — the check is resolved as normal, but the result may trigger a complication. The GM tells you what it is.
- **A 20 on a dark die** never triggers a complication.

With **advantage** or **disadvantage**, draw **one** die, roll it twice and use the higher or lower result. Both rolls share the same colour. The GM may choose another mode — the two-dice mode (see below).

The bag isn't used for every check: the GM tells you when it's in play. The mechanic doesn't replace the usual rules.

## Game Master's Guide

### What It's For

The mechanic turns some ordinary d20 checks into a source of tension. Players can avoid trouble, but every safe roll of a dark die brings the next complication closer. Light dice give a breather. The threat is driven by the heroes' decisions and story events; you don't need to split the game into acts.

**Principle:** *the threat grows not because the next act has begun, but because the world answers what the characters do.*

### The Bag and Its Parameters

In the basic version there is **one** bag holding light and dark d20s. Players always draw from that one bag, even when the GM runs several threats.

| Parameter | Symbol | Meaning |
|---|---|---|
| Light dice | `W` | Number of ordinary d20s; they don't raise the threat |
| Dark dice | `B` | Number of dangerous d20s; they set how often a check meets the threat |
| Base threshold | `T₀` | Integer from 0 to 20; set by the GM, may change with events |
| Current threshold | `T` | Integer from 0 to 20; starts at `T₀`, then builds up tension |
| Step | `Δ` | Integer from 0, usually 0–3; how much `T` grows after a safe roll of a dark die |

**The die's result** is the number rolled on the d20, without the check's modifiers. If the result was rerolled or replaced, the final number counts (see "Rerolls and Replaced Results").

A threat event happens only if the result on a **dark** die is **strictly lower than `T`**. At `T = 5`, results 1–4 are dangerous, and 5 is not. At `T = 0` and `T = 1` there are no events; at `T = 20`, results 1–19 are dangerous. The threshold never exceeds 20, so a 20 never triggers an event.

The GM may change `W`, `B`, `T₀`, `T` and `Δ` as the story unfolds. The current threshold carries over between scenes, acts and sessions unless the GM decides otherwise. `T₀ = 0` and `Δ = 0` are allowed.

### Check Procedure

1. The GM announces that the check uses the bag.
2. The player draws one d20 blind and rolls it. The result resolves the check by the game's rules.
3. **Light** die: no event, `T` doesn't change.
4. **Dark** die, rolled a **20**: no event, `T` doesn't change.
5. **Dark** die, result **strictly lower than `T`**: a threat event happens. After it, the threshold resets: `T := T₀`.
6. **Dark** die, result **not lower than `T`** and **not 20**: no event, the threshold grows: `T := min(20, T + Δ)`.
7. The die goes back into the bag.

The threat is resolved **once** per check, using the final result.

**Important:** a complication doesn't mean the check fails. The hero can succeed yet draw the pursuer's attention, lose time or run into a new obstacle. A 20 protects only against the threat event; what a 20 means for the check itself is up to the game's rules (in D&D, a Critical Hit on an attack roll).

### Example of Building Tension

The bag holds 5 light d20s and 1 dark d20, `T₀ = 5`, `Δ = 1`.

| Die drawn | Result | What happens | New `T` |
|---|---:|---|---:|
| Dark | 12 | No event; tension grows | 6 |
| Light | 2 | An ordinary check; a breather | 6 |
| Dark | 20 | Neither an event nor growth | 6 |
| Dark | 5 | Event: 5 < 6; reset | 5 |

At `T = 5` a result of 5 is still safe; at `T = 6` it is already dangerous.

### Resetting the Threshold

**Basic mode — full reset:** after an event, `T := T₀`. This makes cycles of rising and releasing tension.

**Optional mode — reset with step:** after an event, `T := min(20, T₀ + Δ)`. The next cycle starts with a little leftover tension. There is no endless build-up: while `T₀` and `Δ` stay the same, the reset point stays the same.

If the GM changes the **base** threshold because of the characters' actions, the reset goes to the new `T₀`. For example, the heroes broke a ward and the GM raised `T₀` from 5 to 8: after an event the threshold returns to 8 (or to `8 + Δ` with reset with step). The simplest way to handle the current threshold is to shift it by the same difference, keeping the accumulated bonus: `T := clamp(T + (T₀_new − T₀_old), 0, 20)`.

### Advantage and Disadvantage

If a check has both advantage and disadvantage, they cancel out (as in both editions of D&D): it's an ordinary check with one die.

**Basic mode — one die, two rolls.** Draw one d20, roll it twice, use the higher result with advantage and the lower with disadvantage. The threat uses the **kept result** and the drawn die's colour, once.

**Optional mode — two dice.** Draw two d20s and roll both. With advantage the die with the higher result is kept, with disadvantage the one with the lower. Only **the kept die's colour and result** count for the threat; the other die doesn't change the threshold.

- **Ties:** if dice of different colours show the same number, the **light** die is kept — with advantage and with disadvantage alike. A tie between dice of the same colour changes nothing.
- The mode needs at least two dice in the bag. If the bag holds one die, the check uses the basic mode.
- Both dice go back into the bag.

**Pair effects (a separate option):** if both drawn dice are dark, the GM may add an unfavourable consequence; if both are light, a small piece of luck or a breather. These effects don't depend on which die was kept. The GM announces their strength in advance; don't turn every pair of dark dice into a catastrophe.

### Rerolls and Replaced Results

Features from the game's rules work as usual; the bag only decides what colour the check is.

- **A reroll** (for example, the halfling's Luck trait: rerolling a 1 on the d20). The same drawn die is rerolled; its colour doesn't change. The new result counts.
- **An extra d20 from a feature** (features that add another d20 to the check). That die is rolled **outside the bag** and has no colour. The check's colour comes from the die from the bag; if the feature lets you use the extra die's result, that result counts for the threat with the colour of the die from the bag.
- **A result replaced after the roll** (features that put another number in place of the rolled one). The number changes, not the colour: the substituted number counts with the drawn die's colour.
- **A replacement declared before the roll.** The die is still drawn blind from the bag: its colour decides whether the check touches the threat. It doesn't need to be rolled; the substituted number is the result. If the substitute is a 20 and the die is dark — neither an event nor growth.

In every case the threat is resolved **once**, using the final result after all rerolls and replacements. The two-dice mode follows the same rule: first determine the final numbers on both dice, then pick the kept die.

### Shaping the Threat with Decisions and Scenes

The GM can move the parameters either way:

- The heroes make noise in a dangerous place — add a dark die, raise `T₀` or `Δ`.
- The pursuer picks up the trail — raise `Δ` (for example, to 2) so safe brushes with the threat bring a complication closer faster.
- More creatures join the hunt — add dark dice.
- The heroes destroy the source of danger — remove a dark die, lower `T₀` or `Δ`.
- The characters find shelter — lower the current `T` or set the bag aside for a while.

**Acts are an optional tool.** The GM changes the bag between acts, scenes, sessions or in answer to the players' decisions. There is no mandatory "+1 dark die per act".

### Several Threats (Optional Mode)

For the players there is **always one** bag. By default one colour of dangerous dice is enough: the GM decides which threat shows itself in a scene. The players don't need to know how many threats are in play.

If you want a mechanical difference, put dice of several dangerous colours into **the same bag**: for example, black for the pursuer, red for the curse. Each colour has its own `T₀`, `T` and `Δ`; the colour drawn decides which counter changes. The calculator below tracks one threat; for several colours, use one calculator per threat or track the counters by hand.

### Exhaustible Bag (Optional Mode)

Drawn dice are **not returned** right away. When there aren't enough dice left for the next check, the GM refills the bag with the composition chosen at that moment. In the two-dice mode both dice leave the bag.

This gives the bag a memory: if the light dice are nearly gone, a dark one becomes more likely; if the dark ones are gone, there's a breather until the refill. The composition at refill can reflect the players' new decisions.

### GM Advice (Not Required Rules)

**Don't reveal the numbers without need.** You can explain the principle of dangerous dice to the players and keep `T₀`, `T` and `Δ` behind the screen. Show the danger through the world: after a noisy break-in footsteps sound behind the door; after a good hiding place the pursuer loses the trail. Agree on the rules with your group in advance, especially if your players value fully transparent odds.

**Start calm.** You can use `T₀ = 0`, `Δ = 0` and even `B = 0` until the heroes wake the danger.

**Give breathers.** Light dice don't raise the threat. Don't draw from the bag on every check — only where tension serves the story.

**An event isn't necessarily damage.** Noise, a lost resource, an approaching enemy, a change of surroundings, a revealed secret, a condition on a character. Match the severity to the campaign's tone.

**Hide how the threat works, not cause and effect.** The players' decisions should feel meaningful even when they don't know the exact numbers.

## Sources and Licence

**Inspiration:** Jason Bulmahn, [The Mechanics of Horror](https://paizo.com/blog/the-mechanics-of-horror) — an article on the dice-bag mechanic of 13 Omens (Paizo). Dread Dice are a standalone d20 adaptation with their own parameters and modes; they are not 13 Omens rules and are not endorsed by Paizo.

**Licence:** the Dread Dice rules text © OmnisGM, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). You may copy and adapt it with attribution: "Dread Dice, OmnisGM, rules.omnisgm.com, CC BY 4.0". The OmnisGM brand, the illustrations and the code of the calculator and the app are not covered by this licence.

## Calculator

The calculator below is a GM's tool: it shows the chance of an event on the next check, rolls dice from a virtual bag, and tracks the current threshold and a log. The rules above read fine without it.

**What it computes.** Let `n = max(0, T − 1)` be the number of dangerous results (1…T−1), and `N = W + B` the dice in the bag right now.

| Check | Chance of an event |
|---|---|
| Ordinary | `B/N × n/20` |
| One die, advantage | `B/N × n²/400` |
| One die, disadvantage | `B/N × (1 − (20 − n)²/400)` |
| Two dice, advantage | `B(B−1)/(N(N−1)) × n²/400 + 2BW/(N(N−1)) × n(n−1)/2/400` |
| Two dice, disadvantage | `B(B−1)/(N(N−1)) × (1 − (20 − n)²/400) + 2BW/(N(N−1)) × (20n − n(n+1)/2)/400` |

The second term in the two-dice mode is a pair of different colours: the dark die is kept only if its result is strictly higher (advantage) or strictly lower (disadvantage) than the light one's; a tie goes to the light die. In an exhaustible bag, `W` and `B` are what's left, not the full composition.

**How it behaves:**

- "Roll", "With advantage", "With disadvantage" — draw and roll dice in the chosen modes and change the threshold by the rules above.
- "Enter result" — for dice rolled at the table: set the kept die's colour and its final number, after rerolls and replacements. The threshold changes; the bag doesn't.
- Changing `T₀` shifts the current `T` by the same difference; changing the composition refills the bag.
- An exhaustible bag refills itself when there aren't enough dice for a check; the "Refill" button does it by hand.
- One threat (one dangerous colour) is tracked.
