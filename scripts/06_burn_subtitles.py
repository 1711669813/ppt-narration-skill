# -*- coding: utf-8 -*-
"""扩展（可选）：把外挂字幕烧进画面。

默认交付是外挂 .srt（播放器自己开关、画质无损）；只有用户明确要"画面里带字幕"时才用本脚本。
烧入是二次编码，会略微损失画质，所以默认**另存为副本**，不覆盖原片。

用法：
    python scripts/06_burn_subtitles.py --video 成片.mp4 [--srt 字幕.srt] [--out 输出.mp4]
                                        [--font-size 44] [--margin 28] [--crf 18]

字体：Windows 用微软雅黑、macOS 用苹方、Linux 用 Noto Sans CJK（自动查找，可用 --font 指定）。
样式：白字 + 半透明黑底 + 底部安全边距，最多两行（.srt 里已经是两句一行）。
"""
import sys
sys.dont_write_bytecode = True
from output_paths import build_root, delivery_root, output_path, MODEL_CACHE

import argparse, os, shutil, subprocess, sys

FONTS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
         "/System/Library/Fonts/PingFang.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
         "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]


def find_font(explicit):
    if explicit:
        if not os.path.exists(explicit):
            sys.exit("指定的字体不存在：%s" % explicit)
        return explicit
    for f in FONTS:
        if os.path.exists(f):
            return f
    sys.exit("没找到中文字体，请用 --font 指定（例如 C:\\Windows\\Fonts\\msyh.ttc）")


def esc(path):
    """ffmpeg 滤镜里的路径转义"""
    return path.replace("\\", "/").replace(":", "\\:")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", default=None, help="默认取成片同目录的 subtitles.srt")
    ap.add_argument("--out", default=None, help="默认 results/<原文件名>_带字幕.mp4；相对路径基于 results")
    ap.add_argument("--font", default=None)
    ap.add_argument("--font-size", type=int, default=44)
    ap.add_argument("--margin", type=int, default=28, help="字幕距底部像素")
    ap.add_argument("--crf", type=int, default=18, help="画质：18 高、20 中、23 低")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的输出文件")
    a = ap.parse_args()

    if not os.path.exists(a.video):
        sys.exit("找不到成片：%s" % a.video)
    srt = a.srt or os.path.join(os.path.dirname(os.path.abspath(a.video)), "subtitles.srt")
    if not os.path.exists(srt):
        sys.exit("找不到字幕：%s（先跑 03_build_video.py，或用 --srt 指定）" % srt)
    out = output_path(a.out, os.path.join(delivery_root(), os.path.splitext(os.path.basename(a.video))[0] + "_带字幕.mp4"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and not a.force:
        sys.exit("输出已存在：%s（加 --force 覆盖）" % out)
    font = find_font(a.font)

    style = ("FontName=%s,FontSize=%d,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
             "BackColour=&H80000000,BorderStyle=4,Outline=1,Shadow=0,Alignment=2,MarginV=%d"
             % (os.path.splitext(os.path.basename(font))[0], a.font_size, a.margin))
    vf = "subtitles=filename='%s':fontsdir='%s':force_style='%s'" % (
        esc(os.path.abspath(srt)), esc(os.path.dirname(os.path.abspath(font))), style)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", a.video, "-vf", vf,
           "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-g", "60",
           "-c:a", "copy", "-movflags", "+faststart", out]
    print("字体：%s" % font)
    print("命令：%s" % " ".join(cmd))
    p = subprocess.run(cmd)
    if p.returncode or not os.path.exists(out):
        sys.exit("烧字幕失败（退出码 %s）。若提示找不到字幕滤镜，请用带 libass 的 ffmpeg 构建。" % p.returncode)
    print("完成：%s（%.1f MB）" % (out, os.path.getsize(out) / 1e6))
    print("原片未被修改：%s" % a.video)
    _ = shutil  # 保持导入（部分环境下用于后续扩展）


if __name__ == "__main__":
    main()
