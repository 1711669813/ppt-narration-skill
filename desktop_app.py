"""GUI entry point and isolated worker entry point for PyInstaller."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading


def worker():
    # Secrets travel via stdin only, never via process arguments or task files.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    config = json.loads(sys.stdin.readline())
    if os.name == "nt":
        original_popen = subprocess.Popen
        class HiddenPopen(original_popen):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
                super().__init__(*args, **kwargs)
        subprocess.Popen = HiddenPopen
    try:
        from desktop.pipeline import run
        root = run(config)
        print("@@RESULT@@" + json.dumps({"ok": True, "root": str(root)}, ensure_ascii=False), flush=True)
        return 0
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code in (0, None):
            message = "任务提前退出。"
        else:
            message = str(exc)
        secret = config.get("api_key", "")
        if secret:
            message = message.replace(secret, "[隐藏密钥]")
        print("@@RESULT@@" + json.dumps({"ok": False, "error": message}, ensure_ascii=False), flush=True)
        return 1


def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from desktop.pipeline import STYLES, VOICES, endpoint

    if os.name == "nt" and getattr(sys, "frozen", False):
        import ctypes
        processes = (ctypes.c_ulong * 2)()
        if ctypes.windll.kernel32.GetConsoleProcessList(processes, 2) == 1:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = tk.Tk()
    app.title("PPT 智能讲解视频生成器 · v0.1.0")
    app.geometry("920x860")
    app.minsize(830, 790)
    app.configure(bg="#f3f6fb")
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TFrame", background="#f3f6fb")
    style.configure("TLabel", background="#f3f6fb", font=("Microsoft YaHei UI", 10))
    style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=7)
    style.configure("Title.TLabel", font=("Microsoft YaHei UI", 22, "bold"), foreground="#172b4d")
    style.configure("Hint.TLabel", foreground="#5b6b82", font=("Microsoft YaHei UI", 9))
    style.configure("Accent.TButton", background="#215be3", foreground="white", padding=10)
    style.map("Accent.TButton", background=[("active", "#1948bd"), ("disabled", "#879ab8")])
    panel = ttk.Frame(app, padding=24)
    panel.pack(fill="both", expand=True)
    ttk.Label(panel, text="把 PPT 变成讲解视频", style="Title.TLabel").pack(anchor="w")
    ttk.Label(panel, text="导入演示文稿，选择讲解方式，自动生成配音、同步高亮与字幕。", style="Hint.TLabel").pack(anchor="w", pady=(4, 15))
    form = ttk.Frame(panel)
    form.pack(fill="x")
    form.columnconfigure(1, weight=1)
    variables = {k: tk.StringVar(value=v) for k, v in {
        "pptx": "", "base_url": "", "api_key": "", "model": "", "style": "",
        "voice": next(iter(VOICES)), "rate": "+6%", "minutes": "10",
        "output": str(Path.home() / "Documents" / "PPT Narration")}.items()}
    widgets = []
    config_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PPTNarration"
    try:
        saved = json.loads((config_dir / "preferences.json").read_text(encoding="utf-8"))
        for key in ("base_url", "model", "output"):
            if isinstance(saved.get(key), str):
                variables[key].set(saved[key])
    except (OSError, ValueError):
        pass

    def row(index, label, key, values=None, choose=None, secret=False):
        ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", pady=5, padx=(0, 15))
        if values:
            entry = ttk.Combobox(form, textvariable=variables[key], values=values, state="readonly", font=("Microsoft YaHei UI", 10))
        else:
            entry = ttk.Entry(form, textvariable=variables[key], show="●" if secret else "", font=("Microsoft YaHei UI", 10))
        entry.grid(row=index, column=1, sticky="ew", pady=5, ipady=4)
        widgets.append((entry, "readonly" if values else "normal"))
        if choose:
            button = ttk.Button(form, text="浏览…", command=choose)
            button.grid(row=index, column=2, padx=(8, 0))
            widgets.append((button, "normal"))

    def choose_ppt():
        path = filedialog.askopenfilename(filetypes=[("PowerPoint", "*.pptx")])
        if path:
            variables["pptx"].set(path)

    def choose_output():
        path = filedialog.askdirectory()
        if path:
            variables["output"].set(path)

    row(0, "PPT 文件", "pptx", choose=choose_ppt)
    row(1, "API 地址", "base_url")
    row(2, "API Key", "api_key", secret=True)
    row(3, "模型名称", "model")
    ttk.Label(form, text="使用兼容 Chat Completions 的接口；地址通常为 https://服务商地址/v1。密钥只保存在本次运行内存中。", style="Hint.TLabel", wraplength=750).grid(row=4, column=0, columnspan=3, sticky="w", pady=(2, 8))
    row(5, "讲解风格", "style", values=STYLES)
    row(6, "配音音色", "voice", values=list(VOICES))
    row(7, "配音语速", "rate", values=["-5%", "+0%", "+6%", "+8%", "+12%"])
    row(8, "时长上限 / 分钟", "minutes")
    row(9, "保存位置", "output", choose=choose_output)
    ttk.Label(panel, text="补充要求（可选）：受众、侧重点或自定义风格", style="Hint.TLabel").pack(anchor="w", pady=(10, 4))
    instructions = tk.Text(panel, height=2, font=("Microsoft YaHei UI", 10), relief="solid", bd=1, wrap="word")
    instructions.pack(fill="x")
    checks = ttk.Frame(panel)
    checks.pack(fill="x", pady=(10, 5))
    vision = tk.BooleanVar(value=False)
    subtitles = tk.BooleanVar(value=True)
    vision_check = ttk.Checkbutton(checks, text="将页面图片发送给 AI（需视觉模型，适合图表较多的 PPT）", variable=vision)
    vision_check.pack(side="left")
    sub_check = ttk.Checkbutton(checks, text="生成外挂字幕", variable=subtitles)
    sub_check.pack(side="right")
    ttk.Label(panel, text="需要联网及 PowerPoint / LibreOffice。讲稿生成会向所填 AI 服务发送 PPT 内容；配音会发送讲稿。", style="Hint.TLabel", wraplength=850).pack(anchor="w", pady=(4, 10))
    buttons = ttk.Frame(panel)
    buttons.pack(fill="x")
    status = tk.StringVar(value="请选择本次讲解风格，然后开始生成。")
    ttk.Label(panel, textvariable=status, style="Hint.TLabel", wraplength=850).pack(anchor="w", pady=(10, 5))
    progress = ttk.Progressbar(panel, mode="indeterminate")
    progress.pack(fill="x", pady=(0, 8))
    log = tk.Text(panel, height=7, font=("Consolas", 10), bg="#101d32", fg="#d7e6fa", wrap="word", state="disabled", relief="flat", padx=10, pady=8)
    log.pack(fill="both", expand=True)
    messages = queue.Queue()
    state = {"process": None, "running": False, "root": None}

    def busy(value):
        state["running"] = value
        for widget, normal in widgets:
            widget.configure(state="disabled" if value else normal)
        for widget in (vision_check, sub_check, instructions):
            widget.configure(state="disabled" if value else "normal")
        start.configure(state="disabled" if value else "normal")
        cancel.configure(state="normal" if value else "disabled")
        if value:
            progress.start(15)
        else:
            progress.stop()

    def reader(config):
        command = [sys.executable, "--worker"] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve()), "--worker"]
        try:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            state["process"] = proc
            if not state["running"]:
                proc.terminate()
                messages.put(("result", {"ok": False, "error": "任务已停止。"}))
                return
            proc.stdin.write(json.dumps(config, ensure_ascii=False) + "\n")
            proc.stdin.close()
            got_result = False
            for line in proc.stdout:
                line = line.rstrip()
                if line.startswith("@@RESULT@@"):
                    messages.put(("result", json.loads(line[len("@@RESULT@@"):])) )
                    got_result = True
                else:
                    messages.put(("log", line.replace(config["api_key"], "[隐藏密钥]")))
            code = proc.wait()
            if not got_result:
                messages.put(("result", {"ok": False, "error": "任务已停止。" if not state["running"] else "任务异常退出（%s）。" % code}))
        except Exception:
            messages.put(("result", {"ok": False, "error": "无法启动生成进程，请检查程序和保存目录。"}))
        finally:
            state["process"] = None

    def begin():
        try:
            config = {k: v.get().strip() for k, v in variables.items()}
            endpoint(config["base_url"])
            config["minutes"] = float(config["minutes"])
            if not 1 <= config["minutes"] <= 120:
                raise ValueError("时长上限应为 1–120 分钟。")
            if not Path(config["pptx"]).is_file() or Path(config["pptx"]).suffix.lower() != ".pptx":
                raise ValueError("请选择一个 .pptx 文件。")
            if not config["api_key"] or not config["model"]:
                raise ValueError("请填写 API Key 和模型名称。")
            if config["style"] not in STYLES:
                raise ValueError("请选择本次讲解风格。")
            if not config["output"]:
                raise ValueError("请选择保存位置。")
            config.update(voice=VOICES[config["voice"]], vision=vision.get(), subtitles=subtitles.get(),
                          instructions=instructions.get("1.0", "end").strip())
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "preferences.json").write_text(json.dumps({k: config[k] for k in
                ("base_url", "model", "output")}, ensure_ascii=False), encoding="utf-8")
        except (ValueError, OSError) as exc:
            messagebox.showerror("请检查配置", str(exc))
            return
        log.configure(state="normal")
        log.delete("1.0", "end")
        log.configure(state="disabled")
        state["root"] = None
        open_button.configure(state="disabled")
        busy(True)
        status.set("正在生成，请留意下方进度。")
        threading.Thread(target=reader, args=(config,), daemon=True).start()

    def stop():
        proc = state["process"]
        state["running"] = False
        if proc and proc.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                proc.terminate()
        status.set("已停止；已生成的中间文件保留在结果目录。")

    def open_output():
        path = state["root"]
        if path and os.name == "nt":
            os.startfile(path)

    def poll():
        while True:
            try:
                kind, data = messages.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                log.configure(state="normal")
                log.insert("end", data + "\n")
                log.see("end")
                log.configure(state="disabled")
                if data.startswith("输出目录："):
                    state["root"] = data.split("：", 1)[1]
                    open_button.configure(state="normal")
                if data.startswith("["):
                    status.set(data)
            else:
                busy(False)
                if data["ok"]:
                    state["root"] = data["root"]
                    status.set("生成完成！点击“打开结果”查看视频、字幕和讲稿。")
                    open_button.configure(state="normal")
                    messagebox.showinfo("生成完成", "视频、字幕和讲稿已保存至：\n" + data["root"])
                else:
                    status.set("生成未完成：" + data["error"])
                    messagebox.showerror("生成未完成", data["error"])
        app.after(150, poll)

    def close():
        if state["running"]:
            if not messagebox.askyesno("退出", "任务仍在运行，退出会停止当前生成。是否退出？"):
                return
            stop()
        app.destroy()

    start = ttk.Button(buttons, text="开始生成视频", style="Accent.TButton", command=begin)
    start.pack(side="left")
    cancel = ttk.Button(buttons, text="停止", command=stop, state="disabled")
    cancel.pack(side="left", padx=10)
    open_button = ttk.Button(buttons, text="打开结果", command=open_output, state="disabled")
    open_button.pack(side="right")
    app.protocol("WM_DELETE_WINDOW", close)
    app.after(150, poll)
    if "--smoke-ui" in sys.argv:
        def capture():
            from PIL import Image
            import win32gui, win32ui
            target = Path(sys.argv[sys.argv.index("--smoke-ui") + 1])
            app.update()
            hwnd = win32gui.GetParent(app.winfo_id())
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width, height = right - left, bottom - top
            dc = win32gui.GetWindowDC(hwnd)
            src = win32ui.CreateDCFromHandle(dc)
            dst = src.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(src, width, height)
            dst.SelectObject(bitmap)
            import ctypes
            ctypes.windll.user32.PrintWindow(hwnd, dst.GetSafeHdc(), 2)
            Image.frombuffer("RGB", (width, height), bitmap.GetBitmapBits(True), "raw", "BGRX", 0, 1).save(target)
            win32gui.DeleteObject(bitmap.GetHandle())
            dst.DeleteDC()
            src.DeleteDC()
            win32gui.ReleaseDC(hwnd, dc)
            app.destroy()
        app.after(1500, capture)
    app.mainloop()


if __name__ == "__main__":
    if "--worker" in sys.argv:
        raise SystemExit(worker())
    if "--self-test" in sys.argv:
        from desktop.pipeline import endpoint, validate_cues, resources
        import edge_tts, pptx, PIL, numpy, mutagen, tkinter
        from lxml import etree
        etree.Element("bundle-test")
        assert endpoint("https://example.com/v1") == "https://example.com/v1/chat/completions"
        assert (resources() / "scripts" / "03_build_video.py").exists()
        assert (resources() / "bin" / "ffmpeg.exe").exists()
        print("Desktop bundle self-test passed.")
    else:
        gui()
