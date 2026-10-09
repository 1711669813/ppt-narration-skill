# -*- coding: utf-8 -*-
"""生成"页码—讲稿—时长"对照稿，并把成片与字幕复制到交付目录。

用法：
    CUES_MODULE=cues python scripts/04_make_sheet.py
环境变量：
    BUILD_ROOT   工作目录（需有 timing2.json），默认包内 results
    OUT_DIR      交付目录，默认 BUILD_ROOT；必须在包内 results 下
    CUES_MODULE  cue 表模块名（默认 cues）；模块里可有 CUES，以及可选的 TITLES / NAME / SRCNAME / NARRATION_STYLE
    SHEET_NAME   对照稿文件名，默认 "<NAME>_讲稿与时长对照稿.md"
页面标题：优先取 cue 模块里的 TITLES[页码]，否则用该页第一句讲稿兜底。
"""
import sys
sys.dont_write_bytecode = True
from output_paths import build_root, delivery_root, output_path, MODEL_CACHE

import importlib, json, os, shutil, sys

ROOT = build_root()
OUT = delivery_root()
MOD = os.environ.get("CUES_MODULE", "cues")
sys.path.insert(0, ROOT)
cm = importlib.import_module(MOD)

VOICE_CN = {
    "zh-CN-YunyangNeural": "男声·云扬（新闻播报）", "zh-CN-YunjianNeural": "男声·云健（激情解说）",
    "zh-CN-YunxiNeural": "男声·云希（年轻阳光）", "zh-CN-YunxiaNeural": "男声·云夏（少年）",
    "zh-CN-XiaoxiaoNeural": "女声·晓晓（温暖新闻）", "zh-CN-XiaoyiNeural": "女声·晓依（活泼）",
}
MARK_CN = {"none": "不标记·整页原样", "line": "下划线", "box": "高亮框", "zoom": "高亮框＋放大"}


def mmss(x):
    return "%d:%04.1f" % (int(x // 60), x % 60)


def ms(x):
    return "%d分%04.1f秒" % (int(x // 60), x % 60)


def main():
    t = json.load(open(os.path.join(ROOT, "timing2.json"), encoding="utf-8"))
    pages = t["pages"]
    titles = getattr(cm, "TITLES", {})
    name = getattr(cm, "NAME", "项目")
    n_cues = sum(len(p["cues"]) for p in pages)
    marks = [c["m"] for p in pages for c in p["cues"]]

    L = ["# %s —— 讲解录屏 对照稿" % name, ""]
    L.append("源文件：%s（%d 页 / %d 个讲解单元）" % (getattr(cm, "SRCNAME", "原 PPT"), len(pages), n_cues))
    style = getattr(cm, "NARRATION_STYLE", None)
    if isinstance(style, dict) and style:
        L.append("讲解风格：%s；受众：%s；幽默：%s；举例：%s；补充要求：%s"
                 % (style.get("name") or style.get("id") or "未记录",
                    style.get("audience") or "未记录", style.get("humor") or "未记录",
                    style.get("examples") or "未记录", style.get("requirements") or "无"))
    L.append("配音：普通话 %s（%s），语速 %s；每页讲完留 %.1f 秒再翻页"
             % (VOICE_CN.get(t["voice"], "自定义音色"), t["voice"], t["rate"], t.get("pause", 1.0)))
    L.append("画面：1080p（1920×1080，30fps，H.264＋AAC）。讲到哪一段就标记那一段、其余部分轻轻压暗——"
             "不标记 %d 段 / 下划线 %d 段 / 高亮框 %d 段 / 高亮＋放大 %d 段；"
             "标记在讲出新句前约 0.4 秒开始渐变。"
             % (marks.count("none"), marks.count("line"), marks.count("box"), marks.count("zoom")))
    L.append("标记规则：首页、末页与每页开头“这页讲什么”的句子不标记；说明行/提示行用下划线；"
             "较宽的通栏用高亮框；较小的卡片、图、流程小块自动放大。")
    srt_name = os.environ.get("SRT_NAME", "subtitles.srt")
    L.append("字幕：外挂 %s（未烧入画面，播放器可自己开关）" % srt_name
             if os.environ.get("SUBTITLES", "1") != "0" else "字幕：本次未生成")
    L.append("总时长：%s（%.1f 秒）" % (ms(t["total"]), t["total"]))
    L.append("")
    L.append("> 页面顺序、文字、图片、版式取自原 PPT，逐页导出 4K 后按配音实际时长自动翻页；"
             "原动画未逐帧还原，统一以完整页面呈现。")
    L.append("")
    L.append("## 一、总览：页码—时长对照")
    L.append("")
    L.append("| 页码 | 页面标题 | 讲解单元 | 字数 | 本页时长 | 起始 | 累计 |")
    L.append("|---|---|---|---|---|---|---|")
    cur = 0.0
    for p in pages:
        ch = sum(len(c["t"]) for c in p["cues"])
        L.append("| %d | %s | %d 段 | %d | %s | %s | %s |"
                 % (p["page"], titles.get(p["page"], p["cues"][0]["t"][:18]), len(p["cues"]), ch,
                    ms(p["dur"]), ms(cur), ms(cur + p["dur"])))
        cur += p["dur"]
    L.append("")
    L.append("合计 **%s**" % ms(cur))
    L.append("")
    L.append("## 二、逐句对照：时间轴 — 画面标记 — 讲稿")
    L.append("")
    for p in pages:
        start = sum(q["dur"] for q in pages if q["page"] < p["page"])
        L.append("### 第%d页　%s　（本页 %s，起 %s）"
                 % (p["page"], titles.get(p["page"], ""), ms(p["dur"]), ms(start)))
        L.append("")
        L.append("| # | 时间轴 | 本句时长 | 画面标记 | 讲稿 |")
        L.append("|---|---|---|---|---|")
        for c in p["cues"]:
            L.append("| %d.%d | %s–%s | %.1fs | %s（%s） | %s |"
                     % (p["page"], c["i"] + 1, mmss(start + c["s"]), mmss(start + c["e"]),
                        c["e"] - c["s"], c["lb"], MARK_CN.get(c["m"], c["m"]), c["t"]))
        L.append("")
    L.append("## 三、讲稿全文（可直接照读）")
    L.append("")
    for p in pages:
        L.append("**第%d页　%s**" % (p["page"], titles.get(p["page"], "")))
        L.append("")
        L.append("".join(c["t"] for c in p["cues"]))
        L.append("")

    sheet = output_path(os.path.join(OUT, os.environ.get("SHEET_NAME", "%s_讲稿与时长对照稿.md" % name)))
    os.makedirs(os.path.dirname(sheet), exist_ok=True)
    open(sheet, "w", encoding="utf-8-sig").write("\n".join(L))
    print("sheet ->", sheet, os.path.getsize(sheet))

    s = os.path.join(ROOT, "out2", "subtitles.srt")
    if os.path.exists(s):
        dst = output_path(os.path.join(OUT, os.environ.get("SRT_NAME", "subtitles.srt")))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.abspath(s) != dst:
            shutil.copy2(s, dst)
        print("srt   ->", dst, os.path.getsize(s))
    vids = sorted([f for f in os.listdir(os.path.join(ROOT, "out2")) if f.endswith(".mp4")],
                  key=lambda x: os.path.getmtime(os.path.join(ROOT, "out2", x)))
    if vids:
        s = os.path.join(ROOT, "out2", vids[-1])
        if os.path.abspath(s) != os.path.join(OUT, vids[-1]):
            shutil.copy2(s, os.path.join(OUT, vids[-1]))
        print("video ->", os.path.join(OUT, vids[-1]), os.path.getsize(s))
    else:
        print("（还没有成片）")


if __name__ == "__main__":
    main()
