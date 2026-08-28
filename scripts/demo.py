"""命令行演示：把一段音频转成钢琴谱。

用法：
    python scripts/demo.py 录音.wav                      # 输出到 work/demo/
    python scripts/demo.py 录音.wav -o out --engine dsp
    python scripts/demo.py 录音.wav --engine basicpitch  # 需要 ML 环境
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser(description="钢琴录音 -> 钢琴谱")
    ap.add_argument("audio", type=Path, help="输入音频文件（wav/mp3/flac/ogg/m4a 等）")
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "work" / "demo", help="输出目录")
    ap.add_argument("--engine", default="auto", choices=["auto", "dsp", "basicpitch"], help="转写引擎")
    ap.add_argument("--no-render", action="store_true", help="跳过谱面图像渲染（只出 MIDI/MusicXML）")
    args = ap.parse_args()

    if not args.audio.exists():
        ap.error(f"音频文件不存在：{args.audio}")

    from app.pipeline import run_pipeline
    from app.transcribe import available_engines

    print("可用引擎：", ", ".join(available_engines().keys()))

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] 转写中（引擎={args.engine}）…")
    result = run_pipeline(args.audio, out, engine_name=args.engine, render=not args.no_render)

    # 复制原始音频 + 写音符 JSON
    shutil.copy2(args.audio, out / f"input{args.audio.suffix.lower()}")
    notes_json = [n.to_dict() for n in result.notes]
    (out / "notes.json").write_text(json.dumps(notes_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[2/4] 识别音符：{len(notes_json)} 个")
    print(f"[3/4] 估计速度：{result.bpm:.0f} BPM，音频时长 {result.duration:.1f}s")
    print("[4/4] 产物目录：", out)
    for kind, path in result.files.items():
        print(f"      - {kind:8s} {path.name}  ({path.stat().st_size} bytes)")
    if "svg" in result.files:
        print("      谱面已渲染：score.svg（浏览器可打开）")

    print("\n前 20 个音符：")
    print(f"{'音名':<6}{'MIDI':<6}{'开始(s)':<10}{'时长(s)':<10}{'力度':<6}")
    for n in notes_json[:20]:
        print(f"{n['name']:<6}{n['midi']:<6}{n['start']:<10.3f}{n['duration']:<10.3f}{round(n['velocity']):<6}")


if __name__ == "__main__":
    main()
