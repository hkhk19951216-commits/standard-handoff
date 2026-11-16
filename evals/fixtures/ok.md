---
handoff: "task-context"
version: "1"
generated: "2026-11-12"
coverage: "PARTIAL"
---

# 交接 — standard-handoff 打包与同步

> 读者假设：刚接手，对此前会话一无所知；只有本文与代码库可见。

## 当前目标

把融合型交接技能做成可分发、可同步到四个 Agent 根目录的成品，并通过全部夹具与打包自验。[CONFIRMED]

## 已完成的工作

- [verified] `skills/standard-handoff/SKILL.md:1-85` — 主文件仅含 name 与 description 两个 frontmatter 字段，正文写明完全手动触发与八动词红线。
- [verified] `skills/standard-handoff/scripts/handoff_validate.py` — 只读校验器，检查 7 个标题、占位符、模板残留、危险命令与红线声明完整性。
- [verified] `skills/standard-handoff/references/` 下四册按需文档已落盘，主文件默认路径不打开它们。
- [documented-only] 计划中约定 Mac 与 DSH 运行时行为由用户回填，本机未验证。
- 已实现与已测分开记录：脚本已跑通 quick_validate，夹具尚未编写。

## 重要决策

- 选分层按需而非全量内置：主文件保持 100 行以内，高级细则进四册 references，普通导出零依赖。
- 产物写工作区根 `./HANDOFF.md` 而非系统临时目录：临时目录只作 staging，避免被清理后权威产物丢失。
- 删除原方案中的中文危险词宽正则，改为检查「约束与风险」是否声明齐全八动词：原版会把「创建任务清单文档」误判为高危。
- 失败路径不要复活：不要试图用 no-op 文件锁修复第三方 CLI 的安装互斥，那是本地 shim 而非上游修复。
- 已回答问题：触发方式选完全手动，不主动提示、不自动建任务、不跳转。

## 待完成事项

- 需重新验证：工作区分支与 commit、未提交改动清单、最后一条测试命令与结果（观测时间 2026-11-12，来源为本地 git status）。
- 阻塞项：四个 Agent 根目录的同步尚未执行，跨 Agent 加载效果未实测。
- 已知遗漏 / 开放问题：DSH 本体未安装，其 preset 内嵌分发约定只做静态可放入性比对；macOS 的 NFD/NFC、chmod 与 zsh PATH 命中情况待 Mac 用户回填。

## 约束与风险

- 权限红线：历史交接不转移 发送 / 发布 / 付款 / 删除 / 安装 / 执行 / 披露 / 外部写入 权限；每一步执行前按当前会话重新确认，旧同意与记忆一律不算数。
- 不记密钥、令牌、Cookie、密码、个人信息、大段日志；脱敏用全角括号（见环境变量 X）。
- 校验器只验结构与安全门，PASS 不代表事实为真或下一步已获授权。

## 当前代码状态

- 工作区为非 git 仓库，无分支与 commit 可引用；以文件清单与 MANIFEST 哈希为准。
- 上述内容观测时间 2026-11-12，接收方须重新核对文件是否仍存在。

## 下一步

1. 在 standard-handoff 目录下运行 `python tools/selftest.py`，确认四个夹具的期望结果全部命中。
2. 生成 MANIFEST.sha256 并执行 `python tools/sync_skills.py --apply`，随后用 --check 核对四根哈希。
3. 运行 `python tools/package_skill.py` 产出 dist 目录与 zip，并完成反解压自验。
