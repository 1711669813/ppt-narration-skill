# -*- coding: utf-8 -*-
"""下载可选的本地 ASR 模型（只用于验收：确认"标记的那块＝在讲的那句"）。

    python models/fetch_models.py            # 默认 small
    python models/fetch_models.py base       # 更小
    python models/fetch_models.py --list     # 只打印候选与体积，不下载

下载到包内 results/cache/huggingface/hub，ASR 复核直接复用。
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from output_paths import MODEL_CACHE

MODELS = {
    "tiny": ("Systran/faster-whisper-tiny", "≈75 MB", "只确认有没有声音/说的是不是这段"),
    "base": ("Systran/faster-whisper-base", "≈145 MB", "关键词抽查够用"),
    "small": ("Systran/faster-whisper-small", "≈480 MB", "默认；中文术语识别够用"),
}


def main():
    args = [a for a in sys.argv[1:] if a]
    if "--list" in args:
        for k, (repo, size, note) in MODELS.items():
            print("%-6s %-34s %-9s %s" % (k, repo, size, note))
        return
    key = args[0] if args else "small"
    if key not in MODELS:
        sys.exit("未知模型 %r，可选：%s" % (key, ", ".join(MODELS)))
    repo, size, note = MODELS[key]
    print("准备下载 %s（%s，%s）" % (repo, size, note))
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit("缺少 huggingface_hub：pip install huggingface_hub\n"
                 "（也可以跳过下载：首次运行 faster-whisper 时会自动拉取）")
    path = snapshot_download(repo_id=repo, cache_dir=MODEL_CACHE, allow_patterns=["*.bin", "*.json", "*.txt", "*.model"])
    print("已就绪：", path)
    print("校验：KMP_DUPLICATE_LIB_OK=TRUE python scripts/05_verify.py --asr %s" % key)


if __name__ == "__main__":
    main()
