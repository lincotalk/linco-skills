# Linco Skills

[English](README.md) | [简体中文](README.zh-CN.md)

Linco 维护的开源 Agent Skills。

## 内置 Skill

### `material-to-video`

将用户选择的本地素材、经过调研的主题，或两者结合，制作成来源可追溯、带旁白的竖屏视频，适用于抖音、小红书、微信视频号，或生成一个跨平台通用版本。

该 Skill 负责素材接入、本地内容提取、调研记录、事实追溯、编辑策划、VoxCPM 旁白、封面规划和有限轮次的视觉审查。HyperFrames 负责视频合成、预览、检查和渲染。

支持的本地输入格式包括 PNG、JPEG、WebP、GIF、PDF、DOCX、PPTX、TXT、Markdown、HTML、WAV、MP3、M4A、MP4、MOV 和 WebM。文本、HTML、DOCX 和 PPTX 文件会在本地提取内容；音视频元数据通过 FFprobe 获取；PDF 文本可选用 `pypdf` 或 `pdftotext` 提取。对于需要语义理解的图片和媒体，在完成视觉审查或转录记录前，工作流会保持硬性阻断。

## 环境要求

- Codex Desktop，并且能够访问用户选择的本地路径
- Python 3.10 或更高版本
- Node.js 22 或更高版本
- FFmpeg 和 FFprobe
- 用于合成、预览和渲染的 HyperFrames
- 启用旁白时，需要兼容的 VoxCPM Gradio 服务端点
- 可选：用于确定性提取 PDF 文本的 `pypdf` 或 `pdftotext`

除此之外，仓库中的 Python 脚本仅使用标准库。

## 安装

### 使用 Skills CLI 安装

将 `material-to-video` 安装到当前项目：

```bash
npx --yes skills add lincotalk/linco-skills@material-to-video -y
```

在 Windows PowerShell 中，如果脚本执行策略阻止运行 `npx.ps1`，请改用 `npx.cmd`：

```powershell
npx.cmd --yes skills add lincotalk/linco-skills@material-to-video -y
```

项目级安装会将 Skill 放到 `.agents/skills/material-to-video`，使其随项目一起管理。添加 `-g` 可执行用户级安装，让所有项目都能使用：

```bash
npx --yes skills add lincotalk/linco-skills@material-to-video -g -y
```

安装或更新视频合成和渲染所需的 HyperFrames Skill 包：

```bash
npx hyperframes@latest skills
```

安装完成后重新加载 Codex，以便发现新的 Skill。

### 从源码安装

克隆仓库，可按需切换到某个发布标签，然后将 `material-to-video` 复制到 Codex Skills 目录。

PowerShell：

```powershell
git clone https://github.com/lincotalk/linco-skills.git
Set-Location .\linco-skills
# 可选：git checkout v0.1.0

$codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
New-Item -ItemType Directory -Force (Join-Path $codexRoot "skills") | Out-Null
$skillTarget = Join-Path $codexRoot "skills\material-to-video"
New-Item -ItemType Directory -Force $skillTarget | Out-Null
Copy-Item -Recurse -Force .\material-to-video\* $skillTarget
```

Bash：

```bash
git clone https://github.com/lincotalk/linco-skills.git
cd linco-skills
# 可选：git checkout v0.1.0

mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/material-to-video"
cp -R ./material-to-video/. "${CODEX_HOME:-$HOME/.codex}/skills/material-to-video"
```

确认 `<skills-directory>/material-to-video/SKILL.md` 存在，然后重新加载 Codex。以后要更新源码安装版本时，在克隆的仓库中运行 `git pull`，再重复执行复制命令即可。HyperFrames 会为每个生成的项目固定 CLI 版本，保证后续预览和渲染命令可复现。

## 使用方法

示例请求：

```text
使用 $material-to-video，把这些幻灯片制作成小红书视频：D:\materials\deck.pptx
```

```text
使用 $material-to-video，调研 MCP 工具发现和权限之间的区别，然后制作一个抖音技术单点视频。
```

```text
使用 $material-to-video，结合这些本地笔记和最新官方来源，制作一个跨平台通用版本。除最终渲染的必要确认外，请自主完成整个流程。
```

每个任务都会隔离在 `<workspace>/jobs/<job-slug>/` 目录中。来源记录和编辑模型保存在任务根目录；HyperFrames 项目位于 `project/`，其根目录会按照 HyperFrames 的要求包含 `BRIEF.md`、`STORYBOARD.md` 和 `SCRIPT.md`。

该 Skill 不会将最终结果发布或上传到任何社交平台。

## 旁白服务

本仓库不包含、不托管，也不预设任何旁白服务端点。请部署 [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM)，然后配置其兼容 Gradio 服务的基础 URL。该 URL 必须提供 `/config`、`/gradio_api/info`，以及 [`tts-contract.md`](material-to-video/references/tts-contract.md) 中说明的具名 `/generate` API。

请勿配置具体的 `/generate` 路由。例如，应使用 `https://tts.example.com`，而不是 `https://tts.example.com/generate`。

PowerShell：

```powershell
$env:VOXCPM_TTS_URL = "https://your-voxcpm-service.example.com"
$env:VOXCPM_TTS_TOKEN = "your-bearer-token" # 仅在服务要求时设置
python material-to-video/scripts/generate_voxcpm_voice.py --check `
  --config material-to-video/assets/config.example.json
```

Bash：

```bash
export VOXCPM_TTS_URL="https://your-voxcpm-service.example.com"
export VOXCPM_TTS_TOKEN="your-bearer-token" # 仅在服务要求时设置
python material-to-video/scripts/generate_voxcpm_voice.py --check \
  --config material-to-video/assets/config.example.json
```

也可以通过 `--endpoint` 参数或任务本地配置中的 `tts.endpoint` 指定端点。建议使用 `VOXCPM_TTS_TOKEN`，不要使用可能暴露在进程列表中的 `--auth-token`。切勿将凭据写入端点 URL 或任务配置。

无需发起网络请求即可检查配置：

```bash
python material-to-video/scripts/generate_voxcpm_voice.py --check-config \
  --config material-to-video/assets/config.example.json
```

首次使用时，该 Skill 会自动执行离线预检。如果没有配置服务，它会提供 OpenBMB/VoxCPM 的链接，并请已经完成部署的用户提供 Gradio 服务基础 URL。内容策划仍可继续，但在服务配置完成并通过在线 `--check` 前，旁白阶段会保持阻断。

未配置端点时，客户端会返回 `tts_not_configured`，不会发起网络请求，并保留已经确认的脚本以便恢复。请将任何已配置的 TTS 服务视为外部数据处理方，不要向不可信的部署发送机密旁白或参考音频。

## 验证

贡献代码或发布版本前，请运行仓库检查：

```bash
python -m compileall -q material-to-video
python -m unittest discover -s tests -v
```

CI 会在 Windows 和 Ubuntu 上，使用 Python 3.10 与 3.12 运行相同的检查。VoxCPM 在线调用和完整的 HyperFrames 渲染依赖外部服务，因此有意不纳入仓库 CI。

## 安全与隐私

本地素材只会从用户明确选择的路径中读取。工作流不会向搜索服务披露本地私有内容；会拒绝清单路径穿越、阻止跨源 TTS 重定向，并避免将 Bearer Token 写入生成的清单。漏洞报告方式请参阅 [SECURITY.md](SECURITY.md)。

## 参与贡献

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。提交贡献即表示你同意该贡献按 MIT 许可证授权。

## 许可证

Copyright 2026 Linco。基于 [MIT License](LICENSE) 授权。
