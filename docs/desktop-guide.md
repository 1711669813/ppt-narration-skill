# PPT 智能讲解视频生成器 · Windows 桌面版

## 下载与运行

从 GitHub Releases 下载 `PPTNarration-v0.1.0-Windows-x64.exe`，双击运行。
支持 Windows 10 / 11 x64，不需要安装 Python 或 FFmpeg。首次启动会解压内置运行库，请稍候。

电脑需要安装 PowerPoint，或者安装 LibreOffice 并将 `soffice` 和 Poppler 的 `pdftoppm` 加入 PATH。
当前版本支持 16:9 的 `.pptx`，输出 1080p MP4。原始 PPT 动画以静态完整页面呈现。

## 一键生成

1. 选择 PPT 文件。
2. 填写自己 AI 服务商的 API 地址、API Key 和模型名称。
3. 选择本次讲解风格、中文音色、语速、时长上限和保存位置。
4. 图表较多时，可勾选“将页面图片发送给 AI”，所填模型须支持图片。
5. 点击“开始生成视频”，完成后点击“打开结果”。

API 使用兼容 Chat Completions 的接口。地址填写服务商提供的完整地址，通常以 `/v1` 结尾；
也支持完整的 `/chat/completions` 地址。本机兼容服务可填写 `http://127.0.0.1:端口/v1`。
模型名称使用服务商实际提供的模型标识，不是网页聊天产品名称。

讲稿生成向所配置的 AI 服务发送 PPT 文本和备注；勾选视觉模式时也发送页面图片。
配音使用在线 edge-tts，会发送讲稿。生成期间需要联网，AI 请求费用由用户自己的服务账号承担。
API Key 只在当前进程内存中使用，不保存在偏好文件、命令行参数或任务日志中。
API 地址、模型名称及保存位置保存在 `%LOCALAPPDATA%/PPTNarration/preferences.json`。

## 输出文件

桌面版把所有任务文件放在所选保存位置的 `results/<时间戳_任务编号>/` 内：

- `讲解录屏_1080p.mp4`：成片。
- `subtitles.srt`：勾选字幕时生成的外挂字幕。
- `*_讲稿与时长对照稿.md`：逐页和逐句的时间轴与讲稿。
- `讲稿预览.txt`、`narration.json`、`cues.py`：生成的讲稿与高亮数据。
- `slides_png_4k/`、`out2/`：页面图片、音频、渲染帧和检查文件。

AI 返回的是 JSON 数据，程序验证目标形状及表格行后映射到实际坐标；不会执行 AI 返回的代码。
首页、末页和每页第一句保留整页画面。实测配音超过时长上限时会停止合成，可提高上限重试。
AI 讲稿仍需人工核对专业事实和图表解读。没有启用视觉模式时，图片中的文字及图表细节可能无法读取。

## 构建桌面版

在 Windows x64、Python 3.12 环境中执行：

```powershell
python -m pip install -r requirements-desktop.txt
python build_desktop.py
```

构建环境需在 PATH 中提供 `ffmpeg.exe` 和 `ffprobe.exe`。
成品输出到 `results/desktop-dist/`；构建文件及缓存也保存在 `results/`。
