# edge-tts 中文音色一览与试听方法

以下示例在包根目录执行，先创建 `results/音色试听/`；从其他目录调用时使用包内 results 的绝对路径。

## 1. 列出全部可用音色（含其它语言的男/女声）

```bash
edge-tts --list-voices | grep zh-CN          # 只看中文
edge-tts --list-voices > results/voices_all.txt      # 全量
```

Python：

```python
import asyncio, edge_tts
async def main():
    for v in await edge_tts.list_voices():
        if v["Locale"].startswith("zh-CN"):
            print(v["ShortName"], v["Gender"], v["VoiceTag"].get("ContentCategories"),
                  v["VoiceTag"].get("VoicePersonalities"))
asyncio.run(main())
```

## 2. 中文音色对照表（edge-tts 内置，无需自建模型）

| ShortName | 性别 | 官方标签 | 适合场景 |
|---|---|---|---|
| `zh-CN-YunyangNeural` | 男 | News / Professional·Reliable | **正式汇报、政府与企业汇报（默认首选）** |
| `zh-CN-YunjianNeural` | 男 | Sports·Passion | 宣传片、动员、有激情的解说 |
| `zh-CN-YunxiNeural` | 男 | Novel / Lively·Sunshine | 培训、科普、轻松口吻 |
| `zh-CN-YunxiaNeural` | 男 | Cartoon / Cute | 演示、动画讲解、面向年轻听众 |
| `zh-CN-XiaoxiaoNeural` | 女 | News·Warm | 正式汇报（女声，温暖） |
| `zh-CN-XiaoyiNeural` | 女 | Cartoon / Lively | 培训、科普（女声，活泼） |
| `zh-CN-liaoning-XiaobeiNeural` | 女 | Dialect·Humorous | 方言场景（东北） |
| `zh-CN-shaanxi-XiaoniNeural` | 女 | Dialect·Bright | 方言场景（陕西） |

多语言男/女声（`Multilingual` 结尾，例如 `en-US-AndrewMultilingualNeural`、`zh-CN-…`）也能读中文，但中文韵律通常不如上表。

## 3. 试听片段（推荐流程：先给用户听，再让他选）

```bash
edge-tts --voice zh-CN-YunyangNeural --rate=+8% \
  --text "先看建设背景。本部总体管理需要两类可持续的对外服务：政府侧专题支撑，客户侧核算服务。" \
  --write-media results/音色试听/云扬_男声_新闻播报.mp3
```

批量生成（Python）：

```python
import asyncio, os, edge_tts
SAMPLE = "先看建设背景。本部总体管理需要两类可持续的对外服务。用电相关二氧化碳排放测算量，等于各用电量与适用因子乘积之和。"
VOICES = [("zh-CN-YunyangNeural", "云扬_男声_新闻播报"),
          ("zh-CN-YunjianNeural", "云健_男声_激情解说"),
          ("zh-CN-YunxiNeural",    "云希_男声_年轻阳光"),
          ("zh-CN-YunxiaNeural",   "云夏_男声_少年"),
          ("zh-CN-XiaoxiaoNeural", "晓晓_女声_温暖新闻"),
          ("zh-CN-XiaoyiNeural",   "晓依_女声_活泼")]
async def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for v, label in VOICES:
        await edge_tts.Communicate(SAMPLE, v, rate="+8%").save(
            os.path.join(outdir, "%s（%s）.mp3" % (label, v)))
asyncio.run(main("results/音色试听"))
```

## 4. 语速 / 音量 / 音高

```python
edge_tts.Communicate(text, voice, rate="+8%", volume="+0%", pitch="+0Hz")
```

- `rate`：`+6%` 是"正式汇报"的稳妥值；`+8%` 只快约 2%，听感几乎无差别，常用于压时长；`-5%~0%` 适合教学。
- `pitch`：`+20Hz` 会更亮，`-20Hz` 更沉稳；正式汇报一般不动。
- `volume`：不要靠它调音量（后期统一 normalize 更保险）。

## 5. 想用别的开源语音模型（可选）

若用户点名要用非 edge-tts 的本地模型（CosyVoice / GPT-SoVITS / ChatTTS / Kokoro / Piper 等），接口要求只有两条：
1. 能对**一整页文本**合成一个音频文件；
2. **最好能给出词/字级时间戳**。没有时间戳时，本 skill 会退回"按字数占比"估算每句起点——高亮会有 0.3~1 秒左右漂移，写讲稿时尽量让每句长度接近以减轻漂移。

替换点：`03_build_video.py` 里的 `tts_page()`；保持返回 `(mp3_path, [{"t","s","d"}, ...])` 即可，其余流程不用改。
