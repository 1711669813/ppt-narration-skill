# 排错速查

## 环境类

| 现象 | 原因 | 处理 |
|---|---|---|
| `python -m pip` 报错/无 pip | 默认解释器是精简 venv | 用 `py -0` 列出的解释器，Windows 常见 `D:\anaconda3\python.exe` |
| `ffmpeg: command not found` | ffmpeg 未在 PATH | 装 ffmpeg 并加 PATH；`00_check_env.py` 会直接报出来 |
| `ImportError: win32com` | 缺 pywin32 | `pip install pywin32`；仍失败改用 LibreOffice 路径 |
| COM 导出报"PowerPoint 无法启动" | Office 未安装/未激活，或被安全软件拦 | 用 LibreOffice：`soffice --headless --convert-to pdf deck.pptx` 再 `pdftoppm -r 150 -png deck.pdf slide` |
| anaconda 里装完包，streamlit 坏了 | pip 升了 pillow/protobuf | 记住原版本，装完 `pip install "pillow==<原版本>" "protobuf<5"` 还原 |
| `edge-tts` 报网络错误 | 公司网络拦 websocket | 换网络/热点；edge-tts 需要联网（音色是服务端模型） |
| `faster-whisper` 报 OpenMP 冲突 | Windows 上 libiomp 重复加载 | 设环境变量 `KMP_DUPLICATE_LIB_OK=TRUE` |

## 画面类

| 现象 | 原因 | 处理 |
|---|---|---|
| 放大后的画面被**纵向拉长** | 放大窗口宽高比算错（`vh = vw*9/16`） | 归一化坐标下 16:9 窗口＝正方形，改 `need` 同时作为宽高；加断言 |
| 画面出现**黑边** | 窗口超出页面（`vx0` 被夹成负数） | 夹取要用 `min(max(v, 0), max(0, 1-need))`，并且 `need ≤ 1.0` |
| 放大后文字发虚 | 页面图只导了 1920 | 导 4K（`pres.Export(OUTDIR,"PNG",3840,2160)`） |
| 高亮框框错位置 | 坐标来自 group 内 shape 未换算 | 用 grpSpPr 的 `chOff/chExt` 换算成绝对坐标（`01_extract_ppt.py` 已处理） |
| 表格高亮整表而不是某行 | 只用了表格整体矩形 | 用 `row.height` 现算行矩形；表头是第 0 行 |
| 背景太暗 / 太亮 | `DIM_BOX`/`DIM_LINE` 不合适 | 调这两个常量（默认 72 / 46），不是删标记 |
| 每句都闪，看不出重点 | 所有 cue 都画框 | 把"这页讲什么"、过渡句、首页、末页改成 `m="none"` |

## 音频/时序类

| 现象 | 原因 | 处理 |
|---|---|---|
| 标记与语音**漂移** | 没拿到词级时间戳 | `edge_tts.Communicate(..., boundary="WordBoundary")`；检查日志里每页是 `wordboundary=exact` |
| 词边界拿不到（中文返回 0 事件） | edge-tts 版本行为差异 | 升级 edge-tts；仍不行则脚本自动退回按字数比例对齐，并打印 `fallback` 告警 |
| 每页停留比预期长 0.6 秒 | mp3 尾部自带静音被算进页时长 | 用 `silencedetect` 取真实说话结束点再加 1.0 秒 |
| 总时长比预算长 10% | 每句句末都用"。"，停顿累积 | 列表项之间改"；/，"；或用 `prompts/02` 的压缩顺序 |
| 音频与画面对不齐 | concat 各帧时长未对齐 1/30 秒 | 帧时长按 1/30 秒取整，最后一帧吃掉舍入余量，使每页总时长精确 |

## 验收类

| 现象 | 检查 |
|---|---|
| 怀疑串页/串句 | `05_verify.py` 逐句帧比对（均值差 <3） |
| 怀疑放大拉伸 | `05_verify.py` 几何检查（目标块差 <22、黑边 <1.5%） |
| 怀疑"标的不是正在讲的" | 抽几段 cue 音频 ASR，看关键词是否落在该 cue 的转写里 |
| 怀疑没声音/声音小 | `ffmpeg -i out.mp4 -af volumedetect -f null -`，看 mean/max 音量 |
