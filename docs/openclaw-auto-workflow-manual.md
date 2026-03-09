# OpenClaw 自动化工作系统操作手册（v1）

## 1. 目标

这套机制的目标不是“让 Agent 一直自由发挥”，而是让 OpenClaw 在**可控、可追溯、可暂停**的前提下，具备稳定的项目自动推进能力。

核心设计原则：
- 小步推进
- 定时触发
- 运行态与项目内容分离
- 所有动作可追溯
- 跑完一批自动停到 no-op，而不是无限发散

---

## 2. 适用场景

适合：
- 研究型项目
- 规划型项目
- 文档驱动项目
- 可以拆成一系列小 step 的工作

不适合直接上这套的：
- 高风险外部动作（发邮件、发布、对外同步）
- 强交互型编码工作流
- 需要频繁人工判断才能继续的复杂多分叉任务

---

## 3. 系统架构

这套系统由 4 层组成：

### Layer A：项目目录
项目实际内容所在目录。

本次验证后的推荐位置：
- `~/.openclaw/workspace/projects`

不要把自动推进项目长期放在 `~/Documents/...`，因为 macOS 下 LaunchAgent 后台访问 Documents 容易碰到权限问题。

示例：
- `~/.openclaw/workspace/projects/alpha-insight-research`
- `~/.openclaw/workspace/projects/personal-website`

### Layer B：项目控制文件
每个项目保留常规文档：
- `PROJECT.md`
- `TODO.md`
- `DECISIONS.md`
- `docs/`

总控目录中保留：
- `DASHBOARD.md`
- `AUTO_ADVANCE.md`

### Layer C：运行态目录
所有自动化执行状态放在独立 runtime 目录，不与项目内容混放。

推荐位置：
- `~/.openclaw/workspace/runtime/auto-advance/`

示例文件：
- `alpha-insight-research-state.json`
- `alpha-insight-research-trace.log`
- `alpha-insight-research-last-run.txt`

### Layer D：定时触发器
由 macOS LaunchAgent 负责周期性触发。

不再推荐 crontab 作为主方案，因为实测容易被覆盖、回退、或写入不稳定。

---

## 4. 工作机制原理

系统运行逻辑如下：

1. LaunchAgent 每隔固定时间唤醒一次脚本
2. 脚本读取该项目的 runtime state
3. 根据 `next_step_index` 决定当前该执行哪个 step
4. 执行该 step
5. 把结果写回项目目录（文档、TODO、PROJECT 等）
6. 把状态写回 runtime 目录
7. 更新 `AUTO_ADVANCE.md` / `DASHBOARD.md`
8. 等待下一次定时触发

如果该批 step 已全部完成：
- 进入 `no-op`
- 继续被定时唤醒，但只记录“当前无新动作执行”

也就是说：

### 这是“批次式自动推进”
不是完全开放式无限自推。

一批任务会预先定义 3–5 个小 step，跑完就停。

---

## 5. 为什么采用“批次式”而不是“无限自推进”

原因有 5 个：

1. **可控**：不会无限发散
2. **好审计**：每一步都知道是谁、何时、做了什么
3. **易 debug**：出错时能快速定位到具体 step
4. **降低风险**：不容易误改大量项目文件
5. **适合早期系统稳定化**：先验证调度与执行可靠性，再逐步增强智能度

推荐做法：
- 每批 3–5 步
- 每步只做一件小事
- 每批跑完再定义下一批

---

## 6. 为什么必须把运行态文件和项目内容分开

这是这套系统能稳定跑起来的关键原则之一。

### 不推荐
把以下文件放在项目目录里：
- state.json
- trace.log
- lock 文件
- 上次执行标记

### 推荐
全部放在：
- `~/.openclaw/workspace/runtime/auto-advance/`

原因：
- 运行态是“调度器资产”，不是“项目资产”
- 更方便清理和重建
- 更方便做多项目统一调度
- 能减少项目目录污染
- 权限更稳定

---

## 7. 核心文件说明

## 7.1 `AUTO_ADVANCE.md`
作用：
- 表示当前自动推进队列
- 人和 Agent 都可以看
- 记录当前 next action / checkpoint / 状态

典型内容：
```md
# Auto Advance Queue

## Ready
- project: alpha-insight-research
  level: L4
  next_action: 补充 3 个竞品的核心定位摘要
  checkpoint: docs/competitor-positioning.md 已生成
  notify: on_blocked,on_decision,on_complete
  last_update: 2026-03-08
```

它是：
- 可读的任务看板
- 不是底层真实调度状态源

真实调度状态源是 runtime 里的 state 文件。

## 7.2 `state.json`
作用：
- 记录当前推进到第几个 step
- 是脚本真正依赖的执行状态

示例：
```json
{
  "next_step_index": 2,
  "last_run": "2026-03-08 22:33:23"
}
```

## 7.3 `trace.log`
作用：
- 记录详细执行轨迹
- 用于排查问题

记录内容包括：
- 启动时间
- 当前 step
- 执行了什么动作
- 是否完成
- 下一步切换为什么

## 7.4 `progress-log.md`
作用：
- 记录项目视角的重要进展
- 给人看，不是给调度器看

它应该写“结果”，而不是写太底层的系统细节。

---

## 8. 小步任务怎么设计

一个 step 要满足以下原则：

### 好的 step 应该：
- 只做一件事
- 产出明确文件或明确状态变化
- 出错时容易定位
- 不依赖太多上下文猜测

### 好例子
- 生成 `docs/competitor-positioning.md`
- 更新 `PROJECT.md` 中的 Next Action
- 追加一条 progress log

### 坏例子
- “继续研究并完善产品规划”
- “如果觉得差不多就往下推进”
- “自己判断需要做哪些文件修改”

step 越具体，系统越稳。

---

## 9. 定时触发机制

推荐使用 LaunchAgent。

### 推荐参数
- `StartInterval = 900`（15 分钟）
- `RunAtLoad = false`（如果希望从下一轮开始）
- `RunAtLoad = true`（如果希望加载时立即跑一次）

### 示例 plist
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.example.openclaw.project-auto-advance</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/you/.openclaw/workspace/scripts/auto_advance_projects.py</string>
  </array>
  <key>StartInterval</key>
  <integer>900</integer>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>/tmp/openclaw_project_auto_advance.out</string>
  <key>StandardErrorPath</key>
  <string>/tmp/openclaw_project_auto_advance.err</string>
</dict>
</plist>
```

### 常用命令
加载：
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.openclaw.project-auto-advance.plist
```

卸载：
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.example.openclaw.project-auto-advance.plist
```

强制立即执行：
```bash
launchctl kickstart -k gui/$(id -u)/com.example.openclaw.project-auto-advance
```

查看是否已加载：
```bash
launchctl list | grep project-auto-advance
```

---

## 10. 为什么不推荐直接用 crontab

本次实测中，crontab 暴露出这些问题：
- 容易被旧模板覆盖
- 多次 patch 时容易回退
- 写入行为不够稳定
- 排查“是谁改了 crontab”比较麻烦

LaunchAgent 的优点：
- 更贴近 macOS 原生
- 更好管理用户级后台任务
- 更方便重载、查看、kickstart
- 对长期自动化任务更友好

---

## 11. 实际搭建步骤

### Step 1：准备项目目录
把项目放到：
- `~/.openclaw/workspace/projects/`

### Step 2：准备项目文档
至少有：
- `PROJECT.md`
- `TODO.md`
- `docs/`

### Step 3：建立总控文件
建立：
- `DASHBOARD.md`
- `AUTO_ADVANCE.md`

### Step 4：建立 runtime 目录
建立：
- `~/.openclaw/workspace/runtime/auto-advance/`

### Step 5：编写自动推进脚本
脚本职责：
- 读取 state
- 执行一个 step
- 写回项目文件
- 更新 queue / dashboard
- 记录 trace / progress

### Step 6：配置 LaunchAgent
- 设定 15 分钟或 1 小时周期
- 先手工 kickstart 测试
- 确认 state / trace / progress 都在更新

### Step 7：先用 3 步小批次验证
不要一上来就做无限推进。
先验证：
- 是否按时触发
- 是否能写回项目文件
- 是否能正确 no-op

### Step 8：再追加下一批 step
验证稳定后再续新一批。

---

## 12. 推荐的 step 批次模板

适合研究项目的 5 步模板：

1. 输出一个结构文档
2. 输出一个对比文档
3. 输出一个判断文档
4. 更新项目状态文件
5. 收敛下一阶段的最小范围

例如：
- step-01：列竞品候选
- step-02：写竞品定位
- step-03：写差异点
- step-04：写 MVP 范围
- step-05：更新 PROJECT/TODO 进入下一阶段

---

## 13. 推荐的日志策略

### trace.log
写技术轨迹：
- start run
- executing step
- wrote file
- completed step
- no-op

### progress-log.md
写项目结果：
- 已补充 3 个竞品定位摘要
- 已提炼差异点
- 已收敛 MVP 范围

### stderr/stdout
保留原始系统输出：
- `/tmp/openclaw_project_auto_advance.err`
- `/tmp/openclaw_project_auto_advance.out`

---

## 14. 风险与边界

### 不要让这套系统自动做：
- 对外发送
- 发布上线
- 删除大量文件
- 改系统配置
- 涉及密钥/权限的大动作

### 推荐只做：
- 研究文档生成
- 项目文档更新
- TODO / PROJECT / queue 更新
- 低风险内部整理

---

## 15. 当前验证结论

这套机制已经验证通过的关键点：
- LaunchAgent 可作为稳定触发器
- 15 分钟周期可稳定运行一整夜
- 批次式 step 推进可控
- runtime 与项目内容分离是必要设计
- 项目目录迁出 `~/Documents` 后，后台写入稳定
- 跑完一批后自动进入 no-op 是正确行为

---

## 16. 建议的 v2 演进方向

在 v1 稳定后，可以考虑升级为“半开放式自动推进”：
- 仍保留 step 批次
- 但脚本可在批次结束时，根据 `AUTO_ADVANCE.md` 或 `PROJECT.md` 自动生成下一批 1–2 步候选
- 由主会话确认后接续

这比完全无限自推进更稳，也比纯手工续批更省心。

---

## 17. 一句话总结

这套系统不是“让 Agent 自由发挥”，而是：

## 用 LaunchAgent 提供外部定时触发，用 runtime state 提供可恢复执行，用小步 step 提供可控推进，用项目文档承接结果。

如果要给别的 OpenClaw 直接复用，最重要的三条是：
1. 项目放在 `workspace/projects`，不要放 `Documents`
2. runtime 文件独立放在 `workspace/runtime/auto-advance`
3. 永远按 3–5 个 step 一批来跑


---

## 18. 最小模板包（可复制骨架）

为了让别的 OpenClaw 直接照抄搭建，本仓库补了一套最小模板：

- `docs/templates/auto-workflow-minimal/projects/example-project/`
- `docs/templates/auto-workflow-minimal/runtime/auto-advance/`
- `docs/templates/auto-workflow-minimal/scripts/auto_advance_projects.py`
- `docs/templates/auto-workflow-minimal/LaunchAgents/com.example.openclaw.project-auto-advance.plist`

### 模板包用途

它不是完整产品，而是一个“最小可运行骨架”：
- 有项目目录
- 有 runtime 目录
- 有 state / trace / last-run 文件
- 有 3 个 step 的自动推进脚本
- 有 LaunchAgent 触发器模板

### 推荐使用方式

1. 复制整套模板到你自己的 workspace
2. 改 `example-project` 为真实项目名
3. 改脚本中的 `WORKSPACE` / 路径
4. 改 `STEPS` 为你的真实小步任务
5. 加载 LaunchAgent
6. 手工 kickstart 一次验证

### 模板包的定位

这套模板的价值不在于“智能”，而在于：
- 可复制
- 可调试
- 可扩展
- 适合作为别的 OpenClaw 自动化工作的起点
