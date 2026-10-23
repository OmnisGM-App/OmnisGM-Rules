# Owner decisions: what counts as one, and how the agent treats it

Copy of the template from OmnisGM-App/claude-plugins/templates/owner-decisions.md — edit there, roll out
as copies. The owner reviews every step and validates production changes himself; the agent's job is to make
his decisions visible and to stop where a decision is his.

1. **A decision written in an issue checklist is binding.** «Passives as targets — dnd2014 only» stays so
   even when the code, the edition rules or a cleaner design argue otherwise. A mismatch "the code allows it /
   the decision forbids it" is a question to the owner, not a reason to act (Table#634: a green PR thrown away
   whole). A baseline that moved in an area the decision declared untouched is a signal to stop, not to re-shoot.
2. **A "Recommended" option the owner clicked is the agent's proposal, accepted.** In issues and PRs write
   «proposed by the agent, accepted by the owner»; «Owner's decision» only when the decision is in his own
   words. Before offering an option, check it against the SRD text and the map/plan it belongs to, and make
   sure it does not contradict itself. Collect rule and lifecycle questions into ONE list before the first PR,
   not one question per review round (Table#1024: six PRs, two "decisions" against the rules, a re-scope).
3. **Mechanics of the current edition stay in the current wave** (owner, 2026-10-21: «we do 2024 now, and
   everything about it is in the current wave»); a new stored field or a "no way back" branch beyond the
   plan is a question whether it is needed at all.
4. **Advice on a screenshot of another session's question — only after reading.** Open the issue body and
   comments, its PR, the code the recommended option relies on, and the rule in the SRD text in Rules; say in
   the answer what was checked and where the issue or code contradicts the question (owner, 2026-10-22:
   «перепроверяй в будущем»).
5. **Planning sessions write no code** (owner, 2026-07-03). A session that runs as strategy, planning or
   review produces plans, issues and reviews; code is written in a session opened for it. Do not slip into
   code without an explicit ask.
6. **Switch nothing on for users before the owner validates it.** New sources, feeds, channels and
   integrations ship disabled (`enabled: false`) and are enabled after his check. External posts (Slack,
   Telegram, e-mail) and anything that touches a server outside a push — only on an explicit command for
   that action.
7. **Increments over big bangs; general models over flags.** Split redesigns and new sources into reviewable
   steps with clean commit points; prefer a value that can grow (`local_community: "ru"`) to a boolean that
   cannot (`ru_community`).
