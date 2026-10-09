# -*- coding: utf-8 -*-
"""环境自检：把"出片所需的一切"逐项验一遍，缺什么直接说清楚怎么补。

    python scripts/00_check_env.py
"""
import sys
sys.dont_write_bytecode = True
from output_paths import build_root, delivery_root, output_path, MODEL_CACHE

import os, shutil, subprocess, sys

OK, WARN, BAD = "[ok]  ", "[注意]", "[缺失]"
problems = []


def say(tag, msg):
    print("%s %s" % (tag, msg))


def check_python():
    say(OK, "python: %s" % sys.executable)
    if sys.version_info < (3, 9):
        say(BAD, "需要 Python 3.9+，当前 %d.%d" % sys.version_info[:2]); problems.append("python")
    else:
        say(OK, "版本 %d.%d.%d" % sys.version_info[:3])


def check_pip_pkgs():
    need = [("pptx", "python-pptx", True), ("edge_tts", "edge-tts", True),
            ("PIL", "pillow", True), ("numpy", "numpy", True)]
    if os.name == "nt":
        need.append(("win32com", "pywin32", True))
    opt = [("mutagen", "mutagen"), ("faster_whisper", "faster-whisper")]
    for mod, pkg, required in need:
        try:
            __import__(mod); say(OK, "import %-12s (%s)" % (mod, pkg))
        except Exception as e:
            if required:
                say(BAD, "import %-12s 失败：%s → pip install %s" % (mod, e, pkg)); problems.append(pkg)
            else:
                say(WARN, "可选 %-12s 未装（%s）" % (mod, pkg))
    for mod, pkg in opt:
        try:
            __import__(mod); say(OK, "可选 %-12s (%s)" % (mod, pkg))
        except Exception:
            say(WARN, "可选 %-12s 未装：pip install %s" % (mod, pkg))


def check_bin(name):
    p = shutil.which(name)
    if p:
        try:
            out = subprocess.run([name, "-version"], capture_output=True, text=True,
                                 timeout=20).stdout.splitlines()[0]
        except Exception:
            out = p
        say(OK, "%-8s %s" % (name, out))
    else:
        say(BAD, "%-8s 不在 PATH —— 合成/取时长/抽帧都要用它" % name)
        problems.append(name)


def check_office():
    if os.name != "nt":
        say(WARN, "非 Windows：用 LibreOffice 导页（soffice %s）"
            % ("已就绪" if shutil.which("soffice") else "未安装"))
        say(WARN, "pdftoppm %s" % ("已就绪" if shutil.which("pdftoppm") else "未安装（建议装 poppler-utils）"))
        return
    try:
        import win32com.client as w
        app = w.DispatchEx("PowerPoint.Application")
        ver = app.Version
        app.Quit()
        say(OK, "PowerPoint COM %s（导 4K 页面图用）" % ver)
    except Exception as e:
        say(BAD, "PowerPoint COM 不可用：%s → 装/激活 Microsoft Office，或改用 LibreOffice" % e)
        problems.append("PowerPoint/Office")


def check_fonts():
    cands = [r"C:\Windows\Fonts\msyh.ttc", "/System/Library/Fonts/PingFang.ttc",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]
    hit = [c for c in cands if os.path.exists(c)]
    if hit:
        say(OK, "中文字体（烧字幕时用）：%s" % hit[0])
    else:
        say(WARN, "未找到常见中文字体；只用外挂 .srt 时无影响")


def check_tts():
    try:
        import asyncio, edge_tts
        vs = asyncio.run(edge_tts.list_voices())
        zh = [v["ShortName"] for v in vs if v["Locale"] == "zh-CN"]
        say(OK, "edge-tts 可联网，中文音色 %d 个，例如 %s" % (len(zh), ", ".join(zh[:3])))
    except Exception as e:
        say(BAD, "edge-tts 连不上：%s → 配音需要联网；公司网络可能拦 websocket，换网络试" % e)
        problems.append("edge-tts 网络")


def check_workdir():
    root = build_root()
    try:
        for d in ("slides_png_4k", os.path.join("out2", "audio"), os.path.join("out2", "frames")):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        say(OK, "工作目录可写：%s" % root)
    except Exception as e:
        say(BAD, "工作目录不可写：%s" % e); problems.append("BUILD_ROOT")


if __name__ == "__main__":
    print("== PPT 讲解录屏生成包 · 环境自检 ==")
    check_python()
    check_pip_pkgs()
    print("-- 外部程序 --")
    for b in ("ffmpeg", "ffprobe"):
        check_bin(b)
    check_office()
    check_fonts()
    print("-- 配音服务 --")
    check_tts()
    print("-- 工作目录 --")
    check_workdir()
    print()
    if problems:
        print("结论：还有 %d 项要处理 → %s" % (len(problems), ", ".join(problems)))
        sys.exit(1)
    print("结论：环境就绪，可以开始。")
