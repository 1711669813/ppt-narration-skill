# 用到的"模型"清单

这个包里没有自带大体积权重文件，因为**核心的语音模型是在线服务**，只有验收用的 ASR 模型需要本地下载（可选）。下面是完整清单。

## 1. 配音音色（必需，在线，无需下载）

`edge-tts` 调用的是微软在线语音服务，**音色本身就是服务端模型**，本地只发文本、收音频，所以包里不需要放权重。前提：**运行时需要联网**。

| voice id | 音色 | 适合 |
|---|---|---|
| `zh-CN-YunyangNeural` | 云扬·男声·新闻播报 | **正式汇报首选（默认）** |
| `zh-CN-YunjianNeural` | 云健·男声·激情解说 | 宣传、动员 |
| `zh-CN-YunxiNeural` | 云希·男声·年轻阳光 | 培训、科普 |
| `zh-CN-YunxiaNeural` | 云夏·男声·少年 | 演示、动画讲解 |
| `zh-CN-XiaoxiaoNeural` | 晓晓·女声·温暖新闻 | 正式汇报（女声） |
| `zh-CN-XiaoyiNeural` | 晓依·女声·活泼 | 培训、科普 |

列出你自己账号可见的全部音色：

```bash
edge-tts --list-voices | grep zh-CN
python -c "import asyncio,edge_tts;print('\n'.join(v['ShortName'] for v in asyncio.run(edge_tts.list_voices()) if v['Locale']=='zh-CN'))"
```

生成试听片段（在包根目录执行，先创建 `results/音色试听/`）：

```bash
edge-tts --voice zh-CN-YunyangNeural --rate=+8% \
  --text "先看建设背景。本部总体管理需要两类可持续的对外服务。" \
  --write-media results/音色试听/sample_yunyang.mp3
```

## 2. 本地 ASR 模型（可选，仅用于验收）

用途：把成片里几段音频转成文字，确认"画面上标的那块"正是"正在讲的那句"。不做这一步也能出片，但这是唯一能自动证明标记与台词一致的办法。

| 模型 | 体积 | 说明 |
|---|---|---|
| `Systran/faster-whisper-small` | ≈ 480 MB | 默认；中文术语识别够用（实测能正确转出"AI 能碳管家""二〇二六年九月"） |
| `Systran/faster-whisper-base` | ≈ 145 MB | 体积小、精度略低，够做关键词抽查 |
| `Systran/faster-whisper-tiny` | ≈ 75 MB | 只为确认"有没有声音/说的是不是这段"时用 |

下载（脚本会自动用包内 `results/cache/huggingface/hub` 缓存目录，重复运行不会重复下载）：

```bash
python models/fetch_models.py                 # 默认 small
python models/fetch_models.py base            # 换体积
```

## 3. 字体（仅在"把字幕烧进画面"时需要）

`scripts/06_burn_subtitles.py` 会自动按平台找中文字体：Windows 用 `msyh.ttc`（微软雅黑），macOS 用 `PingFang.ttc`，Linux 用 `NotoSansCJK`。找不到时脚本会提示安装，不烧字幕则完全不需要字体。
