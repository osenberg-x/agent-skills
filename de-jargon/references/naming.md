# 命名、日志、文案层

词表主要管句子。但黑话在**标识符**里代价更高：它会进 API、进日志、进 `grep` 结果、进别人的调用栈。文档里的黑话读者能跳过，标识符里的黑话会跟着代码活十年。

## 一、标识符

### 判断顺序

1. 这个词是不是**领域里真实存在的概念**？（`bloom filter` 的 bit slot 是真概念）
2. 它在这段代码里，指的是那个概念吗？
3. 换成一个描述**它做什么**的名字，读代码的人是不是更快理解？

三问里有一问答不上，就改名。

### 高频问题标识符

| 现有 | 问题 | 改法 |
|---|---|---|
| `slot` / `slot_count` / `m_slot` | slot 在多数场景只是"第几个位置"，不是领域概念。**例外：signals/slots 模式（Qt、boost::signals2）里的 slot 是真术语，保留** | `index`、`entry`、`connection`、`position`、`free_index` |
| `gate` / `gate_check` / `gating` | 除非真是硬件门或逻辑门 | `requires_auth`、`check_permission()`、`is_enabled()` |
| `thaw()` / `thawed` | thaw 只是"从暂停恢复"的一种说法 | `resume()`、`unfreeze()`、`restore()` |
| `converge()` / `converged` | 除非真在做数值收敛 | `settle()`、`finalize()`、`merge()` |
| `watermark` | 除流处理外，通常指"已处理到的位置" | `processed_offset`、`used_bytes`、`high_water_mark`（有专名时用专名） |
| `skeleton` | 除 UI 骨架屏外 | `stub`、`template`、`outline` |
| `closure` | 闭包是真术语；业务流程里的 closure 不是 | `complete`、`end_to_end` |
| `align_*` / `sync_align` | 语义模糊 | `make_consistent_with_*`、`copy_from_*` |
| `is_landed` / `landed` | 没有"落地"这个状态 | `is_implemented`、`is_deployed`、`is_verified` |
| `capability_bit` / `cap_bit` | 位号本身不说明含义，读代码要回查定义 | `supports_export`、`can_export()`、`kCapExport` |
| `contract`（作变量名） | 契约测试之外，通常只是 schema | `schema`、`field_def`、`wire_format` |
| `budget`（非 SRE 语境） | 读者不知道是超时还是重试次数 | `timeout_ms`、`max_retries`、`memory_limit_mb` |

### 抽象通胀

AI 生成代码还有个相关毛病：**用泛词兜住没想清楚的东西**。这和黑话同源 —— 都是"名字看着对，但指不出实体"。

- `data`、`info`、`obj`、`item` → 说清是什么：`record`、`event`、`header`、`entry`
- `handle`、`process`、`do_*`、`deal_with` → 说清做什么：`close_connection()`、`recalc_checksum()`
- `Manager`、`Helper`、`Util`、`Service`、`Processor` → 说清管什么、帮什么
- `flag`、`status`、`state`（无前缀）→ `is_connected`、`scan_state`、`session_status`

判据：**读到名字能猜到类型或关键行为，就算合格**。`ThreatManager` 不合格，`QuarantineStore` 合格。

### 中文标识符

偶见于配置键、日志字段、JSON 字段。规则同上，但更严：中文标识符无法被英文工具链正确处理（大小写折叠、分词、排序）。
只有一种情况保留中文：**面向最终用户展示的键名**（如 `"威胁名称"` 这种 i18n 前的占位）。

## 二、日志文案

AI 写的日志有两个典型毛病：**只写动作不写对象**、**写结论不写证据**。

- ✗ `开始处理…` / `处理完成` / `流程已闭环`
- ✓ `隔离完成: path=/tmp/x.bin, size=1024, rule=EICAR`

- ✗ `发生异常，已兜底处理`
- ✓ `读 endpoint.json 失败: path=/var/run/app/endpoint.json, err=ENOENT，回退到默认端口 7001`

- ✗ `权限门禁未通过`
- ✓ `拒绝连接: 客户端签名校验失败, pid=1234, sig=<hex[:8]>`

规则：
1. 每条日志带**可定位的标识**（路径、pid、id、错误码）
2. 失败日志写**下一步做了什么**（回退/重试/中止），不写"兜底"
3. 不写情绪词和程度词：不要「异常严重」「大量」「明显」

## 三、错误信息（面向用户）

这一层 AI 味最重，因为训练语料里全是"操作失败，请稍后重试"。

- ✗ `操作失败，请稍后重试`
- ✓ `无法打开 C:\config.ini：文件被其他程序占用`

- ✗ `网络异常`
- ✓ `连接控制中心 10.1.2.3:443 超时（30 秒）`

- ✗ `数据校验未通过`
- ✓ `第 3 行的日期格式不对：应为 2026-11-06，实际是 2026/11/06`

规则：**用户读完知道发生了什么、能做什么**。做不到就说明缺上下文，先把上下文补上。

## 四、commit message 与 PR 描述

- ✗ `优化代码` / `完善功能` / `修复问题` / `更新文档`
- ✓ `fix(ipc): endpoint.json 缺失时回退到默认端口 7001`

- ✗ PR 标题：`[重构] 全面落地双进程架构，打通服务与 UI 链路`
- ✓ PR 标题：`refactor: 拆出独立服务进程，IPC 走 envelope 编解码`

- ✗ PR 描述里的 `本 PR 实现了 XX 能力闭环，沉淀了通用组件，为后续赋能`
- ✓ `本 PR 做三件事：1) 拆进程 2) 加 IPC 层 3) UI 侧改走 RPC。不做：驱动侧改造（另开 issue）`

规则：**说做了什么、影响哪里、不做什么**。不说价值、不说意义、不说后续赋能。

## 五、注释

注释只写代码说不出来的东西：**为什么这样做**、**约束是什么**、**踩过什么坑**。不要复述代码。

- ✗ `// 权限门禁校验`（下一行就是 `if (!VerifySignature())`）
- ✓ `// 驱动校验调用者签名，设备必须由服务进程打开；UI 进程签名无效`

- ✗ `// 这里做了兜底处理`
- ✓ `// Win7 无 CoTaskMemFree（combase.dll），改走 ole32!CoTaskMemFree`

判据：**删掉这条注释，后来者会不会踩坑**。不会就删。
