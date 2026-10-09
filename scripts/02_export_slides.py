# -*- coding: utf-8 -*-
"""把每页导出成 4K（3840×2160）PNG，并统一命名为 slides_png_4k/slideNN.png。

为什么是 4K：讲解到小区域时会自动放大，源图若只有 1920 宽，放大后文字发虚。
本脚本宽度写死 3840（输出成片仍是 1080p，不浪费）。

用法：
    PPTX="D:/deck.pptx" python scripts/02_export_slides.py
    python scripts/02_export_slides.py --pptx deck.pptx --root project1

导出方式（自动选择）：
    Windows + Microsoft Office → PowerPoint COM（保真最高，不弹窗）
    其他情况                    → LibreOffice: soffice --convert-to pdf + pdftoppm
"""
import sys
sys.dont_write_bytecode = True
from output_paths import build_root, delivery_root, output_path, MODEL_CACHE

import argparse, glob, os, re, shutil, subprocess, sys

W, H = 3840, 2160


def normalize(raw_dir, out_dir):
    """把导出结果统一改名成 slideNN.png 并按页码排序"""
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    files = list(dict.fromkeys(glob.glob(os.path.join(raw_dir, "*.PNG")) + glob.glob(os.path.join(raw_dir, "*.png"))))
    if not files:
        sys.exit("没有导出任何图片，请检查上面的报错")

    def key(f):
        m = re.findall(r"\d+", os.path.basename(f))
        return int(m[-1]) if m else 0
    for i, f in enumerate(sorted(files, key=key), 1):
        dst = os.path.join(out_dir, "slide%02d.png" % i)
        shutil.copy2(f, dst)
    print("源图 %d 张 → %s" % (len(files), out_dir))


def export_com(src, raw_dir):
    import pythoncom, win32com.client as win32
    pythoncom.CoInitialize()
    app = pres = None
    try:
        app = win32.DispatchEx("PowerPoint.Application")
        pres = app.Presentations.Open(src, ReadOnly=True, WithWindow=False)   # 不弹窗
        print("打开成功，共 %d 页" % pres.Slides.Count)
        pres.Export(raw_dir, "PNG", W, H)
        print("导出完成")
    finally:
        try:
            if pres is not None:
                pres.Close()
        except Exception as e:
            print("关闭演示文稿出错：", e)
        try:
            if app is not None:
                app.Quit()
        except Exception as e:
            print("退出 PowerPoint 出错：", e)
        pythoncom.CoUninitialize()


def export_libreoffice(src, raw_dir):
    for exe in ("soffice", "libreoffice"):
        if shutil.which(exe):
            break
    else:
        sys.exit("既没有 PowerPoint COM（非 Windows 或未装 Office），也没有 LibreOffice。\n"
                 "请安装 LibreOffice（macOS/Ubuntu: sudo apt install libreoffice），并确保 pdftoppm 可用。")
    pdf = os.path.join(raw_dir, os.path.splitext(os.path.basename(src))[0] + ".pdf")
    subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", raw_dir, src], check=True)
    if not shutil.which("pdftoppm"):
        sys.exit("需要 poppler-utils 提供 pdftoppm（Ubuntu: sudo apt install poppler-utils；macOS: brew install poppler）")
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(W), "-scale-to-y", str(H),
                    pdf, os.path.join(raw_dir, "幻灯片")], check=True)
    print("LibreOffice/pdftoppm 导出完成")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", default=os.environ.get("PPTX"), help="源 .pptx（或环境变量 PPTX）")
    ap.add_argument("--root", default=build_root(), help="工作目录（限 results 内；相对路径基于 results）")
    a = ap.parse_args()
    if not a.pptx or not os.path.exists(a.pptx):
        sys.exit("请用 --pptx 或环境变量 PPTX 指定存在的 .pptx")

    a.root = output_path(a.root)
    raw = os.path.join(a.root, "png_raw")
    out = os.path.join(a.root, "slides_png_4k")
    os.makedirs(raw, exist_ok=True)
    if os.name == "nt":
        try:
            export_com(os.path.abspath(a.pptx), raw)
        except Exception as e:
            print("PowerPoint COM 导出失败：%s\n改用 LibreOffice 试一次" % e)
            export_libreoffice(os.path.abspath(a.pptx), raw)
    else:
        export_libreoffice(os.path.abspath(a.pptx), raw)
    normalize(raw, out)
    print("完成：4K 页面图在", out)
