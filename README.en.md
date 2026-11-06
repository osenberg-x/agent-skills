[中文](README.md) | **English**

# agent-skills

A collection of agent skills in the `SKILL.md` format. Works with Claude Code, WorkBuddy, and any other tool that loads Agent Skills. Each top-level directory is one skill — link or copy it into that tool's skills directory.

| Skill | What it does |
|---|---|
| [`de-jargon`](de-jargon/) | Removes machine-translated jargon from code comments, technical docs, and identifier names |

---

## de-jargon

Chinese technical writing has a set of words that look professional and carry no information:

> 门禁、解冻、收窄、切片、收口、落地、闭环、兜底、对齐、沉淀、颗粒度、打通、卡点、水位、心智、抓手、赋能、骨架、锚点、正交

Most of them are single-word translations of English metaphors — gate, thaw, narrow, slice, converge, land, closed-loop, fallback, align, consolidate, granularity, connect, blocker, watermark, mental model, handle, empower, skeleton, anchor, orthogonal.

What they share: each has a stronger everyday meaning in Chinese, so the reader has to work out that it doesn't mean what it appears to say, and the answer is rarely unique.

The damage isn't that they read badly. It's that **one word covers several different mechanisms**. 「做权限门禁校验」 could mean verifying a signature, checking an ACL, or reading a config flag. The reader cannot tell which.

### Three tests, not a gut feeling

1. **Can it point at a code entity?** Can the word be mapped to a specific function, field, state value, protocol field, or config key?
   「权限门禁」 points at nothing → jargon. 「校验客户端签名」 points at `verify_signature()` → fine.
2. **Does its opposite exist?** 「解冻」 (thaw) presupposes a `frozen` state. If the code has no such state machine, the word describes a transition that never happens.
3. **Does deleting it lose information?** If the sentence means the same thing without the word, the word was rhetoric, not information. This test catches the most cases.

### One word, several mechanisms

This is where naive replacements go wrong. Swap in a synonym and you will pick the wrong mechanism.

| Word | May mean |
|---|---|
| 兜底 (fallback) | default value / return-after-catch / failure return after retries / backup data source / placeholder in the UI |
| 门禁 (gate) | authentication / feature flag / input validation / admission policy |
| 对齐 (align) | field names match / value ranges match / behavior matches / docs and code agree |
| 闭环 (closed loop) | end-to-end runs / has a rollback path / has monitoring and alerts / every state transition is handled |

**If you can list two or more readings, the word carries no information.** Split it and write what you actually mean.

### Usage

The scanner uses only the Python standard library:

```bash
# whole tree
python de-jargon/scripts/scan.py .

# only level A (should be rewritten by default)
python de-jargon/scripts/scan.py . --level A

# one family
python de-jargon/scripts/scan.py . --family buzz,gate

# only what changed in this branch
git diff --name-only | python de-jargon/scripts/scan.py --paths-from -
```

The report tells apart three positions: **comments**, **string literals** (`⟨在字符串里⟩`), and **identifiers** (`⟨在代码里⟩`). A word in a comment should be rewritten; the same word in a user-facing string may be intended; in an identifier it is the most expensive to change. These cases should not be handled the same way.

```
扫描 259 个文件 · 命中 41 处   [A 级 41 · B 级 0]

  src/service/ipc/handlers.cpp  (9 处, A9 B0)
     162:6    [A][flow] // 会话收口：发射一条事件并复位聚合
              ↑ 「收口」 结束 / 完成 / 合并到主干
```

Exit code is 1 when any level-A hit is found, so it drops into pre-commit or CI directly. Pass `--no-fail` to disable.

### Handling rules

| Position | Action |
|---|---|
| Code comments | Rewrite |
| Log lines, error messages | Rewrite |
| Identifiers | Rewrite, then search for references and rebuild |
| `.md` docs | Report only — wording in design docs usually records a review decision |
| Quoted text from other people | Flag, do not change |

### What it won't do

- **No conversational rewriting.** The goal is precision, not friendliness. Turning a design doc casual is a different problem.
- **No touching real terms.** Idempotent, timeout, backoff, backpressure, watermark, resume-from-breakpoint, state machine — these have one verifiable definition and are terms, not jargon.
- **No business decisions on your behalf.** Team habits, established translations, and product names (「账号解冻」 is a feature, not jargon) get asked about first.

---

## Install

Clone anywhere, then link or copy the skills you want into your tool's skills directory:

- WorkBuddy: `~/.workbuddy/skills/`
- Claude Code: `~/.claude/skills/`

Check your tool's docs for the exact path. The examples below use WorkBuddy.

**Windows — directory junction, edits sync automatically, no admin rights needed**

```bat
git clone https://github.com/osenberg-x/agent-skills.git %USERPROFILE%\agent-skills
mklink /J "%USERPROFILE%\.workbuddy\skills\de-jargon" "%USERPROFILE%\agent-skills\de-jargon"
```

**macOS / Linux**

```bash
git clone https://github.com/osenberg-x/agent-skills.git ~/agent-skills
ln -s ~/agent-skills/de-jargon ~/.workbuddy/skills/de-jargon
```

**Copy only, no update tracking**

```bash
cp -r agent-skills/de-jargon ~/.workbuddy/skills/
```

Reopen your session after installing; skills are loaded at startup.

## Adding a skill

Create a directory at the repo root with a `SKILL.md` containing YAML frontmatter (`name` and `description` are required). Add `references/` and `scripts/` as needed, then add a row to the table above.

```
<skill-name>/
├── SKILL.md          # required: frontmatter + main workflow
├── references/       # loaded on demand, keeps the main file small
└── scripts/          # deterministic code, run not read
```

## License

MIT
