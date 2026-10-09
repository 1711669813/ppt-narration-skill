# -*- coding: utf-8 -*-
"""Dump every shape with ABSOLUTE bounding box (groups resolved) as fractions of the slide.

用法：
    PPTX="D:/deck.pptx" python scripts/01_extract_ppt.py
    python scripts/01_extract_ppt.py --pptx deck.pptx --out shapes_geom.json

产物：shapes_geom.json（每页每个形状的名称/类型/归一化包围盒/文字/备注；表格附带每一行的矩形），
同时打印一张人可读的坐标表——写 cue 时照着挑区域。
"""
import sys
sys.dont_write_bytecode = True
from output_paths import build_root, delivery_root, output_path, MODEL_CACHE

import argparse, json, os, sys
from pptx import Presentation

ap = argparse.ArgumentParser()
ap.add_argument("--pptx", default=os.environ.get("PPTX"), help="源 .pptx（或环境变量 PPTX）")
ap.add_argument("--out", default=None, help="输出 json（默认 <BUILD_ROOT>/shapes_geom.json）")
a = ap.parse_args()
if not a.pptx or not os.path.exists(a.pptx):
    sys.exit("请用 --pptx 或环境变量 PPTX 指定存在的 .pptx")
SRC = a.pptx
OUT = output_path(a.out, os.path.join(build_root(), "shapes_geom.json"))
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)

prs = Presentation(SRC)
SW, SH = prs.slide_width, prs.slide_height


def xfrm(sh):
    """absolute (x, y, w, h) in EMU, resolving group child offsets"""
    return sh.left, sh.top, sh.width, sh.height


def walk(shapes, res, parent=None):
    for sh in shapes:
        try:
            x, y, w, h = xfrm(sh)
        except Exception:
            x = y = w = h = None
        if parent is not None and x is not None:
            px, py, pw, ph, cx, cy, cw, ch = parent
            if cw and ch:
                x = px + (x - cx) * pw / cw
                y = py + (y - cy) * ph / ch
                w = w * pw / cw
                h = h * ph / ch
        entry = {"name": sh.name, "kind": "group" if sh.shape_type == 6 else str(sh.shape_type)}
        if None not in (x, y, w, h):
            entry["rect"] = [round(x / SW, 4), round(y / SH, 4),
                             round((x + w) / SW, 4), round((y + h) / SH, 4)]
        txt = ""
        if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
            txt = " / ".join(p.text.strip() for p in sh.text_frame.paragraphs if p.text.strip())
        if getattr(sh, "has_table", False) and sh.has_table:
            txt = "表格: " + " | ".join(c.text.strip().replace("\n", " ") for c in sh.table.rows[0].cells)
            rows, acc = [], y
            for r in sh.table.rows:            # 每一行的矩形（写 cue 时按行高亮用；表头是第 0 行）
                rows.append([round(x / SW, 4), round(acc / SH, 4),
                             round((x + w) / SW, 4), round((acc + r.height) / SH, 4)])
                acc += r.height
            entry["rows"] = rows
        entry["text"] = txt[:70]
        res.append(entry)
        if sh.shape_type == 6:
            el = sh._element
            g = el.grpSpPr.getchildren()[0] if el.grpSpPr is not None else None
            ch_off = ch_ext = None
            xf = None
            for child in el.grpSpPr:
                tag = child.tag.split("}")[-1]
                if tag == "xfrm":
                    xf = child
            if xf is not None:
                for child in xf:
                    tag = child.tag.split("}")[-1]
                    if tag == "chOff":
                        ch_off = (int(child.get("x")), int(child.get("y")))
                    if tag == "chExt":
                        ch_ext = (int(child.get("cx")), int(child.get("cy")))
            egg = (x, y, w, h, ch_off[0], ch_off[1], ch_ext[0], ch_ext[1]) if (ch_off and ch_ext and x is not None) else parent
            walk(sh.shapes, res, egg)


data = []
for i, slide in enumerate(prs.slides, 1):
    res = []
    walk(slide.shapes, res)
    notes = ""
    if slide.has_notes_slide:
        notes = slide.notes_slide.notes_text_frame.text.strip()
    data.append({"page": i, "shapes": res, "notes": notes})

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

for s in data:
    print("=" * 78)
    print("PAGE", s["page"])
    for sh in s["shapes"]:
        r = sh.get("rect")
        rs = ("[%.3f,%.3f,%.3f,%.3f]" % tuple(r)) if r else "[-]"
        print(" %-26s %-10s %-28s %s" % (sh["name"], sh["kind"], rs, sh["text"]))
print("written", OUT)
