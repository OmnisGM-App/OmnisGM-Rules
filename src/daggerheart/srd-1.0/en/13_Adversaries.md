# Adversaries

## Using Adversaries

Adversaries are Game Master-controlled creatures that oppose the player characters. Each adversary has a stat block that defines their capabilities in play.

### Adversary Stat Block Anatomy

Each adversary stat block includes the following elements:

- **Name:** The adversary's name.
- **Tier and Type:** The adversary's power level (Tier 1–4) and role type.
- **Description:** A brief flavor description of the adversary.
- **Motives & Tactics:** A list of verbs describing how the adversary behaves in combat.
- **Difficulty:** The target number PCs must meet or exceed on action rolls against this adversary.
- **Damage Thresholds:** Two numbers (Minor/Major) that determine how much damage is needed to mark HP.
- **Hit Points (HP):** The number of HP the adversary has before being defeated.
- **Stress:** The number of Stress slots the adversary has.
- **Attack Modifier (ATK):** Added to the adversary's attack rolls.
- **Standard Attack:** The adversary's default attack, including weapon name, range, and damage.
- **Experience:** Optional. Specific skills the adversary has, with a modifier bonus.
- **Features:** Special abilities categorized as Passive, Action, or Reaction.

### Adversary Types

- **Bruiser:** A tough, hard-hitting adversary that deals heavy damage.
- **Horde:** A group of adversaries that acts as one. Listed as Horde (N/HP), where N is the number per HP slot. Deals reduced damage when HP is half or more marked.
- **Leader:** An adversary that commands others and uses spotlight mechanics.
- **Minion:** A weak adversary defeated by any damage. Overflow damage can defeat additional minions.
- **Ranged:** An adversary that attacks from a distance.
- **Skulk:** A stealthy adversary that uses deception and ambush tactics.
- **Social:** An adversary focused on social encounters rather than combat.
- **Solo:** A powerful boss adversary with the Relentless feature, allowing multiple spotlights per GM turn.
- **Standard:** A typical adversary with no special type modifiers.
- **Support:** An adversary that buffs allies or debuffs PCs.

### Building Balanced Encounters

To build a balanced encounter, calculate your **Battle Points** budget:

**Battle Points = 3 × number of PCs + 2**

Each adversary costs a number of Battle Points based on their type:

| Type | Battle Points |
|---|---|
| Minion | 1 |
| Horde | 2 |
| Standard | 2 |
| Ranged | 2 |
| Skulk | 2 |
| Support | 2 |
| Social | 2 |
| Bruiser | 3 |
| Leader | 3 |
| Solo | 5 |

### Adversary Stat Block Benchmarks

| | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|---|---|
| **Difficulty** | 10–14 | 12–16 | 15–19 | 17–21 |
| **Minor Threshold** | 3–10 | 7–14 | 10–20 | 18–35 |
| **Major Threshold** | 8–18 | 14–25 | 22–40 | 35–65 |
| **HP** | 3–8 | 4–10 | 5–12 | 5–14 |
| **Stress** | 1–3 | 2–4 | 3–5 | 4–6 |
| **ATK** | +0 to +3 | +1 to +5 | +3 to +7 | +5 to +10 |

## Tier 1 Adversaries (Level 1)

### Acid Burrower

**_Tier 1 Solo._** _A horse-sized insect with digging claws and acidic blood._

- **Motives & Tactics:** Burrow, drag away, feed, reposition
- **Difficulty:** 14 | **Thresholds:** 8/15 | **HP:** 8 | **Stress:** 3
- **ATK:** +3 | **Claws:** Very Close | 1d12+2 phy
- **Experience:** Tremor Sense +2

#### Features

**_Relentless (3) - Passive:_** The Burrower can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Earth Eruption - Action:_** **Mark a Stress** to have the Burrower burst out of the ground. All creatures within Very Close range must succeed on an Agility Reaction Roll or be knocked over, making them _Vulnerable_ until they next act.

**_Spit Acid - Action:_** Make an attack against all targets in front of the Burrower within Close range. Targets the Burrower succeeds against take **2d6** physical damage and must mark an Armor Slot without receiving its benefits (they can still use armor to reduce the damage). If they can't mark an Armor Slot, they must mark an additional HP and you gain a Fear.

**_Acid Bath - Reaction:_** When the Burrower takes Severe damage, all creatures within Close range are bathed in their acidic blood, taking **1d10** physical damage. This splash covers the ground within Very Close range with blood, and all creatures other than the Burrower who move through it take **1d6** physical damage.

---

### Archer Guard

**_Tier 1 Ranged._** _A tall guard bearing a longbow and quiver with arrows fletched in the settlement's colors._

- **Motives & Tactics:** Arrest, close gates, make it through the day, pin down
- **Difficulty:** 10 | **Thresholds:** 4/8 | **HP:** 3 | **Stress:** 2
- **ATK:** +1 | **Longbow:** Far | 1d8+3 phy
- **Experience:** Local Knowledge +3

#### Features

**_Hobbling Shot - Action:_** Make an attack against a target within Far range. On a success, **mark a Stress** to deal **1d12+3** physical damage. If the target marks HP from this attack, they have disadvantage on Agility Rolls until they clear at least 1 HP.

---

### Bear

**_Tier 1 Bruiser._** _A large bear with thick fur and powerful claws._

- **Motives & Tactics:** Climb, defend territory, pummel, track
- **Difficulty:** 14 | **Thresholds:** 9/17 | **HP:** 7 | **Stress:** 2
- **ATK:** +1 | **Claws:** Melee | 1d8+3 phy
- **Experience:** Ambusher +3, Keen Senses +2

#### Features

**_Overwhelming Force - Passive:_** Targets who mark HP from the Bear's standard attack are knocked back to Very Close range.

**_Bite - Action:_** **Mark a Stress** to make an attack against a target within Melee range. On a success, deal **3d4+10** physical damage and the target is _Restrained_ until they break free with a successful Strength Roll.

**_Momentum - Reaction:_** When the Bear makes a successful attack against a PC, you gain a Fear.

---

### Bladed Guard

**_Tier 1 Standard._** _An armored guard bearing a sword and shield painted in the settlement's colors._

- **Motives & Tactics:** Arrest, close gates, make it through the day, pin down
- **Difficulty:** 12 | **Thresholds:** 5/9 | **HP:** 5 | **Stress:** 2
- **ATK:** +1 | **Longsword:** Melee | 1d6+1 phy
- **Experience:** Local Knowledge +3

#### Features

**_Shield Wall - Passive:_** A creature who tries to move within Very Close range of the Guard must succeed on an Agility Roll. If additional Bladed Guards are standing in a line alongside the first, and each is within Melee range of another guard in the line, the Difficulty increases by the total number of guards in that line.

**_Detain - Action:_** Make an attack against a target within Very Close range. On a success, **mark a Stress** to _Restrain_ the target until they break free with a successful attack, Finesse Roll, or Strength Roll.

---

### Brawny Zombie

**_Tier 1 Bruiser._** _A large corpse, decay-bloated and angry._

- **Motives & Tactics:** Crush, destroy, hail debris, slam
- **Difficulty:** 10 | **Thresholds:** 8/15 | **HP:** 7 | **Stress:** 4
- **ATK:** +2 | **Slam:** Very Close | 1d12+3 phy
- **Experience:** Collateral Damage +2, Throw +4

#### Features

**_Slow - Passive:_** When you spotlight the Zombie and they don't have a token on their stat block, they can't act yet. Place a token on their stat block and describe what they're preparing to do. When you spotlight the Zombie and they have a token on their stat block, clear the token and they can act.

**_Rend Asunder - Action:_** Make a standard attack with advantage against a target the Zombie has _Restrained_. On a success, the attack deals direct damage.

**_Rip and Tear - Reaction:_** When the Zombies makes a successful standard attack, you can **mark a Stress** to temporarily _Restrain_ the target and force them to mark 2 Stress.

---

### Cave Ogre

**_Tier 1 Solo._** _A massive humanoid who sees all sapient life as food._

- **Motives & Tactics:** Bite off heads, feast, rip limbs, stomp, throw enemies
- **Difficulty:** 13 | **Thresholds:** 8/15 | **HP:** 8 | **Stress:** 3
- **ATK:** +1 | **Club:** Very Close | 1d10+2 phy
- **Experience:** Throw +2

#### Features

**_Ramp Up - Passive:_** You must **spend a Fear** to spotlight the Ogre. While spotlighted, they can make their standard attack against all targets within range.

**_Bone Breaker - Passive:_** The Ogre's attacks deal direct damage.

**_Hail of Boulders - Action:_** **Mark a Stress** to pick up heavy objects and throw them at all targets in front of the Ogre within Far range. Make an attack against these targets. Targets the Ogre succeeds against take **1d10+2** physical damage. If they succeed against more than one target, you gain a Fear.

**_Rampaging Fury - Reaction:_** When the Ogre marks 2 or more HP, they can rampage. Move the Ogre to a point within Close range and deal **2d6+3** direct physical damage to all targets in their path.

---

### Construct

**_Tier 1 Solo._** _A roughly humanoid being of stone and steel, assembled and animated by magic._

- **Motives & Tactics:** Destroy environment, serve creator, smash target, trample groups
- **Difficulty:** 13 | **Thresholds:** 7/15 | **HP:** 9 | **Stress:** 4
- **ATK:** +4 | **Fist Slam:** Melee | 1d20 phy

#### Features

**_Relentless (2) - Passive:_** The Construct can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Weak Structure - Passive:_** When the Construct marks HP from physical damage, they must mark an additional HP.

**_Trample - Action:_** **Mark a Stress** to make an attack against all targets in the Construct's path when they move. Targets the Construct succeeds against take **1d8** physical damage.

**_Overload - Reaction:_** Before rolling damage for the Construct's attack, you can **mark a Stress** to gain a +10 bonus to the damage roll. The Construct can then take the spotlight again.

**_Death Quake - Reaction:_** When the Construct marks their last HP, the magic powering them ruptures in an explosion of force. Make an attack with advantage against all targets within Very Close range. Targets the Construct succeeds against take **1d12+2** magic damage.

---

### Courtier

**_Tier 1 Social._** _An ambitious and ostentatiously dressed socialite._

- **Motives & Tactics:** Discredit, gain favor, maneuver, scheme
- **Difficulty:** 12 | **Thresholds:** 4/8 | **HP:** 3 | **Stress:** 4
- **ATK:** -4 | **Daggers:** Melee | 1d4+2 phy
- **Experience:** Socialite +3

#### Features

**_Mockery - Action:_** **Mark a Stress** to say something mocking and force a target within Close range to make a Presence Reaction Roll (14) to see if they can save face. On a failure, the target must mark 2 Stress and is _Vulnerable_ until the scene ends.

**_Scapegoat - Action:_** **Spend a Fear** and target a PC. The Courtier convinces a crowd or prominent individual that the target is the cause of their current conflict or misfortune.

---

### Deeproot Defender

**_Tier 1 Bruiser._** _A burly vegetable-person with grasping vines._

- **Motives & Tactics:** Ambush, grab, protect, pummel
- **Difficulty:** 10 | **Thresholds:** 8/14 | **HP:** 7 | **Stress:** 3
- **ATK:** +2 | **Vines:** Close | 1d8+3 phy
- **Experience:** Huge +3

#### Features

**_Ground Slam - Action:_** Slam the ground, knocking all targets within Very Close range back to Far range. Each target knocked back this way must mark a Stress.

**_Grab and Drag - Action:_** Make an attack against a target within Close range. On a success, **spend a Fear** to pull them into Melee range, deal **1d6+2** physical damage, and _Restrain_ them until the Defender takes Severe damage.

---

### Dire Wolf

**_Tier 1 Skulk._** _A large wolf with menacing teeth, seldom encountered alone._

- **Motives & Tactics:** Defend territory, harry, protect pack, surround, trail
- **Difficulty:** 12 | **Thresholds:** 5/9 | **HP:** 4 | **Stress:** 3
- **ATK:** +2 | **Claws:** Melee | 1d6+2 phy
- **Experience:** Keen Senses +3

#### Features

**_Pack Tactics - Passive:_** If the Wolf makes a successful standard attack and another Dire Wolf is within Melee range of the target, deal **1d6+5** physical damage instead of their standard damage and you gain a Fear.

**_Hobbling Strike - Action:_** **Mark a Stress** to make an attack against a target within Melee range. On a success, deal **3d4+10** direct physical damage and make them _Vulnerable_ until they clear at least 1 HP.

---

### Giant Mosquitoes

**_Tier 1 Horde (5/HP)._** _Dozens of fist-sized mosquitoes, flying together for protection._

- **Motives & Tactics:** Fly away, harass, steal blood
- **Difficulty:** 10 | **Thresholds:** 5/9 | **HP:** 6 | **Stress:** 3
- **ATK:** -2 | **Proboscis:** Melee | 1d8+3 phy
- **Experience:** Camouflage +2

#### Features

**_Horde (1d4+1) - Passive:_** When the Mosquitoes have marked half or more of their HP, their standard attack deals **1d4+1** physical damage instead.

**_Flying - Passive:_** While flying, the Mosquitoes have a +2 bonus to their Difficulty.

**_Bloodsucker - Reaction:_** When the Mosquitoes' attack causes a target to mark HP, you can **mark a Stress** to force the target to mark an additional HP.

---

### Giant Rat

**_Tier 1 Minion._** _A cat-sized rodent skilled at scavenging and survival._

- **Motives & Tactics:** Burrow, hunger, scavenge, wear down
- **Difficulty:** 10 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -4 | **Claws:** Melee | 1 phy
- **Experience:** Keen Senses +3

#### Features

**_Minion (3) - Passive:_** The Rat is defeated when they take any damage. For every 3 damage a PC deals to the Rat, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Giant Rats within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 1 physical damage each. Combine this damage.

---

### Giant Scorpion

**_Tier 1 Bruiser._** _A human-sized arachnid with tearing claws and a stinging tail._

- **Motives & Tactics:** Ambush, feed, grapple, poison
- **Difficulty:** 13 | **Thresholds:** 7/13 | **HP:** 6 | **Stress:** 3
- **ATK:** +1 | **Pincers:** Melee | 1d12+2 phy
- **Experience:** Camouflage +2

#### Features

**_Double Strike - Action:_** **Mark a Stress** to make a standard attack against two targets within Melee range.

**_Venomous Stinger - Action:_** Make an attack against a target within Very Close range. On a success, **spend a Fear** to deal **1d4+4** physical damage and _Poison_ them until their next rest or they succeed on a Knowledge Roll (16). While _Poisoned_, the target must roll a **d6** before they make an action roll. On a result of 4 or lower, they must mark a Stress.

**_Momentum - Reaction:_** When the Scorpion makes a successful attack against a PC, you gain a Fear.

---

### Glass Snake

**_Tier 1 Standard._** _A clear serpent with a massive head that leaves behind a glass shard trail wherever they go._

- **Motives & Tactics:** Climb, feed, keep distance, scare
- **Difficulty:** 14 | **Thresholds:** 6/10 | **HP:** 5 | **Stress:** 3
- **ATK:** +2 | **Glass Fangs:** Very Close | 1d8+2 phy

#### Features

**_Armor-Shredding Shards - Passive:_** After a successful attack against the Snake within Melee range, the attacker must mark an Armor Slot. If they can't mark an Armor Slot, they must mark an HP.

**_Spinning Serpent - Action:_** **Mark a Stress** to make an attack against all targets within Very Close range. Targets the Snake succeeds against take **1d6+1** physical damage.

**_Spitter - Action:_** **Spend a Fear** to introduce a **d6** Spitter Die. When the Snake is in the spotlight, roll this die. On a result of 5 or higher, all targets in front of the Snake within Far range must succeed on an Agility Reaction Roll or take **1d4** physical damage. The Snake can take the spotlight a second time this GM turn.

---

### Green Ooze

**_Tier 1 Skulk._** _A moving mound of translucent green slime._

- **Motives & Tactics:** Camouflage, consume and multiply, creep up, envelop
- **Difficulty:** 8 | **Thresholds:** 5/10 | **HP:** 5 | **Stress:** 2
- **ATK:** +1 | **Ooze Appendage:** Melee | 1d6+1 mag
- **Experience:** Camouflage +3

#### Features

**_Slow - Passive:_** When you spotlight the Ooze and they don't have a token on their stat block, they can't act yet. Place a token on their stat block and describe what they're preparing to do. When you spotlight the Ooze and they have a token on their stat block, clear the token and they can act.

**_Acidic Form - Passive:_** When the Ooze makes a successful attack, the target must mark an Armor Slot without receiving its benefits (they can still use armor to reduce the damage). If they can't mark an Armor Slot, they must mark an additional HP.

**_Envelop - Action:_** Make a standard attack against a target within Melee range. On a success, the Ooze envelops them and the target must mark 2 Stress. The target must mark an additional Stress when they make an action roll. If the Ooze takes Severe damage, the target is freed.

**_Split - Reaction:_** When the Ooze has 3 or more HP marked, you can **spend a Fear** to split them into two Tiny Green Oozes (with no marked HP or Stress). Immediately spotlight both of them.

---

### Harrier

**_Tier 1 Standard._** _A nimble fighter armed with javelins._

- **Motives & Tactics:** Flank, harry, kite, profit
- **Difficulty:** 12 | **Thresholds:** 5/9 | **HP:** 3 | **Stress:** 3
- **ATK:** +1 | **Javelin:** Close | 1d6+2 phy
- **Experience:** Camouflage +2

#### Features

**_Maintain Distance - Passive:_** After making a standard attack, the Harrier can move anywhere within Far range.

**_Fall Back - Reaction:_** When a creature moves into Melee range to make an attack, you can **mark a Stress** before the attack roll to move anywhere within Close range and make an attack against that creature. On a success, deal **1d10+2** physical damage.

---

### Head Guard

**_Tier 1 Leader._** _A seasoned guard with a mace, a whistle, and a bellowing voice._

- **Motives & Tactics:** Arrest, close gates, pin down, seek glory
- **Difficulty:** 15 | **Thresholds:** 7/13 | **HP:** 7 | **Stress:** 3
- **ATK:** +4 | **Mace:** Melee | 1d10+4 phy
- **Experience:** Commander +2, Local Knowledge +2

#### Features

**_Rally Guards - Action:_** **Spend 2 Fear** to spotlight the Head Guard and up to **2d4** allies within Far range.

**_On My Signal - Reaction: Countdown (5):_** When the Head Guard is in the spotlight for the first time, activate the countdown. It ticks down when a PC makes an attack roll. When it triggers, all Archer Guards within Far range make a standard attack with advantage against the nearest target within their range. If any attacks succeed on the same target, combine their damage.

**_Momentum - Reaction:_** When the Head Guard makes a successful attack against a PC, you gain a Fear.

---

### Jagged Knife Bandit

**_Tier 1 Standard._** _A cunning criminal in a cloak bearing one of the gang's iconic knives._

- **Motives & Tactics:** Escape, profit, steal, throw smoke
- **Difficulty:** 12 | **Thresholds:** 8/14 | **HP:** 5 | **Stress:** 3
- **ATK:** +1 | **Daggers:** Melee | 1d8+1 phy
- **Experience:** Thief +2

#### Features

**_Climber - Passive:_** The Bandit climbs just as easily as they run.

**_From Above - Passive:_** When the Bandit succeeds on a standard attack from above a target, they deal **1d10+1** physical damage instead of their standard damage.

---

### Jagged Knife Hexer

**_Tier 1 Support._** _A staff-wielding bandit in a cloak adorned with magical paraphernalia, using curses to vex their foes._

- **Motives & Tactics:** Command, hex, profit
- **Difficulty:** 13 | **Thresholds:** 5/9 | **HP:** 4 | **Stress:** 4
- **ATK:** +2 | **Staff:** Far | 1d6+2 mag
- **Experience:** Magical Knowledge +2

#### Features

**_Curse - Action:_** Choose a target within Far range and temporarily _Curse_ them. While the target is _Cursed_, you can **mark a Stress** when that target rolls with Hope to make the roll be with Fear instead.

**_Chaotic Flux - Action:_** Make an attack against up to three targets within Very Close range. **Mark a Stress** to deal **2d6+3** magic damage to targets the Hexer succeeded against.

---

### Jagged Knife Kneebreaker

**_Tier 1 Bruiser._** _An imposing brawler carrying a large club._

- **Motives & Tactics:** Grapple, intimidate, profit, steal
- **Difficulty:** 12 | **Thresholds:** 7/14 | **HP:** 7 | **Stress:** 4
- **ATK:** -3 | **Club:** Melee | 1d4+6 phy
- **Experience:** Thief +2, Unveiled Threats +3

#### Features

**_I've Got 'Em - Passive:_** Creatures _Restrained_ by the Kneebreaker take double damage from attacks by other adversaries.

**_Hold Them Down - Action:_** Make an attack against a target within Melee range. On a success, the target takes no damage but is _Restrained_ and _Vulnerable_. The target can break free, clearing both conditions, with a successful Strength Roll or is freed automatically if the Kneebreaker takes Major or greater damage.

---

### Jagged Knife Lackey

**_Tier 1 Minion._** _A thief with simple clothes and small daggers, eager to prove themselves._

- **Motives & Tactics:** Escape, profit, throw smoke
- **Difficulty:** 9 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -2 | **Daggers:** Melee | 2 phy
- **Experience:** Thief +2

#### Features

**_Minion (3) - Passive:_** The Lackey is defeated when they take any damage. For every 3 damage a PC deals to the Lackey, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Jagged Knife Lackeys within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 2 physical damage each. Combine this damage.

---

### Jagged Knife Lieutenant

**_Tier 1 Leader._** _A seasoned bandit in quality leathers with a strong voice and cunning eyes._

- **Motives & Tactics:** Bully, command, profit, reinforce
- **Difficulty:** 13 | **Thresholds:** 7/14 | **HP:** 6 | **Stress:** 3
- **ATK:** +2 | **Javelin:** Close | 1d8+3 phy
- **Experience:** Local Knowledge +2

#### Features

**_Tactician - Action:_** When you spotlight the Lieutenant, **mark a Stress** to also spotlight two allies within Close range.

**_More Where That Came From - Action:_** Summon three Jagged Knife Lackeys, who appear at Far range.

**_Coup de Grace - Action:_** **Spend a Fear** to make an attack against a _Vulnerable_ target within Close range. On a success, deal **2d6+12** physical damage and the target must mark a Stress.

**_Momentum - Reaction:_** When the Lieutenant makes a successful attack against a PC, you gain a Fear.

---

### Jagged Knife Shadow

**_Tier 1 Skulk._** _A nimble scoundrel bearing a wicked knife and utilizing shadow magic to isolate targets._

- **Motives & Tactics:** Ambush, conceal, divide, profit
- **Difficulty:** 12 | **Thresholds:** 4/8 | **HP:** 3 | **Stress:** 3
- **ATK:** +1 | **Daggers:** Melee | 1d4+4 phy
- **Experience:** Intrusion +3

#### Features

**_Backstab - Passive:_** When the Shadow succeeds on a standard attack that has advantage, they deal **1d6+6** physical damage instead of their standard damage.

**_Cloaked - Action:_** Become _Hidden_ until after the Shadow's next attack. Attacks made while _Hidden_ from this feature have advantage.

---

### Jagged Knife Sniper

**_Tier 1 Ranged._** _A lanky bandit striking from cover with a shortbow._

- **Motives & Tactics:** Ambush, hide, profit, reposition
- **Difficulty:** 13 | **Thresholds:** 4/7 | **HP:** 3 | **Stress:** 2
- **ATK:** -1 | **Shortbow:** Far | 1d10+2 phy
- **Experience:** Stealth +2

#### Features

**_Unseen Strike - Passive:_** If the Sniper is _Hidden_ when they make a successful standard attack against a target, they deal **1d10+4** physical damage instead of their standard damage.

---

### Merchant

**_Tier 1 Social._** _A finely dressed trader with a keen eye for financial gain._

- **Motives & Tactics:** Buy low and sell high, create demand, inflate prices, seek profit
- **Difficulty:** 12 | **Thresholds:** 4/8 | **HP:** 3 | **Stress:** 3
- **ATK:** -4 | **Club:** Melee | 1d4+1 phy
- **Experience:** Shrewd Negotiator +3

#### Features

**_Preferential Treatment - Passive:_** A PC who succeeds on a Presence Roll against the Merchant gains a discount on purchases. A PC who fails on a Presence Roll against the Merchant must pay more and has disadvantage on future Presence Rolls against the Merchant.

**_The Runaround - Passive:_** When a PC rolls a 14 or lower on a Presence Roll made against the Merchant, they must mark a Stress.

---

### Minor Chaos Elemental

**_Tier 1 Solo._** _A coruscating mass of uncontrollable magic._

- **Motives & Tactics:** Confound, destabilize, transmogrify
- **Difficulty:** 14 | **Thresholds:** 7/14 | **HP:** 7 | **Stress:** 3
- **ATK:** +3 | **Warp Blast:** Close | 1d12+6 mag

#### Features

**_Arcane Form - Passive:_** The Elemental is resistant to magic damage.

**_Sickening Flux - Action:_** **Mark a HP** to force all targets within Close range to mark a Stress and become _Vulnerable_ until their next rest or they clear a HP.

**_Remake Reality - Action:_** **Spend a Fear** to transform the area within Very Close range into a different biome. All targets within this area take **2d6+3** direct magic damage.

**_Magical reflection - Reaction:_** When the Elemental takes damage from an attack within Close range, deal an amount of damage to the attacker equal to half the damage they dealt.

**_Momentum - Reaction:_** When the Elemental makes a successful attack against a PC, you gain a Fear.

---

### Minor Demon

**_Tier 1 Solo._** _A crimson-hued creature from the Circles Below, consumed by rage against all mortals._

- **Motives & Tactics:** Act erratically, corral targets, relish pain, torment
- **Difficulty:** 14 | **Thresholds:** 8/15 | **HP:** 8 | **Stress:** 4
- **ATK:** +3 | **Claws:** Melee | 1d8+6 phy

#### Features

**_Relentless (2) - Passive:_** The Demon can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_All Must Fall - Passive:_** When a PC rolls a failure with Fear while within Close range of the Demon, they lose a Hope.

**_Hellfire - Action:_** **Spend a Fear** to rain down hellfire within Far range. All targets within the area must make an Agility Reaction Roll. Targets who fail take **1d20+3** magic damage. Targets who succeed take half damage.

**_Reaper - Reaction:_** Before rolling damage for the Demon's attack, you can **mark a Stress** to gain a bonus to the damage roll equal to the Demon's current number of marked HP.

**_Momentum - Reaction:_** When the Demon makes a successful attack against a PC, you gain a Fear.

---

### Minor Fire Elemental

**_Tier 1 Solo._** _A living flame the size of a large bonfire._

- **Motives & Tactics:** Encircle enemies, grow in size, intimidate, start fires
- **Difficulty:** 13 | **Thresholds:** 7/15 | **HP:** 9 | **Stress:** 3
- **ATK:** +3 | **Elemental Blast:** Far | 1d10+4 mag

#### Features

**_Relentless (2) - Passive:_** The Elemental can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Scorched Earth - Action:_** **Mark a Stress** to choose a point within Far range. The ground within Very Close range of that point immediately bursts into flames. All creatures within this area must make an Agility Reaction Roll. Targets who fail take **2d8** magic damage from the flames. Targets who succeed take half damage.

**_Explosion - Action:_** **Spend a Fear** to erupt in a fiery explosion. Make an attack against all targets within Close range. Targets the Elemental succeeds against take **1d8** magic damage and are knocked back to Far range.

**_Consume Kindling - Reaction:_** Three times per scene, when the Elemental moves onto objects that are highly flammable, consume them to clear a HP or a Stress.

**_Momentum - Reaction:_** When the Elemental makes a successful attack against a PC, you gain a Fear.

---

### Minor Treant

**_Tier 1 Minion._** _An ambulatory sapling rising up to defend their forest._

- **Motives & Tactics:** Crush, overwhelm, protect
- **Difficulty:** 10 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -2 | **Clawed Branch:** Melee | 4 phy

#### Features

**_Minion (5) - Passive:_** The Treant is defeated when they take any damage. For every 5 damage a PC deals to the Treant, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Minor Treants within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 4 physical damage each. Combine this damage.

---

### Patchwork Zombie Hulk

**_Tier 1 Solo._** _A towering gestalt of corpses moving as one, with torso-sized limbs and fists as large as a grown halfling._

- **Motives & Tactics:** Absorb corpses, flail, hunger, terrify
- **Difficulty:** 13 | **Thresholds:** 8/15 | **HP:** 10 | **Stress:** 3
- **ATK:** +4 | **Too Many Arms:** Very Close | 1d20 phy
- **Experience:** Intimidation +2, Tear Things Apart +2

#### Features

**_Destructible - Passive:_** When the Zombie takes Major or greater damage, they mark an additional HP.

**_Flailing Limbs - Passive:_** When the Zombie makes a standard attack, they can attack all targets within Very Close range.

**_Another for the Pile - Action:_** When the Zombie is within Very Close range of a corpse, they can incorporate it into themselves, clearing a HP and a Stress.

**_Tormented Screams - Action:_** **Mark a Stress** to cause all PCs within Far range to make a Presence Reaction Roll (13). Targets who fail lose a Hope and you gain a Fear for each. Targets who succeed must mark a Stress.

---

### Petty Noble

**_Tier 1 Social._** _A richly dressed and adorned aristocrat brimming with hubris._

- **Motives & Tactics:** Abuse power, gather resources, mobilize minions
- **Difficulty:** 14 | **Thresholds:** 6/10 | **HP:** 3 | **Stress:** 5
- **ATK:** -3 | **Rapier:** Melee | 1d6+1 phy
- **Experience:** Aristocrat +3

#### Features

**_My Land, My Rules - Passive:_** All social actions made against the Noble on their land have disadvantage.

**_Guards, Seize Them! - Action:_** Once per scene, **mark a Stress** to summon **1d4** Bladed Guards, who appear at Far range to enforce the Noble's will.

**_Exile - Action:_** **Spend a Fear** and target a PC. The Noble proclaims that the target and their allies are exiled from the noble's territory. While exiled, the target and their allies have disadvantage during social situations within the Noble's domain.

---

### Pirate Captain

**_Tier 1 Leader._** _A charismatic sea dog with an impressive hat, eager to raid and plunder._

- **Motives & Tactics:** Command, make 'em walk the plank, plunder, raid
- **Difficulty:** 14 | **Thresholds:** 7/14 | **HP:** 7 | **Stress:** 5
- **ATK:** +4 | **Cutlass:** Melee | 1d12+2 phy
- **Experience:** Commander +2, Sailor +3

#### Features

**_Swashbuckler - Passive:_** When the Captain marks 2 or fewer HP from an attack within Melee range, the attacker must mark a Stress.

**_Reinforcements - Action:_** Once per scene, **mark a Stress** to summon a Pirate Raiders Horde, which appears at Far range.

**_No Quarter - Action:_** **Spend a Fear** to choose a target who has three or more Pirates within Melee range of them. The Captain leads the Pirates in hurling threats and promises of a watery grave. The target must make a Presence Reaction Roll. On a failure, the target marks **1d4+1** Stress. On a success, they must mark a Stress.

**_Momentum - Reaction:_** When the Captain makes a successful attack against a PC, you gain a Fear.

---

### Pirate Raiders

**_Tier 1 Horde (3/HP)._** _Seafaring scoundrels moving in a ravaging pack._

- **Motives & Tactics:** Gang up, plunder, raid
- **Difficulty:** 12 | **Thresholds:** 5/11 | **HP:** 4 | **Stress:** 3
- **ATK:** +1 | **Cutlass:** Melee | 1d8+2 phy
- **Experience:** Sailor +3

#### Features

**_Horde (1d4+1) - Passive:_** When the Raiders have marked half or more of their HP, their standard attack deals **1d4+1** physical damage instead.

**_Swashbuckler - Passive:_** When the Raiders mark 2 or fewer HP from an attack within Melee range, the attacker must mark a Stress.

---

### Pirate Tough

**_Tier 1 Bruiser._** _A thickly muscled and tattooed pirate with melon-sized fists._

- **Motives & Tactics:** Plunder, raid, smash, terrorize
- **Difficulty:** 13 | **Thresholds:** 8/15 | **HP:** 5 | **Stress:** 3
- **ATK:** +1 | **Massive Fists:** Melee | 2d6 phy
- **Experience:** Sailor +2

#### Features

**_Swashbuckler - Passive:_** When the Tough marks 2 or fewer HP from an attack within Melee range, the attacker must mark a Stress.

**_Clear the Decks - Action:_** Make an attack against a target within Very Close range. On a success, **mark a Stress** to move into Melee range of the target, dealing **3d4** physical damage and knocking the target back to Close range.

---

### Red Ooze

**_Tier 1 Skulk._** _A moving mound of translucent flaming red slime._

- **Motives & Tactics:** Camouflage, consume and multiply, ignite, start fires
- **Difficulty:** 10 | **Thresholds:** 6/11 | **HP:** 5 | **Stress:** 3
- **ATK:** +1 | **Ooze Appendage:** Melee | 1d8+3 mag
- **Experience:** Camouflage +3

#### Features

**_Creeping Fire - Passive:_** The Ooze can only move within Very Close range as their normal movement. They light any flammable object they touch on fire.

**_Ignite - Action:_** Make an attack against a target within Very Close range. On a success, the target takes **1d8** magic damage and is _Ignited_ until they're extinguished with a successful Finesse Roll (14). While _Ignited_, the target takes **1d4** magic damage when they make an action roll.

**_Split - Reaction:_** When the Ooze has 3 or more HP marked, you can **spend a Fear** to split them into two Tiny Red Oozes (with no marked HP or Stress). Immediately spotlight both of them.

---

### Rotted Zombie

**_Tier 1 Minion._** _A decaying corpse ambling toward their prey._

- **Motives & Tactics:** Eat flesh, hunger, maul, surround
- **Difficulty:** 8 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -3 | **Bite:** Melee | 2 phy

#### Features

**_Minion (3) - Passive:_** The Zombie is defeated when they take any damage. For every 3 damage a PC deals to the Zombie, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Rotted Zombies within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 2 physical damage each. Combine this damage.

---

### Sellsword

**_Tier 1 Minion._** _An armed mercenary testing their luck._

- **Motives & Tactics:** Charge, lacerate, overwhelm, profit
- **Difficulty:** 10 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +3 | **Longsword:** Melee | 3 phy

#### Features

**_Minion (4) - Passive:_** The Sellsword is defeated when they take any damage. For every 4 damage a PC deals to the Sellsword, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Sellswords within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 3 physical damage each. Combine this damage.

---

### Shambling Zombie

**_Tier 1 Standard._** _An animated corpse that moves shakily, driven only by hunger._

- **Motives & Tactics:** Devour, hungry, mob enemy, shred flesh
- **Difficulty:** 10 | **Thresholds:** 4/6 | **HP:** 4 | **Stress:** 1
- **ATK:** +0 | **Bite:** Melee | 1d6+1 phy

#### Features

**_Too Many to Handle - Passive:_** When the Zombie is within Melee range of a creature and at least one other Zombie is within Close range, all attacks against that creature have advantage.

**_Horrifying - Passive:_** Targets who mark HP from the Zombie's attacks must also mark a Stress.

---

### Skeleton Archer

**_Tier 1 Ranged._** _A fragile skeleton with a shortbow and arrows._

- **Motives & Tactics:** Perforate distracted targets, play dead, steal skin
- **Difficulty:** 9 | **Thresholds:** 4/7 | **HP:** 3 | **Stress:** 2
- **ATK:** +2 | **Shortbow:** Far | 1d8+1 phy

#### Features

**_Opportunist - Passive:_** When two or more adversaries are within Very Close range of a creature, all damage the Archer deals to that creature is doubled.

**_Deadly Shot - Action:_** Make an attack against a _Vulnerable_ target within Far range. On a success, **mark a Stress** to deal **3d4+8** physical damage.

---

### Skeleton Dredge

**_Tier 1 Minion._** _A clattering pile of bones._

- **Motives & Tactics:** Fall apart, overwhelm, play dead, steal skin
- **Difficulty:** 8 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -1 | **Bone Claws:** Melee | 1 phy

#### Features

**_Minion (4) - Passive:_** The Dredge is defeated when they take any damage. For every 4 damage a PC deals to the Dredge, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Dredges within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 1 physical damage each. Combine this damage.

---

### Skeleton Knight

**_Tier 1 Bruiser._** _A large armored skeleton with a huge blade._

- **Motives & Tactics:** Cut down the living, steal skin, wreak havoc
- **Difficulty:** 13 | **Thresholds:** 7/13 | **HP:** 5 | **Stress:** 2
- **ATK:** +2 | **Rusty Greatsword:** Melee | 1d10+2 phy

#### Features

**_Terrifying - Passive:_** When the Knight makes a successful attack, all PCs within Close range lose a Hope and you gain a Fear.

**_Cut to the Bone - Action:_** **Mark a Stress** to make an attack against all targets within Very Close range. Targets the Knight succeeds against take **1d8+2** physical damage and must mark a Stress.

**_Dig Two Graves - Reaction:_** When the Knight is defeated, they make an attack against a target within Very Close range (prioritizing the creature who killed them). On a success, the target takes **1d4+8** physical damage and loses **1d4** Hope.

---

### Skeleton Warrior

**_Tier 1 Standard._** _A dirt-covered skeleton armed with a rusted blade._

- **Motives & Tactics:** Feign death, gang up, steal skin
- **Difficulty:** 10 | **Thresholds:** 4/8 | **HP:** 3 | **Stress:** 2
- **ATK:** +0 | **Sword:** Melee | 1d6+2 phy

#### Features

**_Only Bones - Passive:_** The Warrior is resistant to physical damage.

**_Won't Stay Dead - Reaction:_** When the Warrior is defeated, you can spotlight them and roll a **d6**. On a result of 6, if there are other adversaries on the battlefield, the Warrior re-forms with no marked HP.

---

### Spellblade

**_Tier 1 Leader._** _A mercenary combining swordplay and magic to deadly effect._

- **Motives & Tactics:** Blast, command, endure
- **Difficulty:** 14 | **Thresholds:** 8/14 | **HP:** 6 | **Stress:** 3
- **ATK:** +3 | **Empowered Longsword:** Melee | 1d8+4 phy/mag
- **Experience:** Magical Knowledge +2

#### Features

**_Arcane Steel - Passive:_** Damage dealt by the Spellblade's standard attack is considered both physical and magic.

**_Suppressing Blast - Action:_** **Mark a Stress** and target a group within Far range. All targets must succeed on an Agility Reaction Roll or take **1d8+2** magic damage. You gain a Fear for each target who marked HP from this attack.

**_Move as a Unit - Action:_** **Spend 2 Fear** to spotlight up to five allies within Far range.

**_Momentum - Reaction:_** When the Spellblade makes a successful attack against a PC, you gain a Fear.

---

### Swarm of Rats

**_Tier 1 Horde (/HP)._** _A skittering mass of ordinary rodents moving as one like a ravenous wave._

- **Motives & Tactics:** Consume, obscure, swarm
- **Difficulty:** 10 | **Thresholds:** 6/10 | **HP:** 6 | **Stress:** 2
- **ATK:** -3 | **Claws:** Melee | 1d8+2 phy

#### Features

**_Horde (1d4+1) - Passive:_** When the Swarm has marked half or more of their HP, their standard attack deals **1d4+1** physical damage instead.

**_In Your Face - Passive:_** All targets within Melee range have disadvantage on attacks against targets other than the Swarm.

---

### Sylvan Soldier

**_Tier 1 Standard._** _A faerie warrior adorned in armor made of leaves and bark._

- **Motives & Tactics:** Ambush, hide, overwhelm, protect, trail
- **Difficulty:** 11 | **Thresholds:** 6/11 | **HP:** 4 | **Stress:** 2
- **ATK:** +0 | **Scythe:** Melee | 1d8+1 phy
- **Experience:** Tracker +2

#### Features

**_Pack Tactics - Passive:_** If the Soldier makes a standard attack and another Sylvan Soldier is within Melee range of the target, deal **1d8+5** physical damage instead of their standard damage.

**_Forest Control - Action:_** **Spend a Fear** to pull down a tree within Close range. A creature hit by the tree must succeed on an Agility Reaction Roll (15) or take **1d10** physical damage.

**_Blend In - Reaction:_** When the Soldier makes a successful attack, you can **mark a Stress** to become _Hidden_ until the Soldier's next attack or a PC succeeds on an Instinct Roll (14) to find them.

---

### Tangle Bramble Swarm

**_Tier 1 Horde (3/HP)._** _A cluster of animate, blood-drinking tumbleweeds, each the size of a large gourd._

- **Motives & Tactics:** Digest, entangle, immobilize
- **Difficulty:** 12 | **Thresholds:** 6/11 | **HP:** 6 | **Stress:** 3
- **ATK:** +0 | **Thorns:** Melee | 1d6+3 phy
- **Experience:** Camouflage +2

#### Features

**_Horde (1d4+2) - Passive:_** When the Swarm has marked half or more of their HP, their standard attack deals **1d4+2** physical damage instead.

**_Crush - Action:_** **Mark a Stress** to deal **2d6+8** direct physical damage to a target with 3 or more bramble tokens.

**_Encumber - Reaction:_** When the Swarm succeeds on an attack, give the target a bramble token. If a target has any bramble tokens, they are _Restrained_. If a target has 3 or more bramble tokens, they are also _Vulnerable_. All bramble tokens can be removed by succeeding on a Finesse Roll (12 + the number of bramble tokens) or dealing Major or greater damage to the Swarm. If bramble tokens are removed from a target using a Finesse Roll, a number of Tangle Bramble Minions spawn within Melee range equal to the number of tokens removed.

---

### Tangle Bramble

**_Tier 1 Minion._** _An animate, blood-drinking tumbleweed._

- **Motives & Tactics:** Combine, drain, entangle
- **Difficulty:** 11 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -1 | **Thorns:** Melee | 2 phy

#### Features

**_Minion (4) - Passive:_** The Bramble is defeated when they take any damage. For every 4 damage a PC deals to the Tangle Bramble, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Tangle Brambles within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 2 physical damage each. Combine this damage.

**_Drain and Multiply - Reaction:_** When an attack from the Bramble causes a target to mark HP and there are three or more Tangle Bramble Minions within Close range, you can combine the Minions into a Tangle Bramble Swarm Horde. The Horde's HP is equal to the number of Minions combined.

---

### Tiny Green Ooze

**_Tier 1 Skulk._** _A small moving mound of translucent green slime._

- **Motives & Tactics:** Camouflage, creep up
- **Difficulty:** 14 | **Thresholds:** 4/None | **HP:** 2 | **Stress:** 1
- **ATK:** -1 | **Ooze Appendage:** Melee | 1d4+1 mag

#### Features

**_Acidic Form - Passive:_** When the Ooze makes a successful attack, the target must mark an Armor Slot without receiving its benefits (they can still use armor to reduce the damage). If they can't mark an Armor Slot, they must mark an additional HP.

---

### Tiny Red Ooze

**_Tier 1 Skulk._** _A small moving mound of translucent flaming red slime_

- **Motives & Tactics:** Blaze, Camouflage
- **Difficulty:** 11 | **Thresholds:** 5/None | **HP:** 2 | **Stress:** 1
- **ATK:** -1 | **Ooze Appendage:** Melee | 1d4+2 mag

#### Features

**_Burning - Reaction:_** When a creature within Melee range deals damage to the Ooze, they take **1d6** direct magic damage.

---

### Weaponmaster

**_Tier 1 Bruiser._** _A master-at-arms wielding a sword twice their size._

- **Motives & Tactics:** Act first, aim for the weakest, intimidate
- **Difficulty:** 14 | **Thresholds:** 8/15 | **HP:** 6 | **Stress:** 3
- **ATK:** +2 | **Claymore:** Very Close | 1d12+2 phy

#### Features

**_Goading Strike - Action:_** Make a standard attack against a target. On a success, **mark a Stress** to _Taunt_ the target until their next successful attack. The next time the _Taunted_ target attacks, they have disadvantage against targets other than the Weaponmaster.

**_Adrenaline Burst - Action:_** Once per scene, **spend a Fear** to clear 2 HP and 2 Stress.

**_Momentum - Reaction:_** When the Weaponmaster makes a successful attack against a PC, you gain a Fear.

---

### Young Dryad

**_Tier 1 Leader._** _An imperious tree-person leading their forest's defenses._

- **Motives & Tactics:** Command, nurture, prune the unwelcome
- **Difficulty:** 11 | **Thresholds:** 6/11 | **HP:** 6 | **Stress:** 2
- **ATK:** +0 | **Scythe:** Melee | 1d8+5 phy
- **Experience:** Leadership +3

#### Features

**_Voice of the Forest - Action:_** **Mark a Stress** to spotlight **1d4** allies within range of a target they can attack without moving. On a success, their attacks deal half damage.

**_Thorny Cage - Action:_** **Spend a Fear** to form a cage around a target within Very Close range and _Restrain_ them until they're freed with a successful Strength Roll. When a creature makes an action roll against the cage, they must mark a Stress.

**_Momentum - Reaction:_** When the Dryad makes a successful attack against a PC, you gain a Fear.

---

### Zombie Pack

**_Tier 1 Horde (2/HP)._** _A group of shambling corpses instinctively moving together._

- **Motives & Tactics:** Consume flesh, hunger, maul
- **Difficulty:** 8 | **Thresholds:** 6/12 | **HP:** 6 | **Stress:** 3
- **ATK:** -1 | **Bite:** Melee | 1d10+2 phy

#### Features

**_Horde (1d4+2) - Passive:_** When the Zombies have marked half or more of their HP, their standard attack deals **1d4+2** physical damage instead.

**_Overwhelm - Reaction:_** When the Zombies mark HP from an attack within Melee range, you can **mark a Stress** to make a standard attack against the attacker.
## Tier 2 Adversaries (Levels 2–4)

### Apprentice Assassin

**_Tier 2 Minion._** _A young trainee eager to prove themselves._

- **Motives & Tactics:** Act reckless, kill, prove their worth, show off
- **Difficulty:** 13 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** -1 | **Thrown Dagger:** Very Close | 4 phy
- **Experience:** Intrusion +2

#### Features

**_Minion (6) - Passive:_** The Assassin is defeated when they take any damage. For every 6 damage a PC deals to the Assassin, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Apprentice Assassins within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 4 physical damage each. Combine this damage.

---

### Archer Squadron

**_Tier 2 Horde (2/HP)._** _A group of trained archers bearing massive bows._

- **Motives & Tactics:** Stick together, survive, volley fire
- **Difficulty:** 13 | **Thresholds:** 8/16 | **HP:** 4 | **Stress:** 3
- **ATK:** +0 | **Longbow:** Far | 2d6+3 phy

#### Features

**_Horde (1d6+3) - Passive:_** When the Squadron has marked half or more of their HP, their standard attack deals **1d6+3** physical damage instead.

**_Focused Volley - Action:_** **Spend a Fear** to target a point within Far range. Make an attack with advantage against all targets within Close range of that point. Targets the Squadron succeeds against take **1d10+4** physical damage.

**_Suppressing Fire - Action:_** **Mark a Stress** to target a point within Far range. Until the next roll with Fear, a creature who moves within Close range of that point must make an Agility Reaction Roll. On a failure, they take **2d6+3** physical damage. On a success, they take half damage.

---

### Assassin Poisoner

**_Tier 2 Skulk._** _A cunning scoundrel skilled in both poisons and ambushing._

- **Motives & Tactics:** Anticipate, get paid, kill, taint food and water
- **Difficulty:** 14 | **Thresholds:** 8/16 | **HP:** 4 | **Stress:** 4
- **ATK:** +3 | **Poisoned Throwing Dagger:** Close | 2d8+1 phy
- **Experience:** Intrusion +2

#### Features

**_Grindletooth Venom - Passive:_** Targets who mark HP from the Assassin's attacks are _Vulnerable_ until they clear a HP.

**_Out of Nowhere - Passive:_** The Assassin has advantage on attacks if they are _Hidden_.

**_Fumigation - Action:_** Drop a smoke bomb that fills the air within Close range with smoke, _Dizzying_ all targets in this area. _Dizzied_ targets have disadvantage on their next action roll, then clear the condition.

---

### Battle Box

**_Tier 2 Solo._** _A cube-shaped construct with a different rune on each of their six sides._

- **Motives & Tactics:** Change tactics, trample foes, wait in disguise
- **Difficulty:** 15 | **Thresholds:** 10/20 | **HP:** 8 | **Stress:** 6
- **ATK:** +2 | **Slam:** Melee | 2d6+3 phy
- **Experience:** Camouflage +2

#### Features

**_Relentless (2) - Passive:_** The Box can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Randomized Tactics - Action:_** **Mark a Stress** and roll a **d6**. The Box uses the corresponding move:

- 1. _Mana Beam._ The Box fires a searing beam. Make an attack against a target within Far range. On a success, deal **2d10+2** magic damage.
- 2. _Fire Jets._ The Box shoots into the air, spinning and releasing jets of flame. Make an attack against all targets within Close range. Targets the Box succeeds against take **2d8** physical damage.
- 3. _Trample._ The Box rockets around erratically. Make an attack against all PCs within Close range. Targets the Box succeeds against take **1d6+5** physical damage and are _Vulnerable_ until their next roll with Hope.
- 4. _Shocking Gas._ The Box sprays out a silver gas sparking with lightning. All targets within Close range must succeed on a Finesse Reaction Roll or mark 3 Stress.
- 5. _Stunning Clap._ The Box leaps and their sides clap, creating a small sonic boom. All targets within Very Close range must succeed on a Strength Reaction Roll or become _Vulnerable_ until the cube is defeated.
- 6. _Psionic Whine._ The Box releases a cluster of mechanical bees whose buzz rattles mortal minds. All targets within Close range must succeed on a Presence Reaction Roll or take **2d4+9** direct magic damage.

**_Overcharge - Reaction:_** Before rolling damage for the Box's attack, you can **mark a Stress** to add a **d6** to the damage roll. Additionally, you gain a Fear.

**_Death Quake - Reaction:_** When the Box marks their last HP, the magic powering them ruptures in an explosion of force. All targets within Close range must succeed on an Instinct Reaction Roll or take **2d8+1** magic damage.

---

### Chaos Skull

**_Tier 2 Ranged._** _A floating humanoid skull animated by scintillating magic._

- **Motives & Tactics:** Cackle, consume magic, serve creator
- **Difficulty:** 15 | **Thresholds:** 8/16 | **HP:** 5 | **Stress:** 4
- **ATK:** +2 | **Energy Blast:** Close | 2d8+3 mag

#### Features

**_Levitation - Passive:_** The Skull levitates several feet off the ground and can't be _Restrained_.

**_Wards - Passive:_** The Skull is resistant to magic damage.

**_Magic Burst - Action:_** **Mark a Stress** to make an attack against all targets within Close range. Targets the Skull succeeds against take **2d6+4** magic damage.

**_Siphon Magic - Action:_** **Spend a Fear** to make an attack against a PC with a Spellcast trait within Very Close range. On a success, the target marks **1d4** Stress and the Skull clears that many Stress. Additionally, on a success, the Skull can immediately be spotlighted again.

---

### Conscript

**_Tier 2 Minion._** _A poorly trained civilian pressed into war._

- **Motives & Tactics:** Follow orders, gang up, survive
- **Difficulty:** 12 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +0 | **Spears:** Very Close | 6 phy

#### Features

**_Minion (6) - Passive:_** The Conscript is defeated when they take any damage. For every 6 damage a PC deals to the Conscript, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Conscripts within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 6 physical damage each. Combine this damage.

---

### Courtesan

**_Tier 2 Social._** _An accomplished manipulator and master of the social arts._

- **Motives & Tactics:** Entice, maneuver, secure patrons
- **Difficulty:** 13 | **Thresholds:** 7/13 | **HP:** 3 | **Stress:** 4
- **ATK:** -3 | **Dagger:** Melee | 1d4+3 phy
- **Experience:** Manipulation +3, Socialite +3

#### Features

**_Searing Glance - Reaction:_** When a PC within Close range makes a Presence Roll, you can **mark a Stress** to cast a gaze toward the aftermath. On the target's failure, they must mark 2 Stress and are _Vulnerable_ until the scene ends or they succeed on a social action against the Courtesan. On the target's success, they must mark a Stress.

---

### Cult Adept

**_Tier 2 Support._** _An experienced mage wielding shadow and fear._

- **Motives & Tactics:** Curry favor, hinder foes, uncover knowledge
- **Difficulty:** 14 | **Thresholds:** 9/18 | **HP:** 4 | **Stress:** 6
- **ATK:** +2 | **Rune-Covered Rod:** Far | 2d4+3 mag
- **Experience:** Fallen Lore +2, Rituals +2

#### Features

**_Enervating Blast - Action:_** **Spend a Fear** to make a standard attack against a target within range. On a success, the target must mark a Stress.

**_Shroud of the Fallen - Action:_** **Mark a Stress** to wrap an ally within Close range in a shroud of _Protection_ until the Adept marks their last HP. While _Protected_, the target has resistance to all damage.

**_Shadow Shackles - Action:_** **Spend a Fear** and choose a point within Far range. All targets within Close range of that point are _Restrained_ in smoky chains until they break free with a successful Strength or Instinct Roll. A target _Restrained_ by this feature must spend a Hope to make an action roll.

**_Fear Is Fuel - Reaction:_** Twice per scene, when a PC rolls a failure with Fear, clear a Stress.

---

### Cult Fang

**_Tier 2 Skulk._** _A professional killer-turned-cultist._

- **Motives & Tactics:** Capture sacrifices, isolate prey, rise in the ranks
- **Difficulty:** 15 | **Thresholds:** 9/17 | **HP:** 4 | **Stress:** 4
- **ATK:** +2 | **Long Knife:** Melee | 2d8+4 phy

#### Features

**_Shadow's Embrace - Passive:_** The Fang can climb and walk on vertical surfaces. **Mark a Stress** to move from one shadow to another within Far range.

**_Pick Off the Straggler - Action:_** **Mark a Stress** to cause a target within Melee range to make an Instinct Reaction Roll. On a failure, the target must mark 2 Stress and is teleported with the Fang to a shadow within Far range, making them temporarily _Vulnerable_. On a success, the target must mark a Stress.

---

### Cult Initiate

**_Tier 2 Minion._** _A low-ranking cultist in simple robes, eager to gain power._

- **Motives & Tactics:** Follow orders, gain power, seek forbidden knowledge
- **Difficulty:** 13 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +0 | **Ritual Dagger:** Melee | 5 phy

#### Features

**_Minion (6) - Passive:_** The Initiate is defeated when they take any damage. For every 6 damage a PC deals to the Initiate, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Cult Initiates within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 5 physical damage each. Combine this damage.

---

### Demonic Hound Pack

**_Tier 2 Horde (1/HP)._** _Unnatural hounds lit from within by hellfire._

- **Motives & Tactics:** Cause fear, consume flesh, please masters
- **Difficulty:** 15 | **Thresholds:** 11/23 | **HP:** 6 | **Stress:** 3
- **ATK:** +0 | **Claws and Fangs:** Melee | 2d8+2 phy
- **Experience:** Scent Tracking +3

#### Features

**_Horde (2d4+1) - Passive:_** When the Pack has marked half or more of their HP, their standard attack deals **2d4+1** physical damage instead.

**_Dreadhowl - Action:_** **Mark a Stress** to make all targets within Very Close range lose a Hope. If a target is not able to lose a Hope, they must instead mark 2 Stress.

**_Momentum - Reaction:_** When the Pack makes a successful attack against a PC, you gain a Fear.

---

### Electric Eels

**_Tier 2 Horde (/HP)._** _A swarm of eels that encircle and electrocute._

- **Motives & Tactics:** Avoid larger predators, shock prey, tear apart
- **Difficulty:** 14 | **Thresholds:** 10/20 | **HP:** 5 | **Stress:** 3
- **ATK:** +0 | **Shocking Bite:** Melee | 2d6+4 phy

#### Features

**_Horde (2d4+1) - Passive:_** When the Eels have marked half or more of their HP, their standard attack deals **2d4+1** physical damage instead.

**_Paralyzing Shock - Action:_** **Mark a Stress** to make a standard attack against all targets within Very Close range. You gain a Fear for each target that marks HP.

---

### Elite Soldier

**_Tier 2 Standard._** _An armored squire or experienced commoner looking to advance._

- **Motives & Tactics:** Gain glory, keep order, make alliances
- **Difficulty:** 15 | **Thresholds:** 9/18 | **HP:** 4 | **Stress:** 3
- **ATK:** +1 | **Spear:** Very Close | 2d8+4 phy

#### Features

**_Reinforce - Action:_** **Mark a Stress** to move into Melee range of an ally and make a standard attack against a target within Very Close range. On a success, deal **2d10+2** physical damage and the ally can clear a Stress.

**_Vassal's Loyalty - Reaction:_** When the Soldier is within Very Close range of a knight or other noble who would take damage, you can **mark a Stress** to move into Melee range of them and take the damage instead.

---

### Failed Experiment

**_Tier 2 Standard._** _A magical necromantic experiment gone wrong, leaving them warped and ungainly._

- **Motives & Tactics:** Devour, hunt, track
- **Difficulty:** 13 | **Thresholds:** 12/23 | **HP:** 3 | **Stress:** 3
- **ATK:** +1 | **Bite and Claw:** Melee | 2d6+5 phy
- **Experience:** Copycat +3

#### Features

**_Warped Fortitude - Passive:_** The Experiment is resistant to physical damage.

**_Overwhelm - Passive:_** When a target the Experiment attacks has other adversaries within Very Close range, the Experiment deals double damage.

**_Lurching Lunge - Action:_** **Mark a Stress** to spotlight the Experiment as an additional GM move instead of spending Fear.

---

### Giant Beastmaster

**_Tier 2 Leader._** _A leather-clad warrior bearing a whip and massive bow._

- **Motives & Tactics:** Command, make a living, maneuver, pin down, protect companion animals
- **Difficulty:** 16 | **Thresholds:** 12/24 | **HP:** 6 | **Stress:** 5
- **ATK:** +2 | **Longbow:** Far | 2d8+4 phy
- **Experience:** Animal Handling +3

#### Features

**_Two as One - Passive:_** When the Beastmaster is spotlighted, you can also spotlight a Tier 1 animal adversary currently under their control.

**_Pinning Strike - Action:_** Make a standard attack against a target. On a success, you can **mark a Stress** to pin them to a nearby surface. The pinned target is _Restrained_ until they break free with a successful Finesse or Strength Roll.

**_Deadly Companion - Action:_** Twice per scene, summon a Bear, Dire Wolf, or similar Tier 1 animal adversary under the Beastmaster's control. The adversary appears at Close range and is immediately spotlighted.

---

### Giant Brawler

**_Tier 2 Bruiser._** _An especially muscular giant wielding a warhammer larger than a human._

- **Motives & Tactics:** Make a living, overwhelm, slam, topple
- **Difficulty:** 15 | **Thresholds:** 14/28 | **HP:** 7 | **Stress:** 4
- **ATK:** +2 | **Warhammer:** Very Close | 2d12+3 phy
- **Experience:** Intrusion +2

#### Features

**_Battering Ram - Action:_** **Mark a Stress** to have the Brawler charge at an inanimate object within Close range they could feasibly smash (such as a wall, cart, or market stand) and destroy it. All targets within Very Close range of the object must succeed on an Agility Reaction Roll or take **2d4+3** physical damage from the shrapnel.

**_Bloody Reprisal - Reaction:_** When the Brawler marks 2 or more HP from an attack within Very Close range, you can make a standard attack against the attacker. On a success, the Brawler deals **2d6+15** physical damage instead of their standard damage.

**_Momentum - Reaction:_** When the Brawler makes a successful attack against a PC, you gain a Fear.

---

### Giant Eagle

**_Tier 2 Skulk._** _A giant bird of prey with blood-stained talons._

- **Motives & Tactics:** Hunt prey, stay mobile, strike decisively
- **Difficulty:** 14 | **Thresholds:** 8/19 | **HP:** 4 | **Stress:** 4
- **ATK:** +1 | **Claws and Beak:** Very Close | 2d6+3 phy

#### Features

**_Flight - Passive:_** While flying, the Eagle gains a +3 bonus to their Difficulty.

**_Deadly Dive - Action:_** **Mark a Stress** to attack a target within Far range. On a success, deal **2d10+2** physical damage and knock the target over, making them _Vulnerable_ until they next act.

**_Take Off- Action:_** Make an attack against a target within Very Close range. On a success, deal **2d4+3** physical damage and the target must succeed on an Agility Reaction Roll or become temporarily _Restrained_ within the Eagle's massive talons. If the target is _Restrained_, the Eagle immediately lifts into the air to Very Far range above the battlefield while holding them.

**_Deadly Drop - Action:_** While flying, the Eagle can drop a _Restrained_ target they are holding. When dropped, the target is no longer _Restrained_ but starts falling. If their fall isn't prevented during the PCs' next action, the target takes **2d20** physical damage when they land.

---

### Giant Recruit

**_Tier 2 Minion._** _A giant fighter wearing borrowed armor._

- **Motives & Tactics:** Batter, make a living, overwhelm, terrify
- **Difficulty:** 13 | **Thresholds:** None | **HP:** 1 | **Stress:** 2
- **ATK:** +1 | **Warhammer:** Very Close | 5 phy

#### Features

**_Minion (7) - Passive:_** The Recruit is defeated when they take any damage. For every 7 damage a PC deals to the Recruit, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Giant Recruits within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 5 physical damage each. Combine this damage.

---

### Gorgon

**_Tier 2 Solo._** _A snake-headed, scaled humanoid with a gilded bow, enraged that their peace has been disturbed._

- **Motives & Tactics:** Corner, hit-and-run, petrify, seek vengeance
- **Difficulty:** 15 | **Thresholds:** 13/25 | **HP:** 9 | **Stress:** 3
- **ATK:** +4 | **Sunsear Shortbow:** Far | 2d20+3 mag
- **Experience:** Stealth +3

#### Features

**_Relentless (2) - Passive:_** The Gorgon can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Sunsear Arrows - Passive:_** When the Gorgon makes a successful standard attack, the target _Glows_ until the end of the scene and can't become _Hidden_. Attack rolls made against a _Glowing_ target have advantage.

**_Crown of Serpents - Action:_** Make an attack roll against a target within Melee range using the Gorgon's protective snakes. On a success, **mark a Stress** to deal **2d10+4** physical damage and the target must mark a Stress.

**_Petrifying Gaze - Reaction:_** When the Gorgon takes damage from an attack within Close range, you can **spend a Fear** to force the attacker to make an Instinct Reaction Roll. On a failure, they begin to turn to stone, marking a HP and starting a Petrification Countdown (4). This countdown ticks down when the Gorgon is attacked. When it triggers, the target must make a death move. If the Gorgon is defeated, all petrification countdowns end.

**_Momentum - Reaction:_** When the Gorgon makes a successful attack against a PC, you gain a Fear.

---

### Juvenile Flickerfly

**_Tier 2 Solo._** _A horse-sized insect with iridescent scales and crystalline wings moving faster than the eye can see._

- **Motives & Tactics:** Collect shiny things, hunt, swoop
- **Difficulty:** 14 | **Thresholds:** 13/26 | **HP:** 10 | **Stress:** 5
- **ATK:** +3 | **Wing Slash:** Very Close | 2d10+4 phy

#### Features

**_Relentless (3) - Passive:_** The Flickerfly can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Peerless Accuracy - Passive:_** Before the Flickerfly makes an attack, roll a **d6**. On a result of 4 or higher, the target's Evasion is halved against this attack.

**_Mind Dance - Action:_** **Mark a Stress** to create a magically dazzling display that grapples the minds of nearby foes. All targets within Close range must make an Instinct Reaction Roll. For each target who failed, you gain a Fear and the Flickerfly learns one of the target's fears.

**_Hallucinatory Breath - Reaction: Countdown (Loop 1d6):_** When the Flickerfly takes damage for the first time, activate the countdown. When it triggers, the Flickerfly breathes hallucinatory gas on all targets in front of them up to Far range. Targets must succeed on an Instinct Reaction Roll or be tormented by fearful hallucinations. Targets whose fears are known to the Flickerfly have disadvantage on this roll. Targets who fail must mark a Stress and lose a Hope.

---

### Knight of the Realm

**_Tier 2 Leader._** _A decorated soldier with heavy armor and a powerful steed._

- **Motives & Tactics:** Run down, seek glory, show dominance
- **Difficulty:** 15 | **Thresholds:** 13/26 | **HP:** 6 | **Stress:** 4
- **ATK:** +4 | **Longsword:** Melee | 2d10+4 phy
- **Experience:** Ancient Knowledge +3, High Society +2, Tactics +2

#### Features

**_Chevalier - Passive:_** While the Knight is on a mount, they gain a +2 bonus to their Difficulty. When they take Severe damage, they're knocked from their mount and lose this benefit until they're next spotlighted.

**_Heavily Armored - Passive:_** When the Knight takes physical damage, reduce it by 3.

**_Cavalry Charge - Action:_** If the Knight is mounted, move up to Far range and make a standard attack against a target. On a success, deal **2d8+4** physical damage and the target must mark a Stress.

**_For the Realm! - Action:_** **Mark a Stress** to spotlight **1d4+1** allies. Attacks they make while spotlighted in this way deal half damage.

---

### Masked Thief

**_Tier 2 Skulk._** _A cunning thief with acrobatic skill and a flair for the dramatic._

- **Motives & Tactics:** Evade, hide, pilfer, profit
- **Difficulty:** 14 | **Thresholds:** 8/17 | **HP:** 4 | **Stress:** 5
- **ATK:** +3 | **Backsword:** Melee | 2d8+3 phy
- **Experience:** Acrobatics +3

#### Features

**_Quick Hands - Action:_** Make an attack against a target within Melee range. On a success, deal **1d8+2** physical damage and the Thief steals one item or consumable from the target's inventory.

**_Escape Plan - Action:_** **Mark a Stress** to reveal a snare trap set anywhere on the battlefield by the Thief. All targets within Very Close range of the trap must succeed on an Agility Reaction Roll (13) or be pulled off their feet and suspended upside down. A target is _Restrained_ and _Vulnerable_ until they break free, ending both conditions, with a successful Finesse or Strength Roll (13).

---

### Master Assassin

**_Tier 2 Leader._** _A seasoned killer with a threatening voice and a deadly blade._

- **Motives & Tactics:** Ambush, get out alive, kill, prepare for all scenarios
- **Difficulty:** 15 | **Thresholds:** 12/25 | **HP:** 7 | **Stress:** 5
- **ATK:** +5 | **Serrated Dagger:** Close | 2d10+2 phy
- **Experience:** Command +3, Intrusion +3

#### Features

**_Won't See It Coming - Passive:_** The Assassin deals direct damage while they're _Hidden_.

**_Strike as One - Action:_** **Mark a Stress** to spotlight a number of other Assassins equal to the Assassin's unmarked Stress.

**_The Subtle Blade - Reaction:_** When the Assassin successfully makes a standard attack against a _Vulnerable_ target, you can **spend a Fear** to deal Severe damage instead of their standard damage.

**_Momentum - Reaction:_** When the Assassin makes a successful attack against a PC, you gain a Fear.

---

### Merchant Baron

**_Tier 2 Social._** _An accomplished merchant with a large operation under their command._

- **Motives & Tactics:** Abuse power, gather resources, mobilize minions
- **Difficulty:** 15 | **Thresholds:** 9/19 | **HP:** 5 | **Stress:** 3
- **ATK:** -2 | **Rapier:** Melee | 1d6+2 phy
- **Experience:** Nobility +2, Trade +2

#### Features

**_Everyone Has a Price - Action:_** **Spend a Fear** to offer a target a dangerous bargain for something they want or need. If used on a PC, they must make a Presence Reaction Roll (17). On a failure, they must mark 2 Stress or take the deal.

**_The Best Muscle Money Can Buy - Action:_** Once per scene, **mark a Stress** to summon **1d4+1** Tier 1 adversaries, who appear at Far range, to enforce the Baron's will.

---

### Minotaur Wrecker

**_Tier 2 Bruiser._** _A massive bull-headed firbolg with a quick temper._

- **Motives & Tactics:** Consume, gore, navigate, overpower, pursue
- **Difficulty:** 16 | **Thresholds:** 14/27 | **HP:** 7 | **Stress:** 5
- **ATK:** +2 | **Battleaxe:** Very Close | 2d8+5 phy
- **Experience:** Navigation +2

#### Features

**_Ramp Up - Passive:_** You must **spend a Fear** to spotlight the Minotaur. While spotlighted, they can make their standard attack against all targets within range.

**_Charging Bull - Action:_** **Mark a Stress** to charge through a group within Close range and make an attack against all targets in the Minotaur's path. Targets the Minotaur succeeds against take **2d6+8** physical damage and are knocked back to Very Far range. If a target is knocked into a solid object or another creature, they take an extra **1d6** damage (combine the damage).

**_Gore - Action:_** Make an attack against a target within Very Close range, moving the Minotaur into Melee range of them. On a success, deal **2d8** direct physical damage.

---

### Mortal Hunter

**_Tier 2 Leader._** _An undead figure wearing a heavy leather coat, with searching eyes and a casually cruel demeanor._

- **Motives & Tactics:** Devour, hunt, track
- **Difficulty:** 16 | **Thresholds:** 15/27 | **HP:** 6 | **Stress:** 4
- **ATK:** +5 | **Tear at Flesh:** Very Close | 2d12+1 phy
- **Experience:** Bloodhound +3

#### Features

**_Terrifying - Passive:_** When the Hunter makes a successful attack, all PCs within Far range lose a Hope and you gain a Fear.

**_Deathlock - Action:_** **Spend a Fear** to curse a target within Very Close range with a necrotic _Deathlock_ until the end of the scene. Attacks made by the Hunter against a _Deathlocked_ target deal direct damage. The Hunter can only maintain one _Deathlock_ at a time.

**_Inevitable Death - Action:_** **Mark a Stress** to spotlight **1d4** allies. Attacks they make while spotlighted in this way deal half damage.

**_Rampage - Reaction: Countdown (Loop 1d6):_** When the Hunter is in the spotlight for the first time, activate the countdown. When it triggers, move the Hunter in a straight line to a point within Far range and make an attack against all targets in their path. Targets the Hunter succeeds against take **2d8+2** physical damage.

---

### Royal Advisor

**_Tier 2 Social._** _A high-ranking courtier with the ear of the local nobility._

- **Motives & Tactics:** Curry favor, manufacture evidence, scheme
- **Difficulty:** 14 | **Thresholds:** 8/15 | **HP:** 3 | **Stress:** 3
- **ATK:** -3 | **Wand:** Far | 1d4+3 phy
- **Experience:** Administration +3, Courtier +3

#### Features

**_Devastating Retort - Passive:_** A PC who rolls less than 17 on an action roll targeting the Advisor must mark a Stress.

**_Bend Ears - Action:_** **Mark a Stress** to influence an NPC within Melee range with whispered words. That target's opinion on one matter shifts toward the Advisor's preference unless it is in direct opposition to the target's motives.

**_Scapegoat - Action:_** **Spend a Fear** to convince a crowd or notable individual that one person or group is responsible for some problem facing the target. The target becomes hostile to the scapegoat until convinced of their innocence with a successful Presence Roll (17).

---

### Secret-Keeper

**_Tier 2 Leader._** _A clandestine leader with a direct channel to the Fallen Gods._

- **Motives & Tactics:** Amass great power, plot, take command
- **Difficulty:** 16 | **Thresholds:** 13/26 | **HP:** 7 | **Stress:** 4
- **ATK:** +3 | **Sigil-laden Staff:** Far | 2d12 mag
- **Experience:** Coercion +2, Fallen Lore +2

#### Features

**_Seize Your Moment - Action:_** **Spend 2 Fear** to spotlight **1d4** allies. Attacks they make while spotlighted in this way deal half damage.

**_Our Master's Will - Reaction:_** When you spotlight an ally within Far range, **mark a Stress** to gain a Fear.

**_Summoning Ritual - Reaction: Countdown (6):_** When the Secret-Keeper is in the spotlight for the first time, activate the countdown. When they mark HP, tick down this countdown by the number of HP marked. When it triggers, summon a Minor Demon who appears at Close range.

**_Fallen Hounds - Reaction:_** Once per scene, when the Secret-Keeper marks 2 or more HP, you can **mark a Stress** to summon a Demonic Hound Pack, which appears at Close range and is immediately spotlighted.

---

### Shark

**_Tier 2 Bruiser._** _A large aquatic predator, always on the move._

- **Motives & Tactics:** Find the blood, isolate prey, target the weak
- **Difficulty:** 14 | **Thresholds:** 14/28 | **HP:** 7 | **Stress:** 3
- **ATK:** +2 | **Toothy Maw:** Very Close | 2d12+1 phy
- **Experience:** Sense of Smell +3

#### Features

**_Terrifying - Passive:_** When the Shark makes a successful attack, all PCs within Far range lose a Hope and you gain a Fear.

**_Rending Bite - Passive:_** When the Shark makes a successful attack, the target must mark an Armor Slot without receiving its benefits (they can still use armor to reduce the damage). If they can't mark an Armor Slot, they must mark an additional HP.

**_Blood in the Water - Reaction:_** When a creature within Close range of the Shark marks HP from another creature's attack, you can **mark a Stress** to immediately spotlight the Shark, moving them into Melee range of the target and making a standard attack.

---

### Siren

**_Tier 2 Skulk._** _A half-fish person with shimmering scales and an irresistible voice._

- **Motives & Tactics:** Consume, lure prey, subdue with song
- **Difficulty:** 14 | **Thresholds:** 9/18 | **HP:** 5 | **Stress:** 3
- **ATK:** +2 | **Distended Jaw Bite:** Melee | 2d6+3 phy
- **Experience:** Song Repertoire +3

#### Features

**_Captive Audience - Passive:_** If the Siren makes a standard attack against a target _Entranced_ by their song, the attack deals **2d10+1** damage instead of their standard damage.

**_Enchanting Song - Action:_** **Spend a Fear** to sing a song that affects all targets within Close range. Targets must succeed on an Instinct Reaction Roll or become _Entranced_ until they mark 2 Stress. Other Sirens within Close range of the target can **mark a Stress** to each add a +1 bonus to the Difficulty of the reaction roll. While _Entranced_, a target can't act and is _Vulnerable_.

---

### Spectral Archer

**_Tier 2 Ranged._** _A ghostly fighter with an ethereal bow, unable to move on while their charge is vulnerable._

- **Motives & Tactics:** Move through solid objects, stay out of the fray, rehash old battles
- **Difficulty:** 13 | **Thresholds:** 6/14 | **HP:** 3 | **Stress:** 3
- **ATK:** +3 | **Longbow:** Far | 2d10+2 phy
- **Experience:** Ancient Knowledge +2

#### Features

**_Ghost - Passive:_** The Archer has resistance to physical damage. **Mark a Stress** to move up to Close range through solid objects.

**_Pick Your Target - Action:_** **Spend a Fear** to make an attack within Far range against a PC who is within Very Close range of at least two other PCs. On a success, the target takes **2d8+12** physical damage.

---

### Spectral Captain

**_Tier 2 Leader._** _A ghostly commander leading their troops beyond death._

- **Motives & Tactics:** Move through solid objects, rally troops, rehash old battles
- **Difficulty:** 16 | **Thresholds:** 13/26 | **HP:** 6 | **Stress:** 4
- **ATK:** +3 | **Longbow:** Far | 2d10+3 phy
- **Experience:** Ancient Knowledge +3

#### Features

**_Ghost - Passive:_** The Captain has resistance to physical damage. **Mark a Stress** to move up to Close range through solid objects.

**_Unending Battle - Action:_** **Spend 2 Fear** to return up to **1d4+1** defeated Spectral allies to the battle at the points where they first appeared (with no marked HP or Stress).

**_Hold Fast - Reaction:_** When the Captain's Spectral allies are forced to make a reaction roll, you can **mark a Stress** to give those allies a +2 bonus to the roll.

**_Momentum - Reaction:_** When the Captain makes a successful attack against a PC, you gain a Fear.

---

### Spectral Guardian

**_Tier 2 Standard._** _A ghostly fighter with spears and swords, anchored by duty._

- **Motives & Tactics:** Move through solid objects, protect treasure, rehash old battles
- **Difficulty:** 15 | **Thresholds:** 7/15 | **HP:** 4 | **Stress:** 3
- **ATK:** +1 | **Spear:** Very Close | 2d8+1 phy
- **Experience:** Ancient Knowledge +2

#### Features

**_Ghost - Passive:_** The Guardian has resistance to physical damage. **Mark a Stress** to move up to Close range through solid objects.

**_Grave Blade - Action:_** **Spend a Fear** to make an attack against a target within Very Close range. On a success, deal **2d10+6** physical damage and the target must mark a Stress.

---

### Spy

**_Tier 2 Social._** _A skilled espionage agent with a knack for being in the right place to overhear secrets._

- **Motives & Tactics:** Cut and run, disguise appearance, eavesdrop
- **Difficulty:** 15 | **Thresholds:** 8/17 | **HP:** 4 | **Stress:** 3
- **ATK:** -2 | **Dagger:** Melee | 2d6+3 phy
- **Experience:** Espionage +3

#### Features

**_Gathering Secrets - Action:_** **Spend a Fear** to describe how the Spy knows a secret about a PC in the scene.

**_Fly on the Wall - Reaction:_** When a PC or group is discussing something sensitive, you can **mark a Stress** to reveal that the Spy is present in the scene, observing them. If the Spy escapes the scene to report their findings, you gain **1d4** Fear.

---

### Stonewraith

**_Tier 2 Skulk._** _A prowling hunter, like a slinking mountain lion, with a slate-gray stone body._

- **Motives & Tactics:** Defend territory, isolate prey, stalk
- **Difficulty:** 13 | **Thresholds:** 11/22 | **HP:** 6 | **Stress:** 3
- **ATK:** +3 | **Bite and Claws:** Melee | 2d8+6 phy
- **Experience:** Stonesense +3

#### Features

**_Stonestrider - Passive:_** The Stonewraith can move through stone and earth as easily as air. While within stone or earth, they are _Hidden_ and immune to all damage.

**_Rocky Ambush - Action:_** While _Hidden_, **mark a Stress** to leap into Melee range with a target within Very Close range. The target must succeed on an Agility or Instinct Reaction Roll (15) or take **2d8** physical damage and become temporarily _Restrained_.

**_Avalanche Roar - Action:_** **Spend a Fear** to roar while within a cave and cause a cave-in. All targets within Close range must succeed on an Agility Reaction Roll (14) or take **2d10** physical damage. The rubble can be cleared with a Progress Countdown (8).

**_Momentum - Reaction:_** When the Stonewraith makes a successful attack against a PC, you gain a Fear.

---

### War Wizard

**_Tier 2 Ranged._** _A battle-hardened mage trained in destructive magic._

- **Motives & Tactics:** Develop new spells, seek power, shatter formations
- **Difficulty:** 16 | **Thresholds:** 11/23 | **HP:** 5 | **Stress:** 6
- **ATK:** +4 | **Staff:** Far | 2d10+4 mag
- **Experience:** Magical Knowledge +2, Strategize +2

#### Features

**_Battle Teleport - Passive:_** Before or after making a standard attack, you can **mark a Stress** to teleport to a location within Far range.

**_Refresh Warding Sphere - Action:_** **Mark a Stress** to refresh the Wizard's "Warding Sphere" reaction.

**_Eruption - Action:_** **Spend a Fear** and choose a point within Far range. A Very Close area around that point erupts into impassable terrain. All targets within that area must make an Agility Reaction Roll (14). Targets who fail take **2d10** physical damage and are thrown out of the area. Targets who succeed take half damage and aren't moved.

**_Arcane Artillery - Action:_** **Spend a Fear** to unleash a precise hail of magical blasts. All targets in the scene must make an Agility Reaction Roll. Targets who fail take **2d12** magic damage. Targets who succeed take half damage.

**_Warding Sphere - Reaction:_** When the Wizard takes damage from an attack within Close range, deal **2d6** magic damage to the attacker. This reaction can't be used again until the Wizard refreshes it with their "Refresh Warding Sphere" action.
## Tier 3 Adversaries (Levels 5–7)

### Adult Flickerfly

**_Tier 3 Solo._** _A winged insect the size of a large house with iridescent scales and wings that move too fast to track._

- **Motives & Tactics:** Collect shiny things, hunt, nest, swoop
- **Difficulty:** 17 | **Thresholds:** 20/35 | **HP:** 12 | **Stress:** 6
- **ATK:** +3 | **Wing Slash:** Very Close | 3d20 phy

#### Features

**_Relentless (4) - Passive:_** The Flickerfly can be spotlighted up to four times per GM turn. Spend Fear as usual to spotlight them.

**_Never Misses - Passive:_** When the Flickerfly makes an attack, the target's Evasion is halved against the attack.

**_Deadly Flight - Passive:_** While flying, the Flickerfly can move up to Far range instead of Close range before taking an action.

**_Whirlwind - Action:_** **Spend a Fear** to whirl, making an attack against all targets within Very Close range. Targets the Flickerfly succeeds against take **3d8** direct physical damage.

**_Mind Dance - Action:_** **Mark a Stress** to create a magically dazzling display that grapples the minds of nearby foes. All targets within Close range must make an Instinct Reaction Roll. For each target who failed, you gain a Fear and the Flickerfly learns one of the target's fears.

**_Hallucinatory Breath - Reaction: Countdown (Loop 1d6):_** When the Flickerfly takes damage for the first time, activate the countdown. When it triggers, the Flickerfly breathes hallucinatory gas on all targets in front of them up to Far range. Targets must make an Instinct Reaction Roll or be tormented by fearful hallucinations. Targets whose fears are known to the Flickerfly have disadvantage on this roll. Targets who fail lose 2 Hope and take **3d8+3** direct magic damage.

**_Uncanny Reflexes - Reaction:_** When the Flickerfly takes damage from an attack within Close range, you can **mark a Stress** to take half damage.

---

### Demon of Avarice

**_Tier 3 Support._** _A regal cloaked monstrosity with circular horns adorned with treasure._

- **Motives & Tactics:** Consume, fuel greed, sow dissent
- **Difficulty:** 17 | **Thresholds:** 15/29 | **HP:** 6 | **Stress:** 5
- **ATK:** +2 | **Hungry Maw:** Melee | 3d6+5 mag
- **Experience:** Manipulation +3

#### Features

**_Money Talks - Passive:_** Attacks against the Demon are made with disadvantage unless the attacker spends a handful of gold. This Demon starts with a number of handfuls equal to the number of PCs. When a target marks HP from the Demon's standard attack, they can spend a handful of gold instead of marking HP (1 handful per HP). Add a handful of gold to the Demon for each handful of gold spent by PCs on this feature.

**_Numbers Must Go Up - Passive:_** Add a bonus to the Demon's attack rolls equal to the number of handfuls of gold they have.

**_Money Is Time - Action:_** **Spend 3 handfuls of gold (or a Fear)** to spotlight **1d4+1** allies.

---

### Demon of Despair

**_Tier 3 Skulk._** _A cloaked demon-creature with long limbs, seeping shadows._

- **Motives & Tactics:** Make fear contagious, stick to the shadows, undermine resolve
- **Difficulty:** 17 | **Thresholds:** 18/35 | **HP:** 6 | **Stress:** 5
- **ATK:** +3 | **Miasma Bolt:** Far | 3d6+1 mag
- **Experience:** Manipulation +3

#### Features

**_Depths of Despair - Passive:_** The Demon deals double damage to PCs with 0 Hope.

**_Your Struggle Is Pointless - Action:_** **Spend a Fear** to weigh down the spirits of all PCs within Far range. All targets affected replace their Hope Die with a **d8** until they roll a success with Hope or their next rest.

**_Your Friends Will Fail You - Reaction:_** When a PC fails with Fear, you can **mark a Stress** to cause all other PCs within Close range to lose a Hope.

**_Momentum - Reaction:_** When the Demon makes a successful attack against a PC, you gain a Fear.

---

### Demon of Hubris

**_Tier 3 Leader._** _A perfectly beautiful and infinitely cruel demon with a gleaming spear and elegant robes._

- **Motives & Tactics:** Condescend, declare premature victory, prove superiority
- **Difficulty:** 18 | **Thresholds:** 18/36 | **HP:** 7 | **Stress:** 5
- **ATK:** +4 | **Perfect Spear:** Very Close | 3d10 phy
- **Experience:** Manipulation +2

#### Features

**_Terrifying - Passive:_** When the Demon makes a successful attack, all PCs within Far range must lose a Hope and you gain a Fear.

**_Double or Nothing - Passive:_** When a PC within Far range fails a roll, they can choose to reroll their Fear Die and take the new result. If they still fail, they mark 2 Stress and the Demon clears a Stress.

**_Unparalleled Skill - Action:_** **Mark a Stress** to deal the Demon's standard attack damage to a target within Close range.

**_The Root of Villainy - Action:_** **Spend a Fear** to spotlight two other Demons within Far range.

**_You Pale in Comparison - Reaction:_** When a PC fails a roll within Close range of the Demon, they must mark a Stress.

---

### Demon of Jealousy

**_Tier 3 Ranged._** _A fickle creature of spindly limbs and insatiable desires._

- **Motives & Tactics:** Join in on others' success, take what belongs to others, hold grudges
- **Difficulty:** 17 | **Thresholds:** 17/30 | **HP:** 6 | **Stress:** 6
- **ATK:** +4 | **Psychic Assault:** Far | 3d8+3 mag
- **Experience:** Manipulation +3

#### Features

**_Unprotected Mind - Passive:_** The Demon's standard attack deals direct damage.

**_My Turn - Reaction:_** When the Demon marks HP from an attack, **spend a number of Fear equal to the HP marked by the Demon** to cause the attacker to mark the same number of HP.

**_Rivalry - Reaction:_** When a creature within Close range takes damage from a different adversary, you can **mark a Stress** to add a **d4** to the damage roll.

**_What's Yours Is Mine - Reaction:_** When a PC takes Severe damage within Very Close range of the Demon, you can **spend a Fear** to cause the target to make a Finesse Reaction Roll. On a failure, the Demon seizes one item or consumable of their choice from the target's inventory.

---

### Demon of Wrath

**_Tier 3 Bruiser._** _A hulking demon with boulder-sized fists, driven by endless rage._

- **Motives & Tactics:** Fuel anger, impress rivals, wreak havoc
- **Difficulty:** 17 | **Thresholds:** 22/40 | **HP:** 7 | **Stress:** 5
- **ATK:** +3 | **Fists:** Very Close | 3d8+1 mag
- **Experience:** Intimidation +2

#### Features

**_Anger Unrelenting - Passive:_** The Demon's attacks deal direct damage.

**_Battle Lust - Action:_** **Spend a Fear** to boil the blood of all PCs within Far range. They use a d20 as their Fear Die until the end of the scene.

**_Retaliation - Reaction:_** When the Demon takes damage from an attack within Close range, you can **mark a Stress** to make a standard attack against the attacker.

**_Blood and Souls - Reaction: Countdown (Loop 6):_** Activate the first time an attack is made within sight of the Demon. It ticks down when a PC takes a violent action. When it triggers, summon **1d4** Minor Demons, who appear at Close range.

---

### Dire Bat

**_Tier 3 Skulk._** _A wide-winged pet endlessly loyal to their vampire owner._

- **Motives & Tactics:** Dive-bomb, hide, protect leader
- **Difficulty:** 14 | **Thresholds:** 16/30 | **HP:** 5 | **Stress:** 3
- **ATK:** +2 | **Claws and Teeth:** Melee | 2d6+7 phy
- **Experience:** Bloodthirsty +3

#### Features

**_Flying - Passive:_** While flying, the Bat gains a +3 bonus to their Difficulty.

**_Screech - Action:_** **Mark a Stress** to send a high-pitch screech out toward all targets in front of the Bat within Far range. Those targets must mark **1d4** Stress.

**_Guardian - Reaction:_** When an allied Vampire marks HP, you can **mark a Stress** to fly into Melee range of the attacker and make an attack with advantage against them. On a success, deal **2d6+2** physical damage.

---

### Dryad

**_Tier 3 Leader._** _A nature spirit in the form of a humanoid tree._

- **Motives & Tactics:** Command, cultivate, drive out, preserve the forest
- **Difficulty:** 16 | **Thresholds:** 24/38 | **HP:** 8 | **Stress:** 5
- **ATK:** +4 | **Deadfall Shortbow:** Far | 3d10+1 phy
- **Experience:** Forest Knowledge +4

#### Features

**_Bramble Patch - Action:_** **Mark a Stress** to target a point within Far range. Create a patch of thorns that covers an area within Close range of that point. All targets within that area take **2d6+2** physical damage when they act. A target must succeed on a Finesse Roll or deal more than 20 damage to the Dryad with an attack to leave the area.

**_Grow Saplings - Action:_** **Spend a Fear** to grow three Treant Sapling Minions, who appear at Close range and immediately take the spotlight.

**_We Are All One - Reaction:_** When an ally dies within Close range, you can **spend a Fear** to clear 2 HP and 2 Stress as the fallen ally's life force is returned to the forest.

---

### Elemental Spark

**_Tier 3 Minion._** _A blazing mote of elemental fire._

- **Motives & Tactics:** Blast, consume, gain mass
- **Difficulty:** 15 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +0 | **Bursts of Fire:** Close | 5 mag

#### Features

**_Minion (9) - Passive:_** The Elemental is defeated when they take any damage. For every 9 damage a PC deals to the Elemental, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Elemental Sparks within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 5 physical damage each. Combine this damage.

---

### Greater Earth Elemental

**_Tier 3 Bruiser._** _A living landslide of boulders and dust, as large as a house._

- **Motives & Tactics:** Avalanche, knock over, pummel
- **Difficulty:** 17 | **Thresholds:** 22/40 | **HP:** 10 | **Stress:** 4
- **ATK:** +7 | **Boulder Fist:** Very Close | 3d10+1 phy

#### Features

**_Slow - Passive:_** When you spotlight the Elemental and they don't have a token on their stat block, they can't act yet. Place a token on their stat block and describe what they're preparing to do. When you spotlight the Elemental and they have a token on their stat block, clear the token and they can act.

**_Crushing Blows - Passive:_** When the Elemental makes a successful attack, the target must mark an Armor Slot without receiving its benefits (they can still use armor to reduce the damage). If they can't mark an Armor Slot, they must mark an additional HP.

**_Immovable Object - Passive:_** An attack that would move the Elemental moves them two fewer ranges (for example, Far becomes Very Close). When the Elemental takes physical damage, reduce it by 7.

**_Rockslide - Action:_** **Mark a Stress** to create a rockslide that buries the land in front of Elemental within Close range with rockfall. All targets in this area must make an Agility Reaction Roll (19). Targets who fail take **2d12+5** physical damage and become _Vulnerable_ until their next roll with Hope. Targets who succeed take half damage.

**_Momentum - Reaction:_** When the Elemental makes a successful attack against a PC, you gain a Fear.

---

### Greater Water Elemental

**_Tier 3 Support._** _A huge living wave that crashes down upon enemies._

- **Motives & Tactics:** Deluge, disperse, drown
- **Difficulty:** 17 | **Thresholds:** 17/34 | **HP:** 5 | **Stress:** 5
- **ATK:** +3 | **Crashing Wave:** Very Close | 3d4+1 mag

#### Features

**_Water Jet - Action:_** **Mark a Stress** to attack a target within Very Close range. On a success, deal **2d4+7** physical damage and the target's next action has disadvantage. On a failure, the target must mark a Stress.

**_Drowning Embrace - Action:_** **Spend a Fear** to make an attack against all targets within Very Close range. Targets the Elemental succeeds against become _Restrained_ and _Vulnerable_ as they begin drowning. A target can break free, ending both conditions, with a successful Strength or Instinct Roll.

**_High Tide - Reaction:_** When the Elemental makes a successful standard attack, you can **mark a Stress** to knock the target back to Close range.

---

### Head Vampire

**_Tier 3 Leader._** _A captivating undead dressed in aristocratic finery._

- **Motives & Tactics:** Create thralls, charm, command, fly, intimidate
- **Difficulty:** 17 | **Thresholds:** 22/42 | **HP:** 6 | **Stress:** 6
- **ATK:** +5 | **Rapier:** Melee | 2d20+4 phy
- **Experience:** Aristocrat +3

#### Features

**_Terrifying - Passive:_** When the Vampire makes a successful attack, all PCs within Far range lose a Hope and you gain a Fear.

**_Look into My Eyes - Passive:_** A creature who moves into Melee range of the Vampire must make an Instinct Reaction Roll. On a failure, you gain **1d4** Fear.

**_Feed on Followers - Action:_** When the Vampire is within Melee range of an ally, they can cause the ally to mark a HP. The Vampire then clears a HP.

**_The Hunt Is On - Action:_** **Spend 2 Fear** to summon **1d4** Vampires, who appear at Far range and immediately take the spotlight.

**_Lifesuck - Reaction:_** When the Vampire is spotlighted, roll a **d8**. On a result of 6 or higher, all targets within Very Close range must mark a HP.

---

### Huge Green Ooze

**_Tier 3 Skulk._** _A translucent green mound of acid taller than most humans._

- **Motives & Tactics:** Camouflage, creep up, envelop, multiply
- **Difficulty:** 15 | **Thresholds:** 15/30 | **HP:** 7 | **Stress:** 4
- **ATK:** +3 | **Ooze Appendage:** Melee | 3d8+1 mag
- **Experience:** Blend In +3

#### Features

**_Slow - Passive:_** When you spotlight the Ooze and they don't have a token on their stat block, they can't act yet. Place a token on their stat block and describe what they're preparing to do. When you spotlight the Ooze and they have a token on their stat block, clear the token and they can act.

**_Acidic Form - Passive:_** When the Ooze makes a successful attack, the target must mark an Armor Slot without receiving its benefits (they can still use armor to reduce the damage). If they can't mark an Armor Slot, they must mark an additional HP.

**_Envelop - Action:_** Make an attack against a target within Melee range. On a success, the Ooze _Envelops_ them and the target must mark 2 Stress. While _Enveloped_, the target must mark an additional Stress every time they make an action roll. When the Ooze takes Severe damage, all _Enveloped_ targets are freed and the condition is cleared.

**_Split - Reaction:_** When the Ooze has 4 or more HP marked, you can **spend a Fear** to split them into two Green Oozes (with no marked HP or Stress). Immediately spotlight both of them.

---

### Hydra

**_Tier 3 Solo._** _A quadrupedal scaled beast with multiple long-necked heads, each filled with menacing fangs._

- **Motives & Tactics:** Devour, regenerate, terrify
- **Difficulty:** 18 | **Thresholds:** 19/35 | **HP:** 10 | **Stress:** 5
- **ATK:** +3 | **Bite:** Close | 2d12+2 phy

#### Features

**_Many-Headed Menace - Passive:_** The Hydra begins with three heads and can have up to five. When the Hydra takes Major or greater damage, they lose a head.

**_Relentless (X) - Passive:_** The Hydra can be spotlighted X times per GM turn, where X is the Hydra's number of heads. Spend Fear as usual to spotlight them.

**_Regeneration - Action:_** If the Hydra has any marked HP, **spend a Fear** to clear a HP and grow two heads.

**_Terrifying Chorus - Action:_** All PCs within Far range lose 2 Hope.

**_Magical Weakness - Reaction:_** When the Hydra takes magic damage, they become _Dazed_ until the next roll with Fear. While _Dazed_, they can't use their Regeneration action but are immune to magic damage.

---

### Monarch

**_Tier 3 Social._** _The sovereign ruler of a nation, wreathed in the privilege of tradition and wielding unmatched power in their domain._

- **Motives & Tactics:** Control vassals, destroy rivals, forge a legacy
- **Difficulty:** 16 | **Thresholds:** 16/32 | **HP:** 6 | **Stress:** 5
- **ATK:** +0 | **Warhammer:** Melee | 3d6+3 phy
- **Experience:** History +3, Nobility +3

#### Features

**_Execute Them! - Action:_** **Spend a Fear** per PC in the party to have the group condemned for crimes real or imagined. A PC who succeeds on a Presence Roll can demand trial by combat or another special form of trial.

**_Crownsguard - Action:_** Once per scene, **mark a Stress** to summon six Tier 3 Minions, who appear at Close range to enforce the Monarch's will.

**_Casus Belli - Reaction: Long-Term Countdown (8):_** **Spend a Fear** to activate after the Monarch's desire for war is first revealed. When it triggers, the Monarch has a reason to rally the nation to war and the support to act on that reason. You gain **1d4** Fear.

---

### Oak Treant

**_Tier 3 Bruiser._** _A sturdy animate old-growth tree._

- **Motives & Tactics:** Hide in plain sight, preserve the forest, root down, swing branches
- **Difficulty:** 17 | **Thresholds:** 22/40 | **HP:** 7 | **Stress:** 4
- **ATK:** +2 | **Branch:** Very Close | 3d8+2 phy
- **Experience:** Forest Knowledge +3

#### Features

**_Just a Tree - Passive:_** Before they make their first attack in a fight or after they become _Hidden_, the Treant is indistinguishable from other trees until they next act or a PC succeeds on an Instinct Roll to identify them.

**_Seed Barrage - Action:_** **Mark a Stress** and make an attack against up to three targets within Close range, pummeling them with giant acorns. Targets the Treant succeeds against take **2d10+5** physical damage.

**_Take Root - Action:_** **Mark a Stress** to _Root_ the Treant in place. The Treant is _Restrained_ while _Rooted_, and can end this effect instead of moving while they are spotlighted. While Rooted, the Treant has resistance to physical damage.

---

### Stag Knight

**_Tier 3 Standard._** _A knight with huge, majestic antlers wearing armor made of dangerous thorns._

- **Motives & Tactics:** Isolate, maneuver, protect the forest, weed the unwelcome
- **Difficulty:** 17 | **Thresholds:** 19/36 | **HP:** 7 | **Stress:** 5
- **ATK:** +3 | **Bramble Sword:** Melee | 3d8+3 phy
- **Experience:** Forest Knowledge +3

#### Features

**_From Above - Passive:_** When the Knight succeeds on a standard attack from above a target, they deal **3d12+3** physical damage instead of their standard damage.

**_Blade of the Forest - Action:_** **Spend a Fear** to make an attack against all targets within Very Close range. Targets the Knight succeeds against take physical damage equal to **3d4** + the target's Major threshold.

**_Thorny Armor - Reaction:_** When the Knight takes damage from an attack within Melee range, you can **mark a Stress** to deal **1d10+5** physical damage to the attacker.

---

### Treant Sapling

**_Tier 3 Minion._** _A small, sentient tree sapling._

- **Motives & Tactics:** Blend in, preserve the forest, pummel, surround
- **Difficulty:** 14 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +0 | **Branches:** Melee | 8 phy

#### Features

**_Minion (6) - Passive:_** The Sapling is defeated when they take any damage. For every 6 damage a PC deals to the Sapling, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Treant Saplings within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 8 physical damage each. Combine this damage.

---

### Vampire

**_Tier 3 Standard._** _An intelligent undead with blood-stained lips and a predator's smile._

- **Motives & Tactics:** Bite, charm, deceive, feed, intimidate
- **Difficulty:** 16 | **Thresholds:** 18/35 | **HP:** 5 | **Stress:** 4
- **ATK:** +3 | **Rapier:** Melee | 3d8 phy
- **Experience:** Nocturnal Hunter +3

#### Features

**_Draining Bite - Action:_** Make an attack against a target within Melee range. On a success, deal **5d4** physical damage. A target who marks HP from this attack loses a Hope and must mark a Stress. The Vampire then clears a HP.

**_Mistform - Reaction:_** When the Vampire takes physical damage, you can **spend a Fear** to take half damage.

---

### Vault Guardian Gaoler

**_Tier 3 Support._** _A boxy, dust-covered construct with thick metallic swinging doors on their torso._

- **Motives & Tactics:** Carry away, entrap, protect, pummel
- **Difficulty:** 16 | **Thresholds:** 19/33 | **HP:** 5 | **Stress:** 3
- **ATK:** +2 | **Body Bash:** Very Close | 3d6+2 phy

#### Features

**_Blocking Shield - Passive:_** Creatures within Melee range of the Gaoler have disadvantage on attack rolls against them. Creatures trapped inside the Gaoler are immune to this feature.

**_Lock Up - Action:_** **Mark a Stress** to make an attack against a target within Very Close range. On a success, the target is _Restrained_ within the Gaoler until freed with a successful Strength Roll (18). While _Restrained_, the target can only attack the Gaoler.

---

### Vault Guardian Sentinel

**_Tier 3 Bruiser._** _A dust-covered golden construct with boxy limbs and a huge mace for a hand._

- **Motives & Tactics:** Destroy at any cost, expunge, protect
- **Difficulty:** 17 | **Thresholds:** 21/40 | **HP:** 6 | **Stress:** 3
- **ATK:** +3 | **Charged Mace:** Very Close | 2d12+1 phy

#### Features

**_Kinetic Slam - Passive:_** Targets who take damage from the Sentinel's standard attack are knocked back to Very Close range.

**_Box In - Action:_** **Mark a Stress** to choose a target within Very Close range to focus on. That target has disadvantage on attack rolls when they're within Very Close range of the Sentinel. The Sentinel can only focus on one target at a time.

**_Mana Bolt - Action:_** **Spend a Fear** to lob explosive magic at a point within Far range. All targets within Very Close range of that point must make an Agility Reaction Roll. Targets who fail take **2d8+20** magic damage and are knocked back to Close range. Targets who succeed take half damage and aren't knocked back.

**_Momentum - Reaction:_** When the Sentinel makes a successful attack against a PC, you gain a Fear.

---

### Vault Guardian Turret

**_Tier 3 Ranged._** _A massive living turret with reinforced armor and twelve pistondriven mechanical legs._

- **Motives & Tactics:** Concentrate fire, lock down, mark, protect
- **Difficulty:** 16 | **Thresholds:** 20/32 | **HP:** 5 | **Stress:** 4
- **ATK:** +3 | **Magitech Cannon:** Far | 3d10+3 mag

#### Features

**_Slow Firing - Passive:_** When you spotlight the Turret and they don't have a token on their stat block, they can't make a standard attack. Place a token on their stat block and describe what they're preparing to do. When you spotlight the Turret and they have a token on their stat block, clear the token and they can attack.

**_Mark Target - Action:_** **Spend a Fear** to _Mark_ a target within Far range until the Turret is destroyed or the _Marked_ target becomes _Hidden_. While the target is _Marked_, their Evasion is halved.

**_Concentrate Fire - Reaction:_** When another adversary deals damage to a target within Far range of the Turret, you can **mark a Stress** to add the Turret's standard attack damage to the damage roll.

**_Detonation - Reaction:_** When the Turret is destroyed, they explode. All targets within Close range must make an Agility Reaction Roll. Targets who fail take **3d20** physical damage. Targets who succeed take half damage.

---

### Young Ice Dragon

**_Tier 3 Solo._** _A glacier-blue dragon with four powerful limbs and frost-tinged wings._

- **Motives & Tactics:** Avalanche, defend lair, fly, freeze, defend what is mine, maul
- **Difficulty:** 18 | **Thresholds:** 21/41 | **HP:** 10 | **Stress:** 6
- **ATK:** +7 | **Bite and Claws:** Close | 4d10 phy
- **Experience:** Protect What Is Mine +3

#### Features

**_Relentless (3) - Passive:_** The Dragon can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Rend and Crush - Passive:_** If a target damaged by the Dragon doesn't mark an Armor Slot to reduce the damage, they must mark a Stress.

**_No Hope - Passive:_** When a PC rolls with Fear while within Far range of the Dragon, they lose a Hope.

**_Blizzard Breath - Action:_** **Spend 2 Fear** to release an icy whorl in front of the Dragon within Close range. All targets in this area must make an Agility Reaction Roll. Targets who fail take **4d6+5** magic damage and are _Restrained_ by ice until they break free with a successful Strength Roll. Targets who succeed must mark 2 Stress or take half damage.

**_Avalanche - Action:_** **Spend a Fear** to have the Dragon unleash a huge downfall of snow and ice, covering all other creatures within Far range. All targets within this area must succeed on an Instinct Reaction Roll or be buried in snow and rocks, becoming _Vulnerable_ until they dig themselves out from the debris. For each PC that fails the reaction roll, you gain a Fear.

**_Frozen Scales - Reaction:_** When a creature makes a successful attack against the Dragon from within Very Close range, they must mark a Stress and become _Chilled_ until their next rest or they clear a Stress. While they are _Chilled_, they have disadvantage on attack rolls.

**_Momentum - Reaction:_** When the Dragon makes a successful attack against a PC, you gain a Fear.
## Tier 4 Adversaries (Levels 8–10)

### Arch-Necromancer

**_Tier 4 Leader._** _A decaying mage adorned in dark, tattered robes._

- **Motives & Tactics:** Corrupt, decay, flee to fight another day, resurrect
- **Difficulty:** 21 | **Thresholds:** 33/66 | **HP:** 9 | **Stress:** 8
- **ATK:** +6 | **Necrotic Blast:** Far | 4d12+8 mag
- **Experience:** Forbidden Knowledge +3, Wisdom of Centuries +3

#### Features

**_Dance of Death - Action:_** **Mark a Stress** to spotlight **1d4** allies. Attacks they make while spotlighted in this way deal half damage, or full damage if you **spend a Fear**.

**_Beam of Decay - Action:_** **Mark 2 Stress** to cause all targets within Far range to make a Strength Reaction Roll. Targets who fail take **2d20+12** magic damage and you gain a Fear. Targets who succeed take half damage. A target who marks 2 or more HP must also mark **2 Stress** and becomes _Vulnerable_ until they roll with Hope.

**_Open the Gates of Death - Action:_** **Spend a Fear** to summon a Zombie Legion, which appears at Close range and immediately takes the spotlight.

**_Not Today, My Dears - Reaction:_** When the Necromancer has marked 7 or more of their HP, you can **spend a Fear** to have them teleport away to a safe location to recover. A PC who succeeds on an Instinct Roll can trace the teleportation magic to their destination.

**_Your Life Is Mine - Reaction: Countdown (Loop 2d6):_** When the Necromancer has marked 6 or more of their HP, activate the countdown. When it triggers, deal **2d10+6** direct magic damage to a target within Close range. The Necromancer then **clears a number of Stress or HP** equal to the number of HP marked by the target from this attack.

---

### Fallen Shock Troop

**_Tier 4 Minion._** _A cursed soul bound to the Fallen's will._

- **Motives & Tactics:** Crush, dominate, earn relief, punish
- **Difficulty:** 18 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +2 | **Cursed Axe:** Very Close | 12 phy

#### Features

**_Minion (12) - Passive:_** The Shock Troop is defeated when they take any damage. For every 12 damage a PC deals to the Shock Troop, defeat an additional Minion within range the attack would succeed against.

**_Aura of Doom - Passive:_** When a PC marks HP from an attack by the Shock Troop, they lose a Hope.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Fallen Shock Troops within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 12 physical damage each. Combine this damage.

---

### Fallen Sorcerer

**_Tier 4 Support._** _A powerful mage bound by the bargains they made in life._

- **Motives & Tactics:** Acquire, dishearten, dominate, torment
- **Difficulty:** 19 | **Thresholds:** 26/42 | **HP:** 6 | **Stress:** 5
- **ATK:** +4 | **Corrupted Staff:** Far | 4d6+10 mag
- **Experience:** Ancient Knowledge +2

#### Features

**_Conflagration - Action:_** **Spend a Fear** to unleash an all-consuming firestorm and make an attack against all targets within Close range. Targets the Sorcerer succeeds against take **2d10+6** direct magic damage.

**_Nightmare Tableau - Action:_** **Mark a Stress** to trap a target within Far range in a powerful illusion of their worst fears. While trapped, the target is _Restrained_ and _Vulnerable_ until they break free, ending both conditions, with a successful Instinct Roll.

**_Slippery - Reaction:_** When the Sorcerer takes damage from an attack, they can teleport up to Far range.

**_Shackles of Guilt - Reaction: Countdown (Loop 2d6):_** When the Sorcerer is in the spotlight for the first time, activate the countdown. When it triggers, all targets within Far range become _Vulnerable_ and must mark a Stress as they relive their greatest regrets. A target can break free from their regret with a successful Presence or Strength Roll. When a PC fails to break free, they lose a Hope.

---

### Fallen Warlord: Realm-Breaker

**_Tier 4 Solo._** _A Fallen God, wreathed in rage and resentment, bearing millennia of experience in breaking heroes' spirits._

- **Motives & Tactics:** Corrupt, dominate, punish, break the weak
- **Difficulty:** 20 | **Thresholds:** 36/66 | **HP:** 8 | **Stress:** 5
- **ATK:** +7 | **Barbed Whip:** Close | 4d8+7 phy
- **Experience:** Conquest +3, History +2, Intimidation +3

#### Features

**_Relentless (2) - Passive:_** The Realm-Breaker can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Firespite Plate Armor - Passive:_** When the Realm-Breaker takes damage, reduce it by **2d10**.

**_Tormenting Lash - Action:_** **Mark a Stress** to make a standard attack against all targets within Very Close range. When a target uses armor to reduce damage from this attack, they must mark 2 Armor Slots.

**_All-Consuming Rage - Reaction: Countdown (Decreasing 8):_** When the Realm-Breaker is in the spotlight for the first time, activate the countdown. When it triggers, create a torrent of incarnate rage that rends flesh from bone. All targets within Far range must make a Presence Reaction Roll. Targets who fail take **2d6+10** direct magic damage. Targets who succeed take half damage. For each HP marked from this damage, summon a Fallen Shock Troop within Very Close range of the target who marked that HP. If the countdown ever decreases its maximum value to 0, the Realm-Breaker marks their remaining HP and all targets within Far range must mark all remaining HP and make a death move.

**_Doombringer - Reaction:_** When a target marks HP from an attack by the Realm-Breaker, all PCs within Far range of the target must lose a Hope.

**_I Have Never Known Defeat (Phase Change) - Reaction:_** When the Realm-Breaker marks their last HP, replace them with the Undefeated Champion and immediately spotlight them.

---

### Fallen Warlord: Undefeated Champion

**_Tier 4 Solo._** _That which only the most feared have a chance to fear._

- **Motives & Tactics:** Dispatch merciless death, punish the defiant, secure victory at any cost
- **Difficulty:** 18 | **Thresholds:** 35/58 | **HP:** 11 | **Stress:** 5
- **ATK:** +8 | **Heart-Shattering Sword:** Very Close | 4d12+13 phy
- **Experience:** Conquest +3, History +2, Intimidation +3

#### Features

**_Relentless (3) - Passive:_** The Undefeated Champion can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Faltering Armor - Passive:_** When the Undefeated Champion takes damage, reduce it by **1d10**.

**_Shattering Strike - Action:_** **Mark a Stress** to make a standard attack against all targets within Very Close range. PCs the Champion succeeds against lose a number of Hope equal to the HP they marked from this attack.

**_Endless Legions - Action:_** **Spend a Fear** to summon a number of Fallen Shock Troops equal to twice the number of PCs. The Shock Troops appear at Far range.

**_Circle of Defilement - Reaction: Countdown (1d8):_** When the Undefeated Champion is in the spotlight for the first time, activate the countdown. When it triggers, activate a magical circle covering an area within Far range of the Champion. A target within that area is _Vulnerable_ until they leave the circle. The circle can be removed by dealing Severe damage to the Undefeated Champion.

**_Momentum - Reaction:_** When the Undefeated Champion makes a successful attack against a PC, you gain a Fear.

**_Doombringer - Reaction:_** When a target marks HP from an attack by the Undefeated Champion, all PCs within Far range of the target lose a Hope.

---

### Hallowed Archer

**_Tier 4 Ranged._** _Spirit soldiers with sanctified bows._

- **Motives & Tactics:** Focus fire, obey, reposition, volley
- **Difficulty:** 19 | **Thresholds:** 25/45 | **HP:** 3 | **Stress:** 2
- **ATK:** +4 | **Sanctified Longbow:** Far | 4d8+8 phy

#### Features

**_Punish the Guilty - Passive:_** The Archer deals double damage to targets marked _Guilty_ by a High Seraph.

**_Divine Volley - Action:_** **Mark a Stress** to make a standard attack against up to three targets.

---

### Hallowed Soldier

**_Tier 4 Minion._** _Souls of the faithful, lifted up with divine weaponry._

- **Motives & Tactics:** Obey, outmaneuver, punish, swarm
- **Difficulty:** 18 | **Thresholds:** None | **HP:** 1 | **Stress:** 2
- **ATK:** +2 | **Sword and Shield:** Melee | 10 phy

#### Features

**_Minion (13) - Passive:_** The Soldier is defeated when they take any damage. For every 13 damage a PC deals to the Soldier, defeat an additional Minion within range the attack would succeed against.

**_Divine Flight - Passive:_** While the Soldier is flying, **spend a Fear** to move up to Far range instead of Close range before taking an action.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Hallowed Soldiers within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 10 physical damage each. Combine this damage.

---

### High Seraph

**_Tier 4 Leader._** _A divine champion, head of a hallowed host of warriors who enforce their god's will._

- **Motives & Tactics:** Enforce dogma, fly, pronounce judgment, smite
- **Difficulty:** 20 | **Thresholds:** 37/70 | **HP:** 7 | **Stress:** 5
- **ATK:** +8 | **Holy Sword:** Very Close | 4d10+10 phy
- **Experience:** Divine Knowledge +3

#### Features

**_Relentless (3) - Passive:_** The Seraph can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Divine Flight - Passive:_** While the Seraph is flying, **spend a Fear** to move up to Far range instead of Close range before taking an action.

**_Judgment - Action:_** **Spend a Fear** to make a target _Guilty_ in the eyes of the Seraph's god until the Seraph is defeated. While _Guilty_, the target doesn't gain Hope on a result with Hope. When the Seraph succeeds on a standard attack against a _Guilty_ target, they deal Severe damage instead of their standard damage. The Seraph can only mark one target at a time.

**_God Rays - Action:_** **Mark a Stress** to reflect a sliver of divinity as a searing beam of light that hits up to twenty targets within Very Far range. Targets must make a Presence Reaction Roll, with disadvantage if they are marked _Guilty_. Targets who fail take **4d6+12** magic damage. Targets who succeed take half damage.

**_We Are One - Action:_** Once per scene, **spend a Fear** to spotlight all other adversaries within Far range. Attacks they make while spotlighted in this way deal half damage.

---

### Kraken

**_Tier 4 Solo._** _A legendary beast of the sea, bigger than the largest galleon, with sucker-laden tentacles and a terrifying maw._

- **Motives & Tactics:** Consume, crush, drown, grapple
- **Difficulty:** 20 | **Thresholds:** 35/70 | **HP:** 11 | **Stress:** 8
- **ATK:** +7 | **Tentacles:** Close | 4d12+10 phy
- **Experience:** Swimming +3

#### Features

**_Relentless (3) - Passive:_** The Kraken can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Many Tentacles - Passive:_** While the Kraken has 7 or fewer marked HP, they can make their standard attack against two targets within range.

**_Grapple and Drown - Action:_** Make an attack roll against a target within Close range. On a success, **mark a Stress** to grab them with a tentacle and drag them beneath the water. The target is _Restrained_ and _Vulnerable_ until they break free with a successful Strength Roll or the Kraken takes Major or greater damage. While _Restrained_ and _Vulnerable_ in this way, a target must mark a Stress when they make an action roll.

**_Boiling Blast - Action:_** **Spend a Fear** to spew a line of boiling water at any number of targets in a line up to Far range. All targets must succeed on an Agility Reaction Roll or take **4d6+9** physical damage. If a target marks an Armor Slot to reduce the damage, they must also mark a Stress.

**_Momentum - Reaction:_** When the Kraken makes a successful attack against a PC, you gain a Fear.

---

### Oracle of Doom

**_Tier 4 Solo._** _A towering immortal and incarnation of fate, cursed to only see bad outcomes._

- **Motives & Tactics:** Change environment, condemn, dishearten, toss aside
- **Difficulty:** 20 | **Thresholds:** 38/68 | **HP:** 11 | **Stress:** 10
- **ATK:** +8 | **Psychic Attack:** Far | 4d8+9 mag
- **Experience:** Boundless Knowledge +4

#### Features

**_Terrifying - Passive:_** When the Oracle makes a successful attack, all PCs within Far range lose a Hope and you gain a Fear.

**_Walls Closing In - Passive:_** When a creature rolls a failure while within Very Far range of the Oracle, they must mark a Stress.

**_Pronounce Fate - Action:_** **Spend a Fear** to present a target within Far range with a vision of their personal nightmare. The target must make a Knowledge Reaction Roll. On a failure, they lose all Hope and take **2d20+4** direct magic damage. On a success, they take half damage and lose a Hope.

**_Summon Tormentors - Action:_** Once per day, **spend 2 Fear** to summon **2d4** Tier 2 or below Minions relevant to one of the PC's personal nightmares. They appear at Close range relative to that PC.

**_Ominous Knowledge - Reaction:_** When the Oracle sees a mortal creature, they instantly know one of their personal nightmares.

**_Vengeful Fate - Reaction:_** When the Oracle marks HP from an attack within Very Close range, you can **mark a Stress** to knock the attacker back to Far range and deal **2d10+4** physical damage.

---

### Outer Realms Abomination

**_Tier 4 Bruiser._** _A chaotic mockery of life, constantly in flux._

- **Motives & Tactics:** Demolish, devour, undermine
- **Difficulty:** 19 | **Thresholds:** 35/71 | **HP:** 7 | **Stress:** 5
- **ATK:** +2d4 | **Massive Pseudopod:** Very Close | 4d6+13 mag

#### Features

**_Chaotic Form - Passive:_** When the Abomination attacks, roll **2d4** and use the result as their attack modifier.

**_Disorienting Presence - Passive:_** When a target takes damage from the Abomination, they must make an Instinct Reaction Roll. On a failure, they gain disadvantage on their next action roll and you gain a Fear.

**_Reality Quake - Action:_** **Spend a Fear** to rattle the edges of reality within Far range of the Abomination. All targets within that area must succeed on a Knowledge Reaction Roll or become _Unstuck_ from reality until the end of the scene. When an _Unstuck_ target spends Hope or marks Armor Slots, HP, or Stress, they must double the amount spent or marked.

**_Unreal Form - Reaction:_** When the Abomination takes damage, reduce it by **1d20**. If the Abomination marks 1 or fewer Hit Points from a successful attack against them, you gain a Fear.

---

### Outer Realms Corruptor

**_Tier 4 Support._** _A shifting, formless mass seemingly made of chromatic light._

- **Motives & Tactics:** Confuse, distract, overwhelm
- **Difficulty:** 19 | **Thresholds:** 27/47 | **HP:** 4 | **Stress:** 3
- **ATK:** +7 | **Corroding Pseudopod:** Very Close | 4d8+5 mag

#### Features

**_Will-Shattering Touch - Passive:_** When a PC takes damage from the Corruptor, they lose a Hope.

**_Disgorge Reality Flotsam - Action:_** **Mark a Stress** to spew partially digested portions of consumed realities at all targets within Close range. Targets must succeed on a Knowledge Reaction Roll or mark 2 Stress.

---

### Outer Realms Thrall

**_Tier 4 Minion._** _A vaguely humanoid form stripped of memory and identity._

- **Motives & Tactics:** Destroy, disgust, disorient, intimidate
- **Difficulty:** 17 | **Thresholds:** None | **HP:** 1 | **Stress:** 1
- **ATK:** +3 | **Claws and Teeth:** Very Close | 11 phy

#### Features

**_Minion (13) - Passive:_** The Thrall is defeated when they take any damage. For every 13 damage a PC deals to the Thrall, defeat an additional Minion within range the attack would succeed against.

**_Group Attack - Action:_** **Spend a Fear** to choose a target and spotlight all Outer Realm Thralls within Close range of them. Those Minions move into Melee range of the target and make one shared attack roll. On a success, they deal 11 physical damage each. Combine this damage.

---

### Perfected Zombie

**_Tier 4 Bruiser._** _A towering, muscular zombie with magically infused strength and skill._

- **Motives & Tactics:** Consume, hound, maim, terrify
- **Difficulty:** 20 | **Thresholds:** 40/70 | **HP:** 9 | **Stress:** 4
- **ATK:** +4 | **Greataxe:** Very Close | 4d12+15 phy

#### Features

**_Terrifying - Passive:_** When the Zombie makes a successful attack, all PCs within Far range lose a Hope and you gain a Fear.

**_Fearsome Presence - Passive:_** PCs can't spend Hope to use features against the Zombie.

**_Perfect Strike - Action:_** **Mark a Stress** to make a standard attack against all targets within Very Close range. Targets the Zombie succeeds against are _Vulnerable_ until their next rest.

**_Skilled Opportunist - Reaction:_** When another adversary deals damage to a target within Very Close range of the Zombie, you can **spend a Fear** to add the Zombie's standard attack damage to the damage roll.

---

### Volcanic Dragon: Ashen Tyrant

**_Tier 4 Solo._** _No enemy has ever had the insolence to wound the dragon so. As the lava settles, it's ground to ash like the dragon's past foes._

- **Motives & Tactics:** Choke, fly, intimidate, kill or be killed
- **Difficulty:** 18 | **Thresholds:** 29/55 | **HP:** 8 | **Stress:** 5
- **ATK:** +10 | **Claws and Teeth:** Close | 4d12+15 phy
- **Experience:** Hunt from Above +5

#### Features

**_Relentless (4) - Passive:_** The Ashen Tyrant can be spotlighted up to four times per GM turn. Spend Fear as usual to spotlight them.

**_Cornered - Passive:_** **Mark a Stress** instead of spending a Fear to spotlight the Ashen Tyrant.

**_Injured Wings - Passive:_** While flying, the Ashen Tyrant gains a +1 bonus to their Difficulty.

**_Ashes to Ashes - Passive:_** When a PC rolls a failure while within Close range of the Ashen Tyrant, they lose a Hope and you gain a Fear. If the PC can't lose a Hope, they must mark a HP.

**_Desperate Rampage - Action:_** **Mark a Stress** to make an attack against all targets within Close range. Targets the Ashen Tyrant succeeds against take **2d20+2** physical damage, are knocked back to Close range of where they were, and must mark a Stress.

**_Ashen Cloud - Action:_** **Spend a Fear** to smash the ground and kick up ash within Far range. While within the ash cloud, a target has disadvantage on action rolls. The ash cloud clears the next time an adversary is spotlighted.

**_Apocalyptic Thrashing - Action: Countdown (1d12):_** **Spend a Fear** to activate. It ticks down when a PC rolls with Fear. When it triggers, the Ashen Tyrant thrashes about, causing environmental damage (such as an earthquake, avalanche, or collapsing walls). All targets within Far range must make a Strength Reaction Roll. Targets who fail take **2d10+10** physical damage and are _Restrained_ by the rubble until they break free with a successful Strength Roll. Targets who succeed take half damage. If the Ashen Tyrant is defeated while this countdown is active, trigger the countdown immediately as the destruction caused by their death throes.

---

### Volcanic Dragon: Molten Scourge

**_Tier 4 Solo._** _Enraged by their wounds, the dragon bursts into molten lava._

- **Motives & Tactics:** Douse with lava, incinerate, repel Invaders, reposition
- **Difficulty:** 20 | **Thresholds:** 30/58 | **HP:** 7 | **Stress:** 5
- **ATK:** +9 | **Lava-Coated Claws:** Close | 4d12+4 phy
- **Experience:** Hunt from Above +5

#### Features

**_Relentless (3) - Passive:_** The Molten Scourge can be spotlighted up to three times per GM turn. Spend Fear as usual to spotlight them.

**_Cracked Scales - Passive:_** When the Molten Scourge takes damage, roll a number of **d6s** equal to HP marked. For each result of 4 or higher, you gain a Fear.

**_Shattering Might - Action:_** **Mark a Stress** to make an attack against a target within Very Close range. On a success, the target takes **4d8+1** physical damage, loses a Hope, and is knocked back to Close range. The Molten Scourge clears a Stress.

**_Eruption - Action:_** **Spend a Fear** to erupt lava from beneath the Molten Scourge's scales, filling the area within Very Close range with molten lava. All targets in that area must succeed on an Agility Reaction Roll or take **4d6+6** physical damage and be knocked back to Close range. This area remains lava. When a creature other than the Molten Scourge enters that area or acts while inside of it, they must mark 6 HP.

**_Volcanic Breath - Reaction:_** When the Molten Scourge takes Major damage, roll a **d10**. On a result of 8 or higher, the Molten Scourge breathes a flow of lava in front of them within Far range. All targets in that area must make an Agility Reaction Roll. Targets who fail take **2d10+4** physical damage, mark **1d4 Stress**, and are _Vulnerable_ until they clear a Stress. Targets who succeed take half damage and must mark a Stress.

**_Lava Splash - Reaction:_** When the Molten Scourge takes Severe damage from an attack within Very Close range, molten blood gushes from the wound and deals **2d10+4** direct physical damage to the attacker.

**_Ashen Vengeance (Phase Change) - Reaction:_** When the Molten Scourge marks their last HP, replace them with the Ashen Tyrant and immediately spotlight them.

---

### Volcanic Dragon: Obsidian Predator

**_Tier 4 Solo._** _A massive winged creature with obsidian scales and impossibly sharp claws._

- **Motives & Tactics:** Defend lair, dive-bomb, fly, hunt, intimidate
- **Difficulty:** 19 | **Thresholds:** 33/65 | **HP:** 6 | **Stress:** 5
- **ATK:** +8 | **Obsidian Claws:** Close | 4d10+4 phy
- **Experience:** Hunt from Above +5

#### Features

**_Relentless (2) - Passive:_** The Obsidian Predator can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Flying - Passive:_** While flying, the Obsidian Predator gains a +3 bonus to their Difficulty.

**_Obsidian Scales - Passive:_** The Obsidian Predator is resistant to physical damage.

**_Avalanche Tail - Action:_** **Mark a Stress** to make an attack against all targets within Close range. Targets the Obsidian Predator succeeds against take **4d6+4** physical damage and are knocked back to Far range and _Vulnerable_ until their next roll with Hope.

**_Dive-Bomb - Action:_** If the Obsidian Predator is flying, **mark a Stress** to choose a point within Far range. Move to that point and make an attack against all targets within Very Close range. Targets the Obsidian Predator succeeds against take **2d10+6** physical damage and must mark a Stress and lose a Hope.

**_Erupting Rage (Phase Change) - Reaction:_** When the Obsidian Predator marks their last HP, replace them with the Molten Scourge and immediately spotlight them.

---

### Zombie Legion

**_Tier 4 Horde (3/HP)._** _A large pack of undead, still powerful despite their rotting flesh._

- **Motives & Tactics:** Consume brain, shred flesh, surround
- **Difficulty:** 17 | **Thresholds:** 25/45 | **HP:** 8 | **Stress:** 5
- **ATK:** +2 | **Undead Hands:** Close | 4d6+10 phy

#### Features

**_Horde (2d6+5) - Passive:_** When the Legion has marked half or more of their HP, their standard attack deals **2d6+5** physical damage instead.

**_Unyielding - Passive:_** The Legion has resistance to physical damage.

**_Relentless (2) - Passive:_** The Legion can be spotlighted up to two times per GM turn. Spend Fear as usual to spotlight them.

**_Overwhelm - Reaction:_** When the Legion takes Minor damage from an attack within Melee range, you can **mark a Stress** to make a standard attack with advantage against the attacker.
