# -*- coding: utf-8 -*-
"""成片验收：容器参数 / 逐句帧对齐 / 放大几何（独立于渲染代码）/ 黑边 / 可选 ASR 抽查。

用法（在 BUILD_ROOT 下跑，或用环境变量指定）：
    python scripts/05_verify.py                       # 基本验收
    python scripts/05_verify.py --max 600             # 时长上限（秒），默认 600
    python scripts/05_verify.py --asr small --asr-n 4 # 追加 ASR 抽查（需 faster-whisper）

环境变量：
    BUILD_ROOT   工作目录（默认包内 results），需要 timing2.json、slides_png_4k/、以及成片
    VIDEO        成片路径（默认自动在 BUILD_ROOT/out2 下找 *1080p*.mp4）
"""
import sys
sys.dont_write_bytecode = True
from output_paths import build_root, delivery_root, output_path, MODEL_CACHE

import argparse, glob, json, os, re, subprocess, sys

ROOT = build_root()
TMP = os.path.join(ROOT, "out2", "verify")
SW, SH, W, H = 3840, 2160, 1920, 1080
CJK = re.compile(r"[\u3400-\u9fff]")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def find_video():
    if os.environ.get("VIDEO"):
        return os.environ["VIDEO"]
    hits = sorted(glob.glob(os.path.join(ROOT, "out2", "*.mp4")), key=os.path.getmtime)
    return hits[-1] if hits else None


def probe(video):
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", video])
    if p.returncode:
        sys.exit("ffprobe 失败：" + p.stderr.strip())
    j = json.loads(p.stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"]
    a = [s for s in j["streams"] if s["codec_type"] == "audio"]
    print("== 容器 ==")
    print("文件 %s（%.1f MB）" % (video, os.path.getsize(video) / 1e6))
    if v:
        s = v[0]
        fr = s.get("avg_frame_rate", "0/1").split("/")
        fps = float(fr[0]) / float(fr[1]) if len(fr) == 2 and float(fr[1]) else 0
        print("视频 %s %dx%d %.2ffps" % (s["codec_name"], s["width"], s["height"], fps))
    else:
        print("[缺失] 没有视频流")
    print("音频 %s" % (a[0]["codec_name"] if a else "[缺失] 没有音轨"))
    dur = float(j["format"]["duration"])
    print("时长 %.2fs = %d:%05.2f" % (dur, dur // 60, dur % 60))
    return dur, bool(v), bool(a)


def volume(video):
    p = run(["ffmpeg", "-hide_banner", "-i", video, "-af", "volumedetect", "-f", "null", "-"])
    mm = re.search(r"mean_volume: ([-\d.]+) dB", p.stderr)
    mx = re.search(r"max_volume: ([-\d.]+) dB", p.stderr)
    if mm and mx:
        print("音量 mean %s dB / max %s dB" % (mm.group(1), mx.group(1)))
        if float(mx.group(1)) < -30:
            print("[缺失] 音量过低，检查配音是否成功")


def frame_from(video, t, path):
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", "%.3f" % t,
         "-i", video, "-frames:v", "1", path])


def cue_checks(video, plan):
    import numpy as np
    from PIL import Image
    os.makedirs(TMP, exist_ok=True)
    # absolute page starts
    starts, acc = {}, 0.0
    for p in plan:
        starts[p["page"]] = acc
        acc += p["dur"]
    print("\n== 逐句帧对齐（本文件 vs 渲染时保存的帧）==")
    worst, worst_at, n = 0.0, "", 0
    for p in plan:
        for c in p["cues"]:
            ref = os.path.join(ROOT, "out2", "frames", "p%02d_c%02d_hold.jpg" % (p["page"], c["i"]))
            if not os.path.exists(ref):
                continue
            f = os.path.join(TMP, "f.png")
            frame_from(video, starts[p["page"]] + (c["s"] + c["e"]) / 2, f)
            a = np.asarray(Image.open(f).convert("RGB"), dtype=np.int16)
            b = np.asarray(Image.open(ref).convert("RGB"), dtype=np.int16)
            if a.shape != b.shape:
                print("[缺失] 帧尺寸不一致 p%d.%d" % (p["page"], c["i"] + 1)); continue
            d = float(np.abs(a - b).mean()); n += 1
            if d > worst:
                worst, worst_at = d, "p%d.%d %s" % (p["page"], c["i"] + 1, c["lb"])
    if n == 0:
        print("（渲染帧已清理，跳过；如需更严的核对请保留 out2/frames）")
    else:
        print("比对 %d 个 cue，最大均值差 %.2f（阈值 3）→ %s"
              % (n, worst, "通过" if worst < 3 else "[失败] 见 " + worst_at))


def geometry_check(video, plan, sample=8):
    import numpy as np
    from PIL import Image
    os.makedirs(TMP, exist_ok=True)
    starts, acc = {}, 0.0
    for p in plan:
        starts[p["page"]] = acc
        acc += p["dur"]
    cands = [(p, c) for p in plan for c in p["cues"]
             if c["view"] != [0.0, 0.0, 1.0, 1.0] and os.path.exists(
                 os.path.join(ROOT, "slides_png_4k", "slide%02d.png" % p["page"]))]
    if not cands:
        print("\n== 放大几何 ==\n（没有放大句或缺少 4K 页面图，跳过）")
        return
    step = max(1, len(cands) // sample)
    print("\n== 放大几何（独立于渲染代码：纯 PIL 裁 4K 原图比对）==")
    print("page.cue  缩放   目标块差  黑边%  判定")
    badw, badb = 0.0, 0.0
    for p, c in cands[::step][:sample]:
        view = c["view"]
        img = Image.open(os.path.join(ROOT, "slides_png_4k", "slide%02d.png" % p["page"])).convert("RGB")
        box = (int(view[0] * SW), int(view[1] * SH), int(round(view[2] * SW)), int(round(view[3] * SH)))
        plain = img.crop(box).resize((W, H), Image.LANCZOS)
        f = os.path.join(TMP, "g.png")
        frame_from(video, starts[p["page"]] + (c["s"] + c["e"]) / 2, f)
        got = Image.open(f).convert("RGB")
        ga, pa = np.asarray(got, dtype=np.int16), np.asarray(plain, dtype=np.int16)
        vw = view[2] - view[0]
        r = c["r"][0] if c["r"] else [view[0], view[1], view[2], view[3]]
        x0 = int(max(0, (r[0] - view[0]) / vw * W + 12)); x1 = int(min(W, (r[2] - view[0]) / vw * W - 12))
        y0 = int(max(0, (r[1] - view[1]) / vw * H + 12)); y1 = int(min(H, (r[3] - view[1]) / vw * H - 12))
        if x1 - x0 < 20 or y1 - y0 < 20:
            x0, x1, y0, y1 = 0, W, 0, H
        d = float(np.abs(ga[y0:y1, x0:x1] - pa[y0:y1, x0:x1]).mean())
        black = float((ga.max(axis=2) < 16).mean()) * 100
        badw, badb = max(badw, d), max(badb, black)
        print("%4d.%-3d %.2fx %9.2f %5.2f%%  %s"
              % (p["page"], c["i"] + 1, 1.0 / vw, d, black, "ok" if d <= 22 and black <= 1.5 else "[失败]"))
    print("最差：目标块差 %.2f（阈值 22）、黑边 %.2f%%（阈值 1.5）→ %s"
          % (badw, badb, "通过" if badw <= 22 and badb <= 1.5 else "[失败] 画面被拉伸或越界"))


def asr_check(video, plan, model_size, n):
    import numpy as np
    from PIL import Image  # noqa: F401
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("\n== ASR 抽查 ==\n（未安装 faster-whisper，跳过：pip install faster-whisper）")
        return
    try:                       # 转写常输出繁体，比对前先归一化，否则覆盖率会被误判
        import zhconv

        def to_simp(s):
            return zhconv.convert(s, "zh-cn")
    except ImportError:
        def to_simp(s):
            return s

        print("（提示：装了 zhconv 会做繁简归一化，覆盖率更准：pip install zhconv）")
    model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=MODEL_CACHE)
    starts, acc = {}, 0.0
    for p in plan:
        starts[p["page"]] = acc
        acc += p["dur"]
    flat = [(p, c) for p in plan for c in p["cues"] if c["m"] != "none"]
    if not flat:
        return
    step = max(1, len(flat) // n)
    print("\n== ASR 抽查：标记与台词是否一致 ==")
    for p, c in flat[::step][:n]:
        t0 = starts[p["page"]] + c["s"] - 0.2
        wav = os.path.join(TMP, "asr.wav")
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", "%.3f" % max(0, t0),
             "-t", "%.3f" % (c["e"] - c["s"] + 0.4), "-i", video, "-ac", "1", "-ar", "16000", wav])
        segs, _ = model.transcribe(wav, language="zh")
        got = CJK.findall(to_simp("".join(s.text for s in segs)))
        got = "".join(got)
        cue = "".join(CJK.findall(c["t"]))
        shingles = {"".join(cue[i:i + 4]) for i in range(max(1, len(cue) - 3))}
        hit = sum(1 for s in shingles if s in got) / max(1, len(shingles)) * 100
        print("p%d.%-3d %-16s 覆盖 %5.1f%%  %s" % (p["page"], c["i"] + 1, c["lb"][:16], hit,
              "ok" if hit >= 40 else "[可疑] 去听一下这段"))
        print("       ASR：%s" % got[:60])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=float, default=600, help="时长上限（秒），默认 600")
    ap.add_argument("--asr", default=None, help="跑 ASR 抽查，给模型名：tiny/base/small")
    ap.add_argument("--asr-n", type=int, default=4, help="ASR 抽查段数")
    a = ap.parse_args()

    video = find_video()
    if not video:
        sys.exit("找不到成片，请设 VIDEO 或把成片放到 %s/out2/ 下" % ROOT)
    tj = os.path.join(ROOT, "timing2.json")
    if not os.path.exists(tj):
        sys.exit("找不到 %s（由 03_build_video.py 生成）" % tj)
    plan = json.load(open(tj, encoding="utf-8"))["pages"]

    dur, has_v, has_a = probe(video)
    if not has_v or not has_a:
        print("[失败] 缺视频流或音轨")
    if dur > a.max:
        print("[失败] 时长 %.1fs 超过上限 %.0fs" % (dur, a.max))
    else:
        print("时长在上限内（%.0fs）" % a.max)
    volume(video)
    cue_checks(video, plan)
    geometry_check(video, plan)
    if a.asr:
        asr_check(video, plan, a.asr, a.asr_n)
    print("\n完成。逐句对照稿见 scripts/04_make_sheet.py 的产物。")
