# 在另一台电脑上安装与使用

这份说明随 `standard-handoff-1.0.1.zip` 一起分发。**解压后请先看本文件**——另一台电脑上没有这段对话记录。

整包不需要联网、不需要安装器、不需要第三方依赖。它就是一个标准 Agent Skills 目录；只有想做完整性自检时才需要 Python 3.9+。

## 0. 拿到什么

解压 zip 得到顶层目录 `standard-handoff/`：

```text
standard-handoff/
├── SKILL.md                    主文件（仅 name + description）
├── INSTALL.md                  本文件
├── README.md LICENSE NOTICE.md MANIFEST.sha256
├── agents/openai.yaml          Codex 手动门
├── assets/handoff.template.md  默认模板
├── references/                 rigor / quality / packaging / receiving
└── scripts/                    _common / handoff_validate / quick_validate / verify_install
```

共 **16 个文件**（含 `MANIFEST.sha256`）。**不要增删或编辑包内文件**，否则哈希校验会失败。

## 1. 先自检（推荐，可选）

进入解压出来的 `standard-handoff/` 目录：

```bash
# macOS / Linux
python3 scripts/verify_install.py

# Windows（PowerShell 或 Git Bash）
py -3 scripts/verify_install.py
```

看到 `PASS: ... file(s) match MANIFEST` 即可。它逐文件比对 sha256、检查 frontmatter 与 LF，**只读、不修复、不写盘**。

> 输出里的 `15 file(s)` 是 MANIFEST 列出的文件数；`MANIFEST.sha256` 自身不列入（否则会自指），所以目录里一共 16 个文件。两个数字不矛盾。

装完之后也能回头验某个已安装副本：

```bash
py -3 scripts/verify_install.py --target "~/.claude/skills/standard-handoff"
```

`FAIL` 的常见原因：解压不完整、传输中被改写、用编辑器改过文件、行尾被转成 CRLF。重新解压或整个目录重拷一次，别手工补丁。

## 2. 装到 agent 根目录

四个目标的路径写法在 Windows 与 macOS 上完全一样：

| Agent | 目标 |
|---|---|
| WorkBuddy | `~/.workbuddy/skills/standard-handoff` |
| Claude Code | `~/.claude/skills/standard-handoff` |
| Codex | `~/.codex/skills/standard-handoff` |
| 通用第四根 | `~/.agents/skills/standard-handoff` |

只用一个 agent 就只装那一个。以下命令假设你在 zip 解压出来的**父目录**里。

### Windows PowerShell

```powershell
$dest = @("$HOME\.workbuddy\skills", "$HOME\.claude\skills", "$HOME\.codex\skills", "$HOME\.agents\skills")
foreach ($d in $dest) {
  $t = Join-Path $d "standard-handoff"
  if (Test-Path $t) { Write-Host "跳过（已存在，请先备份或改名）: $t"; continue }
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  Copy-Item -Recurse -Path .\standard-handoff -Destination $t
  Write-Host "已安装: $t"
}
```

只装 WorkBuddy 一根：

```powershell
Copy-Item -Recurse -Path .\standard-handoff -Destination "$HOME\.workbuddy\skills\standard-handoff"
```

### macOS / Linux（bash / zsh）

```bash
for d in ~/.workbuddy/skills ~/.claude/skills ~/.codex/skills ~/.agents/skills; do
  mkdir -p "$d"
  t="$d/standard-handoff"
  if [ -e "$t" ]; then echo "跳过（已存在）: $t"; else cp -R standard-handoff "$t"; echo "已安装: $t"; fi
done
```

**目标已存在时先备份或改名，不要静默覆盖。** 确认旧副本可以丢弃后，用 `--target` 看差异，再整个目录替换。

> **DSH（DeepSeek Harness 桌面端）**：不走用户级目录扫描，skill 由插件 `presets/*/skills/` 内嵌分发。把整个 `standard-handoff/` 目录放进对应 preset 的 `skills/` 下即可；能否加载取决于该 preset 的注册约定，需自行验证。

## 3. 确认生效

**新开一个会话**（技能目录通常在会话启动时扫描）：

- WorkBuddy / Claude Code：技能列表里出现 `standard-handoff`；也可显式说 `$standard-handoff` 调用。
- Codex：`agents/openai.yaml` 的 `policy.allow_implicit_invocation: false` 保证它不被隐式注入。
- 用 `verify_install.py --target` 复验装进去的那份与 MANIFEST 一致。

## 4. 使用（完全手动）

| 场景 | 口令 | 结果 |
|---|---|---|
| 会话告一段落 | 「写交接文档」/「生成 handoff」/「交接」 | 工作区根 `./HANDOFF.md`，只留 1 个文件 |
| 换窗口 / 换 agent 后接上 | 「接收交接」/「读交接继续」 | 聊天回执，默认不写文件、不继续 |

完整口令：`交接`、`handoff`、`写交接文档`、`接收交接`、`生成 handoff`、`读交接继续`。

```text
你：写交接文档
它：已选择 HANDOFF.md：未发现必须随包携带的附件。→ ./HANDOFF.md
（换 agent，打开同一项目）
你：接收交接
它：接收成功，按要求未继续。当前目标… / 停止位置… / 建议下一步…
你：按交接第 1 步继续
它：才开始动手
```

三条边界：

- 它**不会**因会话变长、上下文压缩或任务快结束而主动提示；不说口令就不动。
- 接收后停下是**成功暂停**，不是失败；要继续执行必须再明确说一次。
- `发送 / 发布 / 付款 / 删除 / 安装 / 执行 / 披露 / 外部写入`：旧交接里的同意一律不算，当前会话重新确认。

需要带附件就说「交接，用 zip」，正式审计说要 audit 档；严谨溯源、打分、落盘冲突、接收签收等高级能力按需翻开 `references/`，普通导出一份都不读。

可选校验产物（在装好的技能目录里运行，把路径换成真实产物）：

```bash
py -3 scripts/handoff_validate.py /path/to/your/HANDOFF.md
```

`PASS` 只说明结构过关，不代表事实为真或下一步已获授权。

## 5. 卸载

手动删除对应目录即可，删除前确认路径：

```powershell
Remove-Item -Recurse "$HOME\.claude\skills\standard-handoff"
```

```bash
rm -rf ~/.claude/skills/standard-handoff
```

不会改动任何 `settings.json` 或其它 agent 配置；本包从来没有写入过它们。

## 6. 注意事项

- 源仓库的 `tools/`、`evals/`、`dist/` **不随包分发**；一源多装同步、打包、全套自检只在源仓库里。
- 想改内容请回源仓库改，重建 `MANIFEST.sha256` 后重新打包；直接改镜像会让哈希校验失败。
- 产物 `HANDOFF.md` 写在工作区根，**绝不写进 agent 配置目录**；同名已存在会另存带时间戳的文件。
- 校验器不验事实真伪、来源授权、语义连续性，也不宣称跨模型无损。
- **macOS 未实测**：六项待回填（四根是否真实存在、DSH preset 约定、zsh PATH 命中、NFD/NFC、chmod 与原子替换、跨机哈希一致）见源仓库 `README.md`。Windows 侧四根同步与哈希一致已实测。
