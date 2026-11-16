# Changelog

All notable changes to this project are documented here. Dates use ISO 8601.
This project follows semantic versioning loosely; the version appears in the
zip filename and here, never in SKILL.md frontmatter (not a cross-agent field).

## [1.0.1] - 2026-11-14

补充**跨机器分发**能力。不改 `SKILL.md`、不改运行时行为、不改任何 API。起因很直接：另一台电脑上既没有源仓库也没有这段对话，独立分发包必须自带安装说明与自检手段。

### Added

- `INSTALL.md`（随包）：Windows PowerShell 与 macOS / Linux bash 的四根安装命令、DSH preset 手动放入、确认生效、六个触发口令与示例对话、完全手动三条边界、卸载与注意事项。
- `scripts/verify_install.py`（随包）：只读自检，逐文件比对 `MANIFEST.sha256` + 关键文件齐全 + frontmatter + LF；支持 `--target` 校验已安装副本；纯标准库、Python 3.9+、不写盘不修复。
- `tools/selftest.py` 增加 3 项断言：源 payload 自检通过、模拟解压副本自检通过、篡改文件能被检出。全套从 18 项增至 **21 项**。
- `tools/package_skill.py` 完整性门禁纳入上述两个文件（现为 16 项），防止再次出现裁剪包。

### Changed

- payload 从 14 文件增至 **16 文件**（含 `MANIFEST.sha256`）。四根镜像、`dist/standard-handoff/` 同步重建，哈希全一致。
- 维护者 README 与 payload README 补上跨机安装指引；版本号推进到 1.0.1。

## [1.0.0] - 2026-11-12

首个可用版本。基于交接类 Skill 市场全景调研（RedSkill 商店 919 条去重结果、GitHub 生态调研）与两个代表样本的深度对比，融合优点、剔除已知缺点，自行实现。

### Added

- `skills/standard-handoff/SKILL.md`：仅 `name` + `description` 两个 frontmatter 字段，约 85 行；完全手动触发白名单、八动词权限红线、三档格式表、默认 EXPORT 10 步 / RECEIVE 5 条、按需加载索引表。
- `assets/handoff.template.md`：7 个中文固定标题；4 字段 frontmatter；置信度四级、四级事实状态、失败路径与不要复活、需重新验证（带观测时间）、已知遗漏全部塞进既有 7 节，不新增顶层章节。
- `agents/openai.yaml`：`policy.allow_implicit_invocation: false`，Codex 侧硬手动门。
- 四册按需 references：`rigor.md`（溯源与脱敏）、`quality.md`（质量分与校验器边界）、`packaging.md`（zip/audit、落盘冲突、产物卫生）、`receiving.md`（回执、成功暂停、旧格式保守映射）。
- `scripts/_common.py`：纯标准库公共层，`expand_path()` / `detect_python()` 四级兜底 / `write_text_lf()` / manifest 与 CRLF 检查。
- `scripts/quick_validate.py`：frontmatter 门禁。
- `scripts/handoff_validate.py`：只读交接校验器，**删除**原方案的 13 条中文危险词宽正则，改为检查「约束与风险」是否声明齐全八动词与当前会话重新确认句式。
- `scripts/handoff_validate.py` 模板残留门禁：拦截未填写的模板原文，修掉「空模板也能 PASS」的漏洞。
- `evals/fixtures/`：`ok.md` / `placeholder.md` / `dangerous.md` / `chinese-false-positive.md`，最后一个专用于回归中文误报。
- `tools/`：一源多装同步、打包与反解压自验、全套自检。
- 随包文档：`README.md` / `LICENSE`（MIT）/ `NOTICE.md`（独立实现与来源声明）/ `MANIFEST.sha256`。

### Design decisions

- **分层按需**（主文件短，细节进 4 册 references），替代「全量内置」与「一律极简」两个极端。
- **完全手动**：description 明写 + 正文复述 + Codex `openai.yaml` 硬门 + 同步脚本默认 `--check`，四道门；不依赖任何平台 hook，不改 `settings.json`。
- **落盘冲突**：权威产物写工作区根 `./HANDOFF.md`（可 diff / 可提交 / 可跨机器），系统临时目录降级为 staging；同名另存带时间戳文件，不静默覆盖。
- **产物卫生**：成功的导出只留 1 个最终文件。
- **诚实边界**：校验器只验结构与安全门，docstring 明写不验事实真伪、置信度升级、语义连续性、来源授权、签名与跨模型无损；降级时禁止伪造校验。
- **跨平台**：纯标准库、Python 3.9+、全 LF、禁用 `fcntl` / `os.getuid()` / `pwd` / `grp` / `termios`、路径全部 `expand_path()`。

### Known limitations

- macOS 与 DSH 桌面端的运行时行为未在本机实测，六项待回填见 `README.md`。
- WorkBuddy 侧「完全手动」是软约束；硬门需用户仅在本机、不随包地配置 `skillOverrides`。
- `PASS` 不代表交接内容为真，也不代表下一步已获授权。

### MANIFEST baseline

`skills/standard-handoff/MANIFEST.sha256` 覆盖 payload 全部文件（自身除外），按相对路径排序、LF 存储。payload 内容变更后必须重建，再同步四个 agent 根。
