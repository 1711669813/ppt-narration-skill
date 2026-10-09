---
name: ppt-narrated-video
description: 将 PPT 制作为逐句高亮标记的讲解录屏，生成前让用户选择讲解语言风格，生成配音、1080p 视频、对照稿与字幕，并统一保存到包内 results。
---

# SKILL：把 PPT 做成"逐句标记"的讲解录屏（1080p MP4 + 对照稿 + 字幕）

> 这份文档是**给任意大模型 / Agent 的执行规范**。把整个包（本文件 + `README.md` + `scripts/` + `templates/` + `references/` + `prompts/` + `models/`）交给模型，它应当能独立复现同规格成品。
>
> 关键要求：**不擅自改动 PPT 内容**；逐页写口语讲稿（解释，不逐字念）；**讲到哪一段就把那一段在画面上标出来**（其余部分轻轻压暗）；按配音实际时长自动翻页，讲完留约 1 秒；输出 1080p MP4 + "页码—讲稿—时长"对照稿；总时长服从用户给的上限。

---

## 输出目录规则

每次调用本包，新生成的所有任务内容统一保存在**本包根目录下的 `results/`**，包括成片、字幕、讲稿与 cue、试听音频、页面图、坐标数据、时间轴、渲染帧、复核截图、报告、日志、临时文件及模型缓存。开始前创建该目录；需要区分任务时使用 `results/<任务名>/`。

脚本默认自动定位包内 `results/`。`BUILD_ROOT`、`OUT_DIR`、`--root` 和 `--out` 的相对路径均以 `results/` 为基准，绝对路径也必须在其中；指向外部的旧配置会报错。模型另外生成的文件、命令重定向和临时辅助脚本也必须遵守此规则。原始 PPT 仍从用户提供的位置读取。


## 0. 输入 / 输出

| 项 | 内容 |
|---|---|
| 输入 | 一个 .pptx；用户口述的要求（讲解风格、受众、时长上限、音色、是否要字幕、重点页） |
| 输出 1 | 1080p MP4（1920×1080、30fps、H.264＋AAC）。画面＝原 PPT 页面全屏；讲到某一句时，该句对应的页面区域出现标记 |
| 输出 2 | 对照稿（Markdown）：①页码–时长总览表 ②**逐句**"时间轴—画面标记—讲稿"表 ③讲稿全文 |
| 输出 3 | 字幕（按用户选择）：**默认只给 `.srt` 外挂文件**，不烧进画面；用户要求烧入时才用 `scripts/06_burn_subtitles.py` 生成带字幕的副本 |
| 硬约束 | 页面顺序/文字/图片/版式与原 PPT 一致；术语、数字、项目名与 PPT 完全一致；材料没写的事实不编造；总时长 ≤ 用户上限（常见"不超过十分钟"）；PPT/备注标注的"虚拟数据/占位符/待确认"要如实带一句 |

---

## 1. 生成前的选择：讲解风格、音色、画面标记、字幕、时长

### 1.0 讲解语言风格 —— 每次新生成视频前让用户选择

收到 PPT 后，先读取 [references/narration-styles.md](references/narration-styles.md)，向用户展示其中的八种风格及自定义选项，请用户选择本次的讲解风格。可结合 PPT 推荐一到两种，但不能根据题材、所选音色或上次任务的风格自行决定。本次请求已经明确指定风格（包括明确说沿用上次）即视为已选择，不重复询问；同一任务的修稿、重渲染沿用本次选择，用户要求换风格时更新。

**未收到本次风格选择时，不写正式讲稿、不进行整片配音或合成。** 等待期间可检查环境、抽取 PPT 内容与坐标、导出原页面。不要把“专业商业汇报”设为自动默认，也不要因用户未回答而替其选定。风格与音色是两个独立选项，可与原有音色、字幕、时长问题合并询问；受众不明确时按所选风格和 PPT 内容合理推断，仅在确实影响讲解深度时补问。

选择后读取对应风格的写作规则，将名称、受众、幽默程度、举例方式及自定义要求写入本次 `results/cues.py`（或任务子目录的 cue 文件）中的 `NARRATION_STYLE` 字典，按 `prompts/01_写讲稿与cue.md` 写稿。它只记录本次选择，不代表新增 TTS 情绪参数；视频、演讲稿与字幕继续取自同一套 cue 文本。`04_make_sheet.py` 会在对照稿顶部显示风格信息。

### 1.1 音色 —— 用"列清单 + 生成试听片段 + 让用户选"

中文候选（完整表见 `references/voices.md`）：

| 音色 | 类型 | 适合 |
|---|---|---|
| `zh-CN-YunyangNeural` | 男声·新闻播报 | **正式汇报首选（默认推荐）** |
| `zh-CN-YunjianNeural` | 男声·激情解说 | 宣传、动员 |
| `zh-CN-YunxiNeural` | 男声·年轻阳光 | 培训、科普 |
| `zh-CN-YunxiaNeural` | 男声·少年 | 演示、动画讲解 |
| `zh-CN-XiaoxiaoNeural` | 女声·温暖新闻 | 正式汇报（女声） |
| `zh-CN-XiaoyiNeural` | 女声·活泼 | 培训、科普 |

做法：先生成**试听片段**（同一句话，每个候选一个 mp3，放到包内 `results/音色试听/`），再让用户选。

```bash
edge-tts --list-voices | grep zh-CN
mkdir -p results/音色试听
edge-tts --voice zh-CN-YunyangNeural --rate=+8% \
         --text "先看建设背景。本部总体管理需要两类可持续的对外服务。" \
         --write-media results/音色试听/sample_yunyang.mp3
```

### 1.2 画面标记方式

默认＝**暗化其余部分 + 高亮框 + 小块自动放大**；并按 `references/mark-styles.md` 的规则**混用四种标记**：

| 标记 | 效果 | 用在哪 |
|---|---|---|
| `none` | 整页原样，不暗化、不画框、不放大 | **首页、末页**；每页开头"这页讲什么"的页标题/导语 |
| `line` | 轻暗化 + 目标下方画下划线 | 说明行、提示行、待确认事项、口径文字 |
| `box` | 暗化 + 高亮框，不放大 | 较宽的卡片带、表格行、流程条、通栏 |
| `zoom` | 暗化 + 高亮框 + 自动放大（1.1–2.5 倍） | 较小的卡片、表格行、图、流程小块 |

**不要每句都标记**：引导句/过渡句/只看整页的句子用 `none`。用户若嫌画面暗，优先调小 `DIM_BOX`（默认 72 ≈ 28% 黑）、`DIM_LINE`（46 ≈ 18% 黑），而不是删标记。

### 1.3 是否需要字幕 —— 一定要问

- 默认交付**外挂 `.srt`**（半透明黑底白字由播放器决定，画面保持干净）；
- 用户要"烧进画面"时才跑 `scripts/06_burn_subtitles.py`（半透明黑底白字、两行一行居中、底部安全边距）；
- 用户说不要字幕就什么都不生成。

### 1.4 时长上限与语速

先按"每秒约 5.2 字（rate +6%）"估算，写完讲稿后用**实测**校正（见 3.3）。接近上限时的处理顺序：

1. 压缩讲稿（删重复、删可从画面看出的列举）——**不要为了凑时间漏掉重点**；
2. 才考虑把 rate 从 +6% 提到 +8%（听感几乎无差别，纯语速）；
3. 最后才考虑减少页面停留（"留约 1 秒"是下限，不要低于 0.8 秒）。

---

## 2. 环境与依赖

```bash
python -m pip install -r requirements.txt      # 或用 install.bat / install.sh
python scripts/00_check_env.py                 # 环境自检：解释器、pip、ffmpeg、Office、edge-tts 连通、字体
```

- 必需：`python-pptx`、`edge-tts`、`pillow`、`numpy`；**ffmpeg / ffprobe 必须在 PATH**。
- Windows：**不需要 LibreOffice**。装了 Microsoft Office 就用 PowerPoint COM 导出页面图（保真度最高，图表/地图/字体原样），需要 `pywin32`。
- Linux/macOS：用 LibreOffice 导出（`scripts/02_export_slides.py` 里有命令）。
- **找不到能装包的 python 时**：Windows 上常见"hermes venv 的 python 没有 pip"，换 `py -0` 列出的、或 `D:\anaconda3\python.exe` 这类自带 pip 的解释器。
- **共享的 anaconda/系统环境**：装包前记下 `pillow`、`protobuf` 版本，装完还原（streamlit 需要 `pillow<11`、`protobuf<5`）。
- 模型：`edge-tts` 的音色是**服务端模型**，无需下载，但需要联网；复核用的 ASR 模型可选，见 `models/README.md`。
- 工作目录默认是包内 `results/`，子目录为 `slides_png_4k/`、`out2/audio/`、`out2/frames/` 等；脚本按自身位置定位，不依赖调用时的当前目录。

---

## 3. 执行流程

### 3.1 抽取内容与坐标 → `scripts/01_extract_ppt.py`

用 python-pptx 递归遍历 shape（**必须处理 group 的坐标变换**、table、chart），导出每页：

- 每个 shape 的名称、类型、**绝对包围盒（按页面宽高归一化到 0–1）**、文字；
- 每页**演讲者备注（notes）**——备注里常有"虚拟数据/占位符/待确认"的口径，讲稿不能与之矛盾。

产物 `shapes_geom.json` + 一张人可读坐标表。表格行的高亮不在这里算，由 `03_build_video.py` 按 `row.height` 现算（表头算第 0 行）。

### 3.2 导出页面图（4K）→ `scripts/02_export_slides.py`

```python
app = win32com.client.DispatchEx("PowerPoint.Application")
pres = app.Presentations.Open(SRC, ReadOnly=True, WithWindow=False)   # 不弹窗
pres.Export(OUTDIR, "PNG", 3840, 2160)                                # 4K！放大会用到
pres.Close(); app.Quit()
```

**为什么导出 4K**：放大时若源图只有 1920 宽，放大即发虚；4K 源 + 放大窗口不小于页面宽度的 40%，可保证放大部分仍是原生清晰度。
导出文件名是 `幻灯片N.PNG`，统一改名为 `slides_png_4k/slideNN.png`。**原动画无法在静态翻页视频里逐帧还原，统一以"完整页面"呈现**（内容一个不少）。

### 3.3 写讲稿并"cue 化"（本 skill 的核心）→ `templates/cues.example.py`

讲稿不是整页一段，而是**"一句＝一个画面标记"的 cue 列表**：

```python
CUES = {
 6: [
   {"t": "建设内容一，是本部的电碳统计分析与总体展示。",
    "r": [[0.215, 0.037, 0.973, 0.121]], "lb": "页标题", "m": "none"},
   {"t": "上方四个指标分别是统计范围内用电量、用电相关二氧化碳排放测算量、重点行业用电占比和授权覆盖客户数。",
    "r": [[0.044, 0.376, 0.953, 0.469]], "lb": "四个指标卡", "m": "box"},
   {"t": "统一统计上，区域与行业标签需要统一，本期建立分类字典与映射规则。",
    "tr": ["表格 11", [1]], "r": [], "lb": "表格第1行·统一统计", "m": "zoom"},
 ],}
```

字段：`t`＝这一句的口播文字（同页所有 `t` 拼起来就是整页讲稿，也是 TTS 输入）；`r`＝要高亮的一个或多个矩形（页面归一化坐标）；`tr`＝`[表格shape名, [行号...]]` 按行高亮；`lb`＝标记的中文名（写进对照稿）；`m`＝标记方式 `none/line/box/zoom`（可写成文件末尾的 `MODES` 表，脚本会自动填进每个 cue）。

**写 cue 的规则**

1. 一页 5–10 句；每句 1–3 行。别把整页罗成一长句，也别一句拆三个画面（切换太碎）。
2. 句子顺序＝页面元素的自然讲解顺序（标题 → 导语 → 主体分块 → 底部说明/口径提示）。
3. 数字、术语、项目名与 PPT 完全一致；"CO₂"口头说"二氧化碳"，"kWh"说"千瓦时"，"≤50"说"五十及以下"，Latin 缩写（AI、H01、客户A）照原样。
4. 用语言过渡把页与页接起来（"先看…""接着看…""这一页是…""最后是…"）。
5. 事实依据只用 PPT/备注；按所选风格可加入明确标注的假设情境、日常类比或提问，具体边界见 `references/narration-styles.md`。不得编造真实案例、数据、引文或结论。
6. 每句末尾标点影响停顿：真正的句子用"。"，列表项之间用"；/，"（能省不少停顿时间）。
7. `r` 要"刚好包住"目标块，不要横跨整页，否则暗化+高亮失去指向性。
8. 页标题/导语那种"这页讲什么"的句子 → `m="none"`；首页/末页 → 全部 `none`。
9. 新增举例、类比、提问必须写入 cue 的 `t`，计入实际配音、字幕与时长；关联已有概念时只标记该概念，无对应页面元素时用 `r=[]`、`m="none"`，不新增或改动 PPT 画面。

提示词模板见 `prompts/01_写讲稿与cue.md`。

**时长预算（实测校正用）**

| 语速 | 每字耗时 | 1000 字 |
|---|---|---|
| rate +6% | ≈ 0.194 s/字（含标点） | ≈ 3 分 14 秒 |
| rate +8% | ≈ 0.183 s/字 | ≈ 3 分 03 秒 |

总时长 ≈ Σ(每页口播时长) + 页数 × 1.0 秒（翻页停留）。先按预算写，**用 TTS 实测后再调**（脚本自带缓存，改一页只重跑那一页）。

### 3.4 配音：一定要拿到"词级时间戳" → `scripts/03_build_video.py`

```python
comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")  # ← 关键
async for chunk in comm.stream():
    if chunk["type"] == "audio":           data += chunk["data"]      # mp3 字节
    elif chunk["type"] == "WordBoundary":  words.append({"t": chunk["text"],
                                          "s": chunk["offset"] / 1e7,  # 100ns → 秒
                                          "d": chunk["duration"] / 1e7})
```

**必须显式传 `boundary="WordBoundary"`**：新版 edge-tts 默认 `SentenceBoundary`，中文还可能返回 0 个事件，那样只能退回按字数比例估算同步（明显漂移）。词级时间戳是"标记跟得上嘴"的根本。
一页一个 mp3（保持语气连贯），缓存名带 `hash(音色+语速+文本)`，改稿自动失效、没改的页复用。

### 3.5 句子 ↔ 词时间戳对齐

把整页口播去掉标点后与"所有词事件文本拼接"逐字符比对：

- 完全一致 → 每句起点＝该句第一个词的 `offset`，终点＝最后一个词的 `offset+duration`；每句起点再减 0.14 秒，让标记"话音未落先亮"。
- 不一致（少见）→ 打印告警，退回按每句字数占比切分该页时间。

页时长 = `silencedetect` 找到的**真实说话结束点** + 1.0 秒（翻页停留）：

```bash
ffmpeg -i page.mp3 -af silencedetect=noise=-40dB:d=0.30 -f null -
```

取最后一个 `silence_start`（mp3 尾部通常自带 ~0.6 秒静音，要减掉，否则停留变成 1.6 秒）。

### 3.6 渲染与合成

**每句的视图**（`view_rect`）

- `m=="zoom"` 且目标宽、高都小于页面 45% → 放大：以目标为中心、外扩 2.3 倍、窗口宽度不小于页面宽度的 40%，并夹在页面内；
- 其余标记（`none/line/box`）→ 保持整页。
- **坐标必须与页面同宽高比**：页面本身是 16:9，所以在归一化坐标下 16:9 窗口＝正方形（`vw == vh`）。用 `vh = vw * 9/16` 之类的字面换算会让窗口超出页面，PIL 用黑边补齐、或 `resize` 把画面拉扁。**务必断言 `abs(vw-vh) < 1e-9` 且窗口在页面内**。

**每帧的画法**（PIL，1920×1080）

1. 从 4K 页图裁出视图窗口 → `resize(1920×1080, LANCZOS)`；
2. 压暗：`L` 蒙版整幅填 `dim`，对每个标记矩形用 `rounded_rectangle(fill=0)` 抠亮；`Image.composite(黑, 原图, 蒙版)`。`dim` 取该帧所有标记的 `style_dim(style) × alpha` 最大值：`box/zoom` → `DIM_BOX=72`（≈28% 黑），`line` → `DIM_LINE=46`（≈18% 黑），`none` → 0（不压暗）；
3. 标记：`line` → 在目标块下方 7px 画 5–10px 圆角下划线（琥珀 `#FFBE00`）+ 淡光晕；`box/zoom` → 圆角描边 5px + 外圈 9px 半透明光晕。画在 RGBA 图层后 `alpha_composite`。

**过渡**：句与句之间 0.4 秒＝12 帧，同时插值"视图窗口"（平滑推近/拉远）与"标记透明度"（旧句淡出、新句淡入）；`none` 句的标记透明度和 `dim` 都归零，于是过渡会自然"退回整页原亮度"。翻页是硬切（像真 PPT）。

**合成**：帧按 `(文件, 时长)` 写进 concat 列表（时长对齐 1/30 秒，最后一帧吃掉舍入余量，保证每页总时长精确），音频用一路 `filter_complex` 逐页 `atrim=end=<页时长>,apad=whole_dur=<页时长>` 后 `concat`，最后

```bash
ffmpeg -f concat -safe 0 -i frames.txt -i narration.wav -map 0:v -map 1:a \
  -vf scale=1920:1080,setsar=1,fps=30,format=yuv420p \
  -c:v libx264 -preset medium -crf 18 -g 60 -c:a aac -b:a 192k -ar 48000 \
  -t <总时长> -movflags +faststart out.mp4
```

**字幕**：脚本顺带写 `subtitles.srt`（一句一条，长句按标点折成两行）。要烧进画面就再跑 `scripts/06_burn_subtitles.py`。

### 3.7 对照稿 → `scripts/04_make_sheet.py`

按第 4 节的格式生成，保存到包内 `results/`。

### 3.8 验收（必须做，别省）→ `scripts/05_verify.py`

1. `ffprobe`：1920×1080、30fps、H.264＋AAC、时长 ≤ 上限；`volumedetect` 确认不是静音。
2. **逐句帧比对**：每个 cue 时间点中点抽一帧，与"该 cue 应有的渲染帧"比像素（均值差 <3 即对齐），确认没有串页/串句。
3. **几何检查**（独立于渲染代码）：对抽样的 `zoom` 句，用纯 PIL 按 `view` 裁 4K 原图并缩放，与视频帧比对标记块内像素；若视频里被拉伸/有黑边，这个差值会很大（>22），黑边比例 >1.5% 也判失败。
4. **标记与台词一致性抽查**：抽 4–6 段 cue 的音频（`ffmpeg -ss/-t` 切），过一遍 ASR（faster-whisper，见 `models/README.md`；Windows anaconda 需 `KMP_DUPLICATE_LIB_OK=TRUE`），检查转写里出现该 cue 的关键词——证明"标的那块"正是"在讲的那句"。
5. 视觉抽查：抽若干帧用视觉模型确认框住了正确的块、压暗生效（但不过暗）、放大部分文字可读。
6. 对照本次 `NARRATION_STYLE` 人工检查讲稿：风格与受众是否匹配、例子是否帮助理解且明确标为假设/类比、幽默是否适度；新增内容是否同步进入配音、对照稿与字幕，并计入时长。`05_verify.py` 的技术检查不能代替这项内容复核。

---

## 4. 对照稿格式（交付物 2）

```markdown
# <项目名> 高亮讲解录屏 对照稿
源文件：<文件名>（N页 / M个讲解单元）
讲解风格：<本次选择>；受众：<受众>；幽默：<程度>；举例：<方式>；补充要求：<自定义要求>
配音：<音色中文名>（<voice id>），语速 +8%；每页讲完留约 1 秒再翻页
画面：1080p；讲到哪一段就标记那一段（框/下划线/放大），其余部分轻轻压暗；首页、末页与每页开头不标记
字幕：外挂 subtitles.srt（未烧入画面）
总时长：9分42秒（未超过 10 分钟）

## 一、总览：页码—时长对照
| 页码 | 页面标题 | 讲解单元 | 字数 | 本页时长 | 起始 | 累计 |

## 二、逐句对照：时间轴 — 画面标记 — 讲稿
### 第6页　06 建设内容一：…（本页 62.7 秒，起 3:45.2）
| # | 时间轴 | 本句时长 | 画面标记 | 讲稿 |
| 6.3 | 3:56.4–4:05.7 | 9.3s | 四个指标卡（高亮框） | 上方四个指标分别是… |

## 三、讲稿全文（可直接照读）
```

---

## 5. 常见坑（都踩过）

| 坑 | 现象 / 处理 |
|---|---|
| edge-tts 默认只给句级边界 | 词时间戳为空 → 只能按字数估时，标记漂移。**必须 `boundary="WordBoundary"`** |
| 放大窗口宽高比算错 | 画面被拉扁或出现黑边。归一化坐标下 16:9 窗口＝正方形，`vw == vh`；加断言 + 独立几何校验 |
| 压暗过重 | 用户会觉得"背景太黑"。`DIM_BOX=72`、`DIM_LINE=46` 起步，必要时更低 |
| 每句都标记 | 画面持续闪、看不出重点。"这页讲什么"的句子、首页、末页都不标 |
| mp3 尾部自带静音 | 若用 mp3 全长当页时长，"讲完留 1 秒"变成 1.6 秒。用 silencedetect 取真实收尾 |
| 每句句末都用"。" | 停顿累积，实测比预算多 10%+ 时长；列表项改用"；/，" |
| 源图只导 1920 | 放大后文字发虚。导 4K 再裁 |
| 又长又窄的条状元素放大 | 会切掉上下文，`m` 设 `box`/`line`，只标记不放大 |
| 表格要按行高亮 | 用 `row.height` 现算行矩形；表头是第 0 行 |
| group 内 shape 坐标 | 需用 grpSpPr 的 `chOff/chExt` 换算成绝对坐标，否则坐标全错 |
| Windows 没有 LibreOffice | 有 MS Office 就用 COM 导出；没有才装 LibreOffice／`soffice --convert-to pdf` + `pdftoppm` |
| Python 无 pip | 换 `py -0` 里带 pip 的解释器（如 anaconda） |
| 帧数多导致渲染慢 | 约 1000 帧 1920×1080（JPEG q92）≈ 3–5 分钟；帧放独立目录，编码后删除 |
| 时长正好卡上限 | 先按预算写、实测后再压缩文本；不要靠"砍停留"或"漏讲重点"省时间 |
| 共享环境依赖被改坏 | 装完把 pillow/protobuf 还原到原版本 |
| 字幕 | 默认外挂 `.srt`；只有用户明确要"烧进画面"才跑 06 脚本（会二次编码，略损画质） |

---

## 6. 包内清单与运行顺序

```
PPT讲解录屏skill/
├─ SKILL.md                     ← 本文件（交给模型的总规范）
├─ README.md                    ← 人读的工作流与细节说明（先看这个）
├─ requirements.txt             ← 依赖（含固定版本）
├─ install.bat / install.sh     ← 一键装依赖（Windows / macOS·Linux）
├─ prompts/
│   ├─ 01_写讲稿与cue.md         ← 让模型产出 cue 表的提示词（含规则、示例、自检）
│   ├─ 02_标记与时长调优.md       ← 标记方式、压暗强度、时长压缩的提示词
│   └─ 03_对照稿与字幕.md         ← 生成对照稿/字幕、以及复核的提示词
├─ scripts/
│   ├─ 00_check_env.py          环境自检（解释器/ffmpeg/Office/edge-tts 连通/字体）
│   ├─ 01_extract_ppt.py        抽取文字＋归一化坐标＋备注 → shapes_geom.json
│   ├─ 02_export_slides.py      导出 4K 页面图（PowerPoint COM；含 LibreOffice 备选）
│   ├─ 03_build_video.py        cue → TTS(词时间戳) → 对齐 → 标记渲染 → 合成 MP4 ＋ .srt
│   ├─ 04_make_sheet.py         生成"页码—讲稿—时长"对照稿
│   ├─ 05_verify.py             验收（容器/逐句帧/几何/黑边/ASR 抽查）
│   └─ 06_burn_subtitles.py     扩展：把 .srt 烧进画面（可选）
├─ templates/
│   ├─ cues.example.py          cue 表模板（本项目 90 段实战示例）
│   └─ sheet.example.md         对照稿样例
├─ references/
│   ├─ voices.md                edge-tts 中文音色一览与试听方法
│   ├─ narration-styles.md      讲解风格菜单、选择规则与举例边界
│   ├─ cue-rules.md             cue 编写细则 + 一个真实页面的完整示例
│   ├─ mark-styles.md           四种标记方式的判定规则（含压暗强度）
│   └─ troubleshooting.md       排错速查（错误码/报错 → 处理）
└─ models/
    ├─ README.md                用到的模型清单与获取方式
    └─ fetch_models.py          可选模型（ASR 复核）下载脚本
```

```bash
# 1) 环境
export PPTX="D:/deck.pptx"
# 在包根目录执行以下示例；清除旧输出路径配置，默认使用包内 results
unset BUILD_ROOT OUT_DIR
mkdir -p results
python scripts/00_check_env.py && pip install -r requirements.txt

# 2) 抽内容与坐标 → 让用户选择本次讲解风格 → 写 cue（人工/模型按 prompts/01 产出）
python scripts/01_extract_ppt.py
python scripts/02_export_slides.py
cp templates/cues.example.py results/cues.py     # 用户选好风格后，改成本项目的讲稿并填写 NARRATION_STYLE

# 3) 出片 + 对照稿
CUES_MODULE=cues TTS_RATE="+8%" python scripts/03_build_video.py
CUES_MODULE=cues python scripts/04_make_sheet.py
python scripts/05_verify.py                  # 必跑
```

**给使用者的最短指令**（把包交给模型时可直接这么说）：

> 用这个包里的 SKILL.md 流程，把 `<PPT 路径>` 做成讲解录屏视频：每次先让我选择本次讲解风格，再按所选风格写稿和举例；告诉我可选音色并让我试听，问我要不要字幕；标记方式用"框+下划线+放大"混用，首页/末页和每页开头不要标记；总时长不超过 10 分钟；所有新生成的内容放到包内 results 文件夹下。
