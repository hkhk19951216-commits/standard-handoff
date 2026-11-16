# standard-handoff — 维护者指南

融合型交接技能的**唯一可编辑源**。四个 agent 根目录全是只读镜像，只改这里、再同步，避免副本漂移。

公开仓库：`https://github.com/hkhk19951216-commits/standard-handoff`。

本技能基于一次交接类 Skill 市场全景调研（商店 919 条去重记录、GitHub 生态与协议层对比）后独立实现。调研原始数据与实施计划属本地资料，未随本仓库分发；设计取舍已落在 `CHANGELOG.md` 与 `skills/standard-handoff/NOTICE.md`。

## 一键安装（推荐）

需要 Node.js 22.20+。本仓库的 `skills/standard-handoff/SKILL.md` 正好符合 skills CLI 的 monorepo 约定，实测 `--list` 返回 `Found 1 skill: standard-handoff`，真实安装后 `SKILL.md` 与源字节一致、16 个文件齐全。

```bash
# 交互式：自己挑技能和 agent
npx skills add hkhk19951216-commits/standard-handoff

# 一条命令、全局、无提示（推荐：显式指定 agent，避免全量写入）
npx skills add hkhk19951216-commits/standard-handoff --skill standard-handoff --global --yes --agent claude-code codex --copy

# 只看仓库里有什么，不安装
npx skills add hkhk19951216-commits/standard-handoff --list
```

实测要点：

- **一定要写 `--agent`**：不加 `--agent` 又加 `--yes` 时，CLI 会向所有支持的 agent 目录写入（本机隔离环境实测 55 个）。只装自己用的那几个。
- `-g` / `--global` 是用户级；去掉则装到当前项目（`.claude/skills/`、`.agents/skills/` 等）。
- CLI 默认用符号链接指到一份 canonical copy；`--copy` 强制复制成独立目录，跨机器搬运与卸载更直观，本包推荐加。
- 覆盖范围：Claude Code `~/.claude/skills/`、Codex `~/.codex/skills/`、通用 `~/.agents/skills/`。**WorkBuddy 与 DSH 不在该 CLI 的支持列表**，这两处按下面的手动方式放，或在源仓库跑 `python tools/sync_skills.py --apply` 一次同步四根。
- 装完可复验：`py -3 scripts/verify_install.py --target "~/.claude/skills/standard-handoff"`，`PASS` 表示 16 个文件与 `MANIFEST.sha256` 一致。

## 手动安装（零依赖）

不想装 Node 也可以：下载 Release 的 `standard-handoff-1.0.1.zip`，解压后读包内 `INSTALL.md`（Windows PowerShell 与 macOS bash 两套命令），或把 `skills/standard-handoff/` 整个目录复制到目标 agent 的 skills 根。完全手动触发、不改任何 agent 配置。

## 单一源原则

```text
本仓库 skills/standard-handoff/   ← 唯一可编辑
        │
        ├── sync --apply ──> ~/.workbuddy/skills/standard-handoff
        │                ──> ~/.claude/skills/standard-handoff
        │                ──> ~/.codex/skills/standard-handoff
        │                ──> ~/.agents/skills/standard-handoff
        │
        └── package ──────> dist/standard-handoff/          （DSH 手动放入）
                     ──────> dist/standard-handoff-<v>.zip   （拷到别的电脑）
                     ──────> dist/standard-handoff-<v>.zip.sha256
```

**永远不要直接编辑镜像目录里的内容。** 改完源后重新生成 `MANIFEST.sha256`、同步、再用 `--check` 复验。

## 目录树

```text
standard-handoff/
├── .gitattributes                  LF 基线：* text=auto eol=lf
├── README.md                       本文件
├── CHANGELOG.md                    版本与 MANIFEST 基线
├── skills/standard-handoff/        ★ payload：同步与打包的唯一字节源（16 文件）
│   ├── SKILL.md                    ≤100 行，仅 name + description
│   ├── INSTALL.md                  另一台电脑上的安装与使用说明（随包）
│   ├── README.md LICENSE NOTICE.md MANIFEST.sha256
│   ├── agents/openai.yaml          Codex 硬手动门
│   ├── assets/handoff.template.md  默认模板（7 个中文固定标题）
│   ├── references/                 rigor / quality / packaging / receiving
│   └── scripts/                    _common / handoff_validate / quick_validate / verify_install
├── tools/                          sync_skills / package_skill / selftest（不进 payload）
├── evals/fixtures/                 ok / placeholder / dangerous / chinese-false-positive
└── dist/                          打包产物（不进 payload）
```

## 跨机器分发

`tools/`、`evals/`、`dist/` **不随包分发**。另一台电脑只拿 `dist/standard-handoff-<v>.zip` 即可，包内 `INSTALL.md` 给了 Windows / macOS 两套安装命令与口令，`scripts/verify_install.py` 可在解压后或安装后独立复验：

```bash
py -3 scripts/verify_install.py
py -3 scripts/verify_install.py --target "~/.claude/skills/standard-handoff"
```

接收方不需要源仓库，也不需要联网。改内容必须回源仓库改、重建 MANIFEST、重新打包；直接改镜像会让哈希校验失败。

## 常用命令

```bash
# 1. 开发完成后：自检（4 夹具 + 静态扫描 + LF/UTF-8 + 解释器兜底 + 安装自检）
python tools/selftest.py

# 2. payload 有内容变更后，重建 MANIFEST（自身不计入哈希）
python -c "import sys; sys.path.insert(0,'skills/standard-handoff/scripts'); \
from _common import build_manifest, write_text_lf; \
write_text_lf('skills/standard-handoff/MANIFEST.sha256', build_manifest('skills/standard-handoff'))"

# 3. 同步：先看差异（默认 --check，绝不写盘）
python tools/sync_skills.py --check
# 确认后再写
python tools/sync_skills.py --apply
python tools/sync_skills.py --check          # 应全部一致，退出码 0
# 若目标目录含 MANIFEST 之外的文件，--apply 默认拒绝并逐一列出；
# 确认那些文件可以丢弃后才加 --force 做全量替换
python tools/sync_skills.py --apply --force

# 4. 打包（含完整性门禁 + 反解压自验）
python tools/package_skill.py --version 1.0.1

# 5. 卸载预演 / 执行（只删哈希完全一致的目标）
python tools/sync_skills.py --uninstall --check
python tools/sync_skills.py --uninstall
```

`--python` / `PYTHON_BIN` 可显式指定解释器；找不到时按 `sys.executable` → `python3` → `python` → `py -3` 兜底，四级都失败则明确退出码 2，不猜路径。所有脚本 Windows / macOS 通用，纯 Python 标准库，Python 3.9+。

### DSH

本体未安装（`~/.dsh` 不存在），其 skill 走插件 `presets/*/skills/` 内嵌分发。默认**不写**；只有显式指定才投放：

```bash
python tools/sync_skills.py --apply --dsh-preset "<preset>/skills"
```

## 不可破的开发约定

| 约定 | 原因 |
|---|---|
| 所有 `.py` / `.md` / `.yaml` 用 **LF + UTF-8** | `.gitattributes` 已锁定；CRLF 会让 `^##` 正则与哈希漂移 |
| frontmatter 只放 `name` + `description` | 实测四个 agent 根的最小交集；`allowed-tools` / `license` / `disable-model-invocation` 都不是通用字段 |
| `name` 必须小写 hyphen-case 且等于目录名 | Codex 会强行归一中文名 |
| `description` 不得含尖括号 | 校验门禁；也避免被当占位符 |
| 纯标准库；**禁用** `fcntl` / `os.getuid()` / `pwd` / `grp` / `termios` | RedSkill CLI 在 Windows 正是死在 `import fcntl` 与 `os.getuid()`；`selftest.py` 会静态扫描这五项 |
| 路径一律走 `expand_path()`，用 `~` / 相对路径 / 环境变量 | 不硬编码盘符或分隔符；Mac 可移植 |
| 产物只写工作区根 `./HANDOFF.md` | 临时目录只作 staging；同名另存带时间戳文件，不静默覆盖 |
| 成功导出只留 **1 个**最终文件 | 不留草稿、校验报告、receipt、解压目录、checksum |
| 校验器只读，不修复 | `PASS` 只代表结构过关，不代表事实为真或已获授权 |
| 不碰任何 agent 配置文件 | 完全手动触发靠 description + 正文 + `agents/openai.yaml` 三道软/硬门 + 脚本默认 `--check` |

## 验收清单

- [x] `quick_validate.py` 通过（name / description / 目录名 / 无尖括号）
- [x] 4 个夹具行为符合预期：合规 0 错、占位符 2 错、破坏性命令 1 错、中文误报样本 0 错
- [x] 模板原文会被「模板残留」门禁拦住（修掉"空模板也能 PASS"的漏洞）
- [x] `selftest.py` 全套通过：**21 项 0 失败**（含静态扫描、LF/UTF-8、四级解释器兜底、MANIFEST 一致性、解压自检与篡改检出）
- [x] `--apply` 后四根各 16 文件、sha256 与 MANIFEST 全一致；Codex 手动门在四根均在位
- [x] 打包完整性 / 卫生 / MANIFEST 三门禁通过，`standard-handoff-1.0.1.zip` 16 条目、反解压自验通过
- [x] `--uninstall --check` 预演不误删；`settings.json` 的 `skillOverrides` 未新增本技能条目

## 待回填（本机 Windows 无法实测）

1. macOS 上四个 skills 根目录是否真实存在、路径大小写与权限。
2. DSH preset 的实际注册约定，`dist/standard-handoff/` 放入后是否被加载。
3. zsh 登录环境下 `python3` / `py -3` 的 PATH 命中情况。
4. macOS 文件名的 NFD/NFC 归一化对 `MANIFEST.sha256` 相对路径键的影响。
5. macOS 上 `chmod` 与 `os.replace` 原子替换行为。
6. 跨机器复制后逐文件哈希是否仍一致——1.0.1 起可用 `verify_install.py` 在 Mac 侧直接复验。

回填后请同步更新 `skills/standard-handoff/README.md` 的「macOS 自检」与「DSH」两节，并重新生成 MANIFEST。

## 版本

当前 `1.0.1`，见 `CHANGELOG.md`。版本号只出现在 zip 文件名与 CHANGELOG，不进 frontmatter（非跨 agent 通用字段）。
