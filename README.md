# OmnisGM Rules — TTRPG SRD Markdown

[Live site](https://rules.omnisgm.com)

A curated collection of tabletop RPG **System Reference Documents (SRDs)** in Markdown, published as a
fast, static reader at **rules.omnisgm.com**. Part of the **OmnisGM** ecosystem. Content is available in
**English and Russian** (the Russian edition is a full, glossary-driven translation).

> **Issues & contributions are welcome — please file them in English.** This keeps the project
> accessible to the broadest audience. Russian is fine too if English is hard for you, but English is preferred.

## Sources

### D&D

- [SRD 5.2.1](https://www.dndbeyond.com/srd) — System Reference Document 5.2.1 by Wizards of the Coast LLC, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode)
- [dndsrd5.2_markdown](https://github.com/springbov/dndsrd5.2_markdown) — English SRD 5.2 in Markdown
- [dndsrd5.2_markdown (yuvalsapir)](https://github.com/yuvalsapir/dndsrd5.2_markdown) — updates to 5.2.1
- [DND.SRD.Wiki](https://github.com/oldmanumby/DND.SRD.Wiki) — SRD 5.1 in Markdown (wiki)
- [dnd-5e-srd-markdown](https://github.com/downfallx/dnd-5e-srd-markdown) — missing dragon stat blocks
- [Lazy GM Tools](https://github.com/mshea/lazy_gm_tools) / [slyflourish.com](https://slyflourish.com/) — monster data

### Tools

- [marker](https://github.com/VikParuchuri/marker) — PDF → Markdown conversion

## Roadmap

### Done / planned / considered

| Status | System | Publisher | License | SRD format |
|:---:|---|---|---|---|
| :white_check_mark: | D&D SRD 5.2.1 | Wizards of the Coast | CC BY 4.0 | [PDF](https://www.dndbeyond.com/srd) |
| :white_check_mark: | D&D SRD 5.1 | Wizards of the Coast | CC BY 4.0 | [PDF](https://www.dndbeyond.com/srd) |
| :white_check_mark: | Daggerheart SRD 1.0 | Darrington Press | [DPCGL](https://darringtonpress.com/license/) | [PDF](https://www.daggerheart.com/srd/), [Markdown](https://github.com/seansbox/daggerheart-srd) |
| :white_check_mark: | Basic Roleplaying (BRP) | Chaosium | [ORC](https://www.chaosium.com/orclicense/) | [PDF](https://www.chaosium.com/brp-system-reference-document/) |
| :calendar: | Pathfinder 2e | Paizo | [ORC](https://paizo.com/orclicense) | [Web](https://2e.aonprd.com/) |
| :calendar: | Starfinder 2e | Paizo | [ORC](https://paizo.com/orclicense) | [Web](https://2e.aonsrd.com/) |
| :calendar: | Year Zero Engine | Free League | [FTL](https://freeleaguepublishing.com/community-content/free-tabletop-licenses/) | [PDF](https://freeleaguepublishing.com/wp-content/uploads/2023/11/YZE-Standard-Reference-Document.pdf) |
| :grey_question: | Dragonbane | Free League | [3rd Party License](https://freeleaguepublishing.com/community-content/free-tabletop-licenses/) | PDF |
| :grey_question: | Fate Core / FAE | Evil Hat Productions | CC BY 3.0 | [Web](https://fate-srd.com/), [Markdown](https://github.com/amazingrando/fate-srd-content) |
| :grey_question: | Blades in the Dark | One Seven Design | CC BY 3.0 | [Web](https://bladesinthedark.com/), [Markdown](https://github.com/amazingrando/blades-in-the-dark-srd-content) |
| :grey_question: | Dungeon World | Sage LaTorra | CC BY 3.0 | [Web](https://www.dungeonworldsrd.com/), [GitHub](https://github.com/Sagelt/Dungeon-World) |
| :grey_question: | 13th Age (Archmage Engine) | Pelgrane Press | OGL 1.0a | [Web](https://www.13thagesrd.com/), [PDF](https://pelgranepress.com/media/SRD/13thAgeArchmageEngineSRD.pdf) |
| :grey_question: | MORK BORG | Free League | [3rd Party License](https://morkborg.com/license/) | [Web](https://morkborg.com/content/) |
| :grey_question: | Worlds Without Number | Sine Nomine | CC0 | PDF (DriveThruRPG) |
| :grey_question: | Cypher System | Monte Cook Games | [CSOL](https://www.montecookgames.com/cypher-system-open-license/) | [Web](https://callmepartario.github.io/og-csrd/) |

> :white_check_mark: — done · :calendar: — planned · :grey_question: — under consideration

### Licensing does not permit

| System | Publisher | Reason |
|---|---|---|
| World of Darkness (VtM, WtA, DtD…) | Paradox Interactive | No open SRD. The [Dark Pack](https://worldofdarkness.com/dark-pack) covers free fan content only |
| 2d20 (Dune, Fallout, Star Trek…) | Modiphius | An SRD exists, but [World Builders](https://modiphius.net/en-us/pages/2d20worldbuilders) is tied to DriveThruRPG; free redistribution is not permitted |

## Licenses

Each SRD is distributed under its own license. See `LICENSE.md` in the corresponding folder.

- D&D SRD 5.2 — CC BY 4.0: [LICENSE.md](src/dnd/srd-5.2/LICENSE.md) | [LICENSE-RU.md](src/dnd/srd-5.2/LICENSE-RU.md)

## Repository layout

- `src/{game}/{version}/{en,ru}/` — Markdown content (input to the import/translation pipeline)
- `web/` — the [Astro](https://astro.build) static-site reader published at rules.omnisgm.com
- `.claude/` — import & translation pipeline (skills + rules). See [CLAUDE.md](CLAUDE.md)

---

*This is an unofficial fan project. All trademarks belong to their respective owners.*
