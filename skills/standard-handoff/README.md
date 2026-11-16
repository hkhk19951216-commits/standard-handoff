# standard-handoff

一个**完全手动触发**的交接技能：用户明确说出口令时，写或读一份紧凑、诚实、跨 Agent 可继续的 `HANDOFF.md`。

平时它就是一张交班便签，不读任何附加文档；只有命中特定条件才按需翻开 `references/` 下的四册。

> **在另一台电脑上安装**：见随包的 `INSTALL.md`——包含 Windows PowerShell / macOS bash 的四根安装命令、六个触发口令、DSH 手动放入与卸载。解压后先跑 `py -3 scripts/verify_install.py` 做完整性自检。

## 什么时候用

用户明确说出「交接」「handoff」「写交接文档」「接收交接」「生成 handoff」「读交接继续」。

**不会**因为会话变长、上下文压缩、任务快结束或任何推测而主动提示、主动写文件、主动建任务或跳转。也不会改任何 agent 配置文件。

## 直接开始用（零依赖）

不需要安装脚本、不需要 Python、不需要联网：

1. 把本目录整个放到你的 agent 的 skills 目录下（路径见下表）。
2. 说「写交接文档」→ 按 `assets/handoff.template.md` 生成一份 `./HANDOFF.md`。
3. 说「接收交接」→ 得到一段聊天回执，默认不落盘。

主文件 `SKILL.md` 只有 `name` + `description` 两个 frontmatter 字段，是实测四个 agent 根目录的最小交集。

## 安装位置

| Agent | 目标路径（Windows / macOS 写法一致） |
|---|---|
| WorkBuddy | `~/.workbuddy/skills/standard-handoff` |
| Claude Code | `~/.claude/skills/standard-handoff` |
| Codex | `~/.codex/skills/standard-handoff` |
| 通用第四根 | `~/.agents/skills/standard-handoff` |
| DSH | 见下节，默认不自动写入 |

手动安装示例：

```bash
# 从源码仓库同步（仅源仓库带 tools/）
python tools/sync_skills.py --apply
python tools/sync_skills.py --check

# 独立分发包不含 tools/，直接复制整个目录；完整命令见 INSTALL.md
cp -R standard-handoff ~/.claude/skills/
```

如果用 `npx skills add <repo>` 之类的第三方安装器，安装后请用本包内的 `MANIFEST.sha256` 复验文件完整性——裁剪过的包会缺 `references/` 或 `agents/openai.yaml`，导致按需路径和 Codex 手动门失效。最快的方式是 `py -3 scripts/verify_install.py`。

### DSH（DeepSeek Harness 桌面端）

DSH 的 skill 走插件 `presets/*/skills/` 内嵌分发，不是用户级目录扫描。本包**不假设能自动安装**：把 `dist/standard-handoff/` 这个纯目录整个放进对应 preset 的 `skills/` 下即可，加载与否取决于该 preset 的注册约定，需自行验证。

### Codex 的手动门

`agents/openai.yaml` 里 `policy.allow_implicit_invocation: false` 是 Codex 侧的硬门。WorkBuddy 侧因本包**不改** `settings.json`，完全手动是软约束（靠 `description` 与正文边界）。如需本机硬门，可仅在自己机器上、不随包地给 `~/.workbuddy/settings.json` 增加 `"skillOverrides": {"standard-handoff": "user-invocable-only"}`。

## 可选校验（需要 Python 3.9+，纯标准库）

进入本技能目录后运行：

```bash
# 校验解压包本身（Windows）
py -3 scripts/verify_install.py
py -3 scripts/quick_validate.py .
py -3 scripts/handoff_validate.py /path/to/your/HANDOFF.md

# 校验已安装到某个 agent 根的副本
py -3 scripts/verify_install.py --target "~/.claude/skills/standard-handoff"

# macOS / Linux 把 py -3 换成 python3
```

`verify_install.py` 逐文件比对 `MANIFEST.sha256`，检查关键文件、frontmatter 与 LF；`quick_validate.py` 是 frontmatter 门禁；`handoff_validate.py` 是交接产物的只读校验器。三个都**只读、不修复、不写盘**。

`handoff_validate.py` 只检查结构与安全门：7 个固定标题、未填占位符、模板残留、下一步首条里的破坏性命令、疑似密钥、权限红线声明是否齐全、coverage=PARTIAL 是否有已知遗漏段。它**不检查**事实真伪、置信度有没有被正确升级、语义连续性、来源署名授权、hash 签名、当前授权状态或跨模型无损。`PASS` 只表示结构过关，**不代表下一步可以安全执行**。

脚本不可用时直接写 Markdown 即可，不要伪造 hash、扫描、签名或验证结果。

## 目录说明

```text
SKILL.md                      主文件，仅两个 frontmatter 字段
INSTALL.md                    另一台电脑上的安装与使用说明
agents/openai.yaml            Codex 硬手动门
assets/handoff.template.md    默认模板，7 个中文固定标题
references/rigor.md           置信度四级 / 四级事实状态 / 脱敏（按需）
references/quality.md         质量分 / staleness / 校验器边界（按需）
references/packaging.md       zip 与 audit 档 / 落盘冲突 / 产物卫生（按需）
references/receiving.md       回执 / 成功暂停 / 旧格式保守映射（按需）
scripts/_common.py            公共层，纯标准库
scripts/handoff_validate.py   只读交接校验器
scripts/quick_validate.py     frontmatter 门禁
scripts/verify_install.py     解压包 / 已安装副本的完整性自检
MANIFEST.sha256               逐文件哈希，可独立复验
```

## 卸载

从源码仓库运行 `python tools/sync_skills.py --uninstall`：只删除哈希与 MANIFEST 完全一致的目标目录，不动 `settings.json`、不动源目录、不动 `dist/`。独立分发包没有 `tools/`，手动删除对应目录即可，命令见 `INSTALL.md`。

## macOS 自检

本包全部使用 `~` / 相对路径、LF 换行、纯标准库，不硬编码盘符或分隔符，也不假设 `python3` 一定在 PATH。首次在 Mac 上建议核对：

```bash
python3 --version                      # 需 >= 3.9
python3 scripts/verify_install.py
python3 -m py_compile scripts/*.py
find . -type f -exec file {} + | grep -i CRLF   # 应无输出
python3 scripts/quick_validate.py .
```

**仍需 Mac 用户回填验证的六项**：四个 skills 根目录是否真实存在、DSH preset 的实际约定、zsh 下 PATH 是否命中 Python、文件名 NFD/NFC 归一化、`chmod` 与 `os.replace` 原子替换行为、以及跨机器同步后的哈希一致性。这些在 Windows 上无法实测。

## 诚实边界

- 不宣称跨模型 / 跨语言 / 跨运行时 / 无损。
- 不宣称校验通过等于事实为真或已获授权。
- 历史交接不转移「发送 / 发布 / 付款 / 删除 / 安装 / 执行 / 披露 / 外部写入」的当前权限；每一步都要在当前会话重新确认。
- 不记录密钥、令牌、Cookie、密码、个人信息、大段日志。

许可见 `LICENSE`，来源与独立性声明见 `NOTICE.md`。
