<!-- When editing this file, mirror the change in README.ru.md -->
# OmnisGM Rules — TTRPG SRD Markdown

**English** · [Русский](README.ru.md)

[Live site](https://rules.omnisgm.com)

A curated collection of tabletop RPG **System Reference Documents (SRDs)** in Markdown, published as a
fast, static reader at **rules.omnisgm.com**. Part of the **OmnisGM** ecosystem. **Every SRD includes a
complete Russian translation — a corpus available nowhere else.**

## The OmnisGM ecosystem

This SRD reader is one of three products under **OmnisGM** — tools for running tabletop RPGs at a
physical table:

- **[OmnisGM](https://omnisgm.com)** — the flagship app: free realtime **D&D 2024 character sheets** for
  in-person play. Each player keeps their sheet on their own phone; the Game Master sees every change live.
  Installable PWA, works offline. The rules in this repo are the ones those sheets are built around.
- **[OmnisGM Rules](https://rules.omnisgm.com)** — this project: a fast, static, bilingual (EN/RU) reader
  for open SRDs, with clean citable HTML and public Markdown sources.
- **[The Guild Herald](https://news.omnisgm.com)** — OmnisGM News: a bilingual (EN/RU) tabletop RPG news
  digest (releases, crowdfunding, rules updates, industry and events).

## Systems

| Status | System | Publisher | License | Notes |
|:---:|---|---|---|---|
| ✅ | D&D SRD 5.2.1 | Wizards of the Coast | CC BY 4.0 | [PDF](https://www.dndbeyond.com/srd) |
| ✅ | D&D SRD 5.1 | Wizards of the Coast | CC BY 4.0 | [PDF](https://www.dndbeyond.com/srd) |
| ✅ | Daggerheart SRD 1.0 | Darrington Press | [DPCGL](https://darringtonpress.com/license/) | [PDF](https://www.daggerheart.com/srd/), [Markdown](https://github.com/seansbox/daggerheart-srd) |
| ✅ | Basic Roleplaying (BRP) | Chaosium | [BRP OGL v1.0](https://www.chaosium.com/brp-system-reference-document/) | [PDF](https://www.chaosium.com/brp-system-reference-document/) |
| 📅 | Pathfinder 2e | Paizo | [ORC](https://paizo.com/orclicense) | [Web](https://2e.aonprd.com/) |
| 📅 | Starfinder 2e | Paizo | [ORC](https://paizo.com/orclicense) | [Web](https://2e.aonsrd.com/) |
| 📅 | Year Zero Engine | Free League | [FTL](https://freeleaguepublishing.com/community-content/free-tabletop-licenses/) | [PDF](https://freeleaguepublishing.com/wp-content/uploads/2023/11/YZE-Standard-Reference-Document.pdf) |
| ❓ | Dragonbane | Free League | [3rd Party License](https://freeleaguepublishing.com/community-content/free-tabletop-licenses/) | PDF |
| ❓ | Fate Core / FAE | Evil Hat Productions | CC BY 3.0 | [Web](https://fate-srd.com/), [Markdown](https://github.com/amazingrando/fate-srd-content) |
| ❓ | Blades in the Dark | One Seven Design | CC BY 3.0 | [Web](https://bladesinthedark.com/), [Markdown](https://github.com/amazingrando/blades-in-the-dark-srd-content) |
| ❓ | Dungeon World | Sage LaTorra | CC BY 3.0 | [Web](https://www.dungeonworldsrd.com/), [GitHub](https://github.com/Sagelt/Dungeon-World) |
| ❓ | 13th Age (Archmage Engine) | Pelgrane Press | OGL 1.0a | [Web](https://www.13thagesrd.com/), [PDF](https://pelgranepress.com/media/SRD/13thAgeArchmageEngineSRD.pdf) |
| ❓ | MORK BORG | Free League | [3rd Party License](https://morkborg.com/license/) | [Web](https://morkborg.com/content/) |
| ❓ | Worlds Without Number | Sine Nomine | CC0 | PDF (DriveThruRPG) |
| ❓ | Cypher System | Monte Cook Games | [CSOL](https://www.montecookgames.com/cypher-system-open-license/) | [Web](https://callmepartario.github.io/og-csrd/) |
| 🚫 | World of Darkness (VtM, WtA, DtD…) | Paradox Interactive | — | No open SRD; the [Dark Pack](https://worldofdarkness.com/dark-pack) covers free fan content only |
| 🚫 | 2d20 (Dune, Fallout, Star Trek…) | Modiphius | — | An SRD exists, but [World Builders](https://modiphius.net/en-us/pages/2d20worldbuilders) is tied to DriveThruRPG; free redistribution is not permitted |

> ✅ done · 📅 planned · ❓ under consideration · 🚫 licensing does not permit

## Licenses

Each SRD is distributed under its own license. See `LICENSE.md` in the corresponding folder.

- D&D SRD 5.2 — CC BY 4.0: [LICENSE.md](src/dnd/srd-5.2/LICENSE.md) | [LICENSE-RU.md](src/dnd/srd-5.2/LICENSE-RU.md)
- D&D SRD 5.1 — CC BY 4.0: [LICENSE.md](src/dnd/srd-5.1/LICENSE.md) | [LICENSE-RU.md](src/dnd/srd-5.1/LICENSE-RU.md)
- Daggerheart SRD 1.0 — DPCGL © Critical Role, LLC (not affiliated with or endorsed by Darrington Press); see the in-app [Legal page](src/daggerheart/srd-1.0/en/00_Legal.md)
- Basic Roleplaying SRD 1.0 — BRP OGL v1.0 © Chaosium Inc.: [LICENSE.md](src/brp/srd-1.0/LICENSE.md)

## Repository structure

- `src/{game}/{version}/{en,ru}/` — Markdown content (input to the import/translation pipeline)
- `web/` — the [Astro](https://astro.build) static-site reader published at rules.omnisgm.com
- `.claude/` — import & translation pipeline (skills + rules). See [CLAUDE.md](CLAUDE.md)

## Contributing

**Issues & contributions are welcome — please file them in English.** This keeps the project accessible
to the broadest audience. Russian is fine too if English is hard for you, but English is preferred.

## Credits & tooling

Markdown source material the import pipeline builds on:

- [dndsrd5.2_markdown](https://github.com/springbov/dndsrd5.2_markdown) — English SRD 5.2 in Markdown
- [dndsrd5.2_markdown (yuvalsapir)](https://github.com/yuvalsapir/dndsrd5.2_markdown) — updates to 5.2.1
- [DND.SRD.Wiki](https://github.com/oldmanumby/DND.SRD.Wiki) — SRD 5.1 in Markdown (wiki)
- [dnd-5e-srd-markdown](https://github.com/downfallx/dnd-5e-srd-markdown) — missing dragon stat blocks
- [Lazy GM Tools](https://github.com/mshea/lazy_gm_tools) / [slyflourish.com](https://slyflourish.com/) — monster data
- [marker](https://github.com/VikParuchuri/marker) — PDF → Markdown conversion

---

*This is an unofficial fan project. All trademarks belong to their respective owners.*
