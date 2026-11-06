# agent-skills

通用的 agent skills 合集，遵循 `SKILL.md` 规范 —— Claude Code、WorkBuddy，以及任何支持 Agent Skills 的工具都能直接加载。每个目录是一个独立 skill，复制或链接到对应工具的 skills 目录即可。

| Skill | 作用 |
|---|---|
| [`de-jargon`](de-jargon/) | 清除代码注释、技术文档与标识符里的 AI 式工程黑话 |

---

## de-jargon

中文技术写作里有一批词，看着专业，实际不携带信息：

> 门禁、解冻、收窄、切片、收口、落地、闭环、兜底、对齐、沉淀、颗粒度、打通、卡点、水位、心智、抓手、赋能、骨架、锚点、正交、咬合

它们大多是英文隐喻被逐字直译的残留（gate / thaw / narrow / slice / converge / land / closed-loop / fallback）。共同特征是：**在中文里另有一个更强的本义**，读者每次遇到都要先做一次"这不是字面意思"的换算，而换算结果往往不唯一。

危害不在难看，在**一个词盖住了好几种不同机制**。看到「启动时做权限门禁校验」，读者不知道是校签名、查 ACL、还是读配置开关。

### 判定靠三条测试，不靠感觉

1. **能否指向一个代码实体** —— 能不能对应到具体的函数、字段、状态值、协议字段？
   「权限门禁」指不出 → 黑话。「校验客户端签名」指向 `verify_signature()` → 合格。
2. **反义词是否存在** —— 「解冻」预设了 `冻结` 状态。代码里没有这个状态机，词就是空的。
3. **删掉是否损失信息** —— 删掉后技术信息不减，说明它是修辞不是信息。这条命中率最高。

### 一个词能指五种东西，所以必须先拆再改

这是最容易出错的地方。直接换同义词一定换错。

| 词 | 可能是 |
|---|---|
| 兜底 | 默认值 / 异常捕获后降级返回 / 重试耗尽后失败返回 / 备用数据源 / UI 保底显示 |
| 门禁 | 身份鉴权 / 功能开关 / 前置参数校验 / 准入策略 |
| 对齐 | 字段名相同 / 取值域相同 / 行为一致 / 文档与代码同步 |
| 闭环 | 端到端能跑通 / 有回滚路径 / 有监控告警 / 状态机转移全覆盖 |

**你能拆出两种以上含义，就说明这个词本身没有信息量。**

### 用法

扫描器只依赖 Python 标准库，无需安装依赖：

```bash
# 全库扫描
python de-jargon/scripts/scan.py .

# 只看 A 级（默认改）
python de-jargon/scripts/scan.py . --level A

# 只看某一族
python de-jargon/scripts/scan.py . --family buzz,gate

# 只查本次改动
git diff --name-only | python de-jargon/scripts/scan.py --paths-from -
```

报告会区分三种位置：**注释**、**字符串字面量**（`⟨在字符串里⟩`）、**标识符**（`⟨在代码里⟩`）。同一句话该改，同一个词出现在字符串里可能只是文案，出现在标识符里改动成本最高 —— 这三种情况不能混为一谈。

```
扫描 259 个文件 · 命中 41 处   [A 级 41 · B 级 0]

  src/service/ipc/handlers.cpp  (9 处, A9 B0)
     162:6    [A][flow] // 会话收口：发射一条事件并复位聚合
              ↑ 「收口」 结束 / 完成 / 合并到主干
```

退出码：有 A 级命中返回 1，可直接接 pre-commit 或 CI。`--no-fail` 关闭。

### 处理规则

| 位置 | 怎么处理 |
|---|---|
| 代码注释 | 直接改 |
| 日志、错误提示 | 直接改 |
| 标识符 | 直接改，改完全局搜索引用并重新构建验证 |
| `.md` 文档 | 只出报告等确认 —— 文档措辞往往承载过审阅决策 |
| 引用他人原话 | 只标注，不改 |

### 不做什么

- **不做口语化润色。** 目标是更精确，不是更亲切。把技术文档改写随意是另一个问题。
- **不动真术语。** 幂等、超时、退避、背压、水位线、断点续传、状态机 —— 有唯一可验证定义的是术语，不是黑话。
- **不替你做业务决定。** 团队口头习惯、行业既有译名、业务专有名词（比如「账号解冻」是功能名不是黑话），遇到会先问。

---

## 安装

克隆到任意位置，再把需要的 skill 链接或复制进你所使用工具的 skills 目录。常见位置：

- WorkBuddy：`~/.workbuddy/skills/`
- Claude Code：`~/.claude/skills/`

以各工具文档为准。下面的示例以 WorkBuddy 为例。

**Windows（目录联接，改动自动同步，无需管理员权限）**

```bat
git clone https://github.com/osenberg-x/agent-skills.git %USERPROFILE%\agent-skills
mklink /J "%USERPROFILE%\.workbuddy\skills\de-jargon" "%USERPROFILE%\agent-skills\de-jargon"
```

**macOS / Linux**

```bash
git clone https://github.com/osenberg-x/agent-skills.git ~/agent-skills
ln -s ~/agent-skills/de-jargon ~/.workbuddy/skills/de-jargon
```

**只想要副本（不跟踪更新）**

```bash
cp -r agent-skills/de-jargon ~/.workbuddy/skills/
```

装好后需要**重新打开会话**，skill 才会出现在列表里。

## 加新 skill

在本仓库根目录新建一个文件夹，放 `SKILL.md`（含 YAML frontmatter 的 `name` 和 `description`），需要的话再加 `references/` 和 `scripts/`。然后在上面表格里加一行。

单 skill 的可选资源结构：

```
<skill-name>/
├── SKILL.md          # 必需：frontmatter + 主流程
├── references/       # 按需加载的详细资料，不占常驻上下文
└── scripts/          # 可执行的确定性代码
```

## License

MIT
