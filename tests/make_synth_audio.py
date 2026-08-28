"""合成一段钢琴音色音频，用于离线测试与演示（无需真实录音）。"""
from __future__ import annotations

import numpy as np

# 自创旋律：C 大调音阶上行 + 简单乐句（避开版权旋律）
MELODY = [60, 62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60]  # C4..C5..C4
BASS = [48, 43, 45, 48, 43, 45, 48, 43]  # C3, G2, A2 ... 弱拍低音


def synth_note(midi: int, dur: float, sr: int = 22050, amp: float = 0.5, rng=None) -> np.ndarray:
    """合成一个类钢琴音符：基频 + 谐波，指数衰减，短促起音。"""
    if rng is None:
        rng = np.random.default_rng(42)
    f = 440.0 * 2.0 ** ((midi - 69) / 12.0)
    n = max(1, int(dur * sr))
    t = np.arange(n) / sr
    wave = np.zeros(n)
    for i, rel in enumerate([1.0, 0.5, 0.25, 0.12, 0.06], start=1):
        tau = 0.7 if i == 1 else 0.35
        phase = rng.uniform(0, 2 * np.pi)
        wave += rel * np.exp(-t / tau) * np.sin(2 * np.pi * f * i * t + phase)
    attack = np.minimum(t / 0.008, 1.0)
    release = np.minimum((dur - t) / 0.06, 1.0)
    wave *= attack * np.clip(release, 0, 1)
    return amp * wave / 1.93


def make_melody_wav(path, bpm: float = 100.0, sr: int = 22050,
                    with_bass: bool = False, noise: float = 0.004,
                    note_dur: float = 0.55) -> list[int]:
    """合成旋律并写入 wav，返回实际放置的 MIDI 音高列表。"""
    import soundfile as sf

    rng = np.random.default_rng(7)
    placed: list[int] = []
    beat = 60.0 / bpm
    step = note_dur
    total = step * max(len(MELODY), len(BASS) * 2 if with_bass else 0) + 1.0
    track = np.zeros(int(total * sr))
    t0 = 0.2  # 起始留白

    for i, mid in enumerate(MELODY):
        start = int((t0 + i * step) * sr)
        seg = synth_note(mid, note_dur * 1.15, sr=sr, rng=rng)
        end = min(start + len(seg), len(track))
        track[start:end] += seg[: end - start]
        placed.append(mid)

    if with_bass:
        for i, mid in enumerate(BASS):
            start = int((t0 + i * step * 2 + beat) * sr)
            seg = synth_note(mid, note_dur * 1.6, sr=sr, amp=0.42, rng=rng)
            end = min(start + len(seg), len(track))
            track[start:end] += seg[: end - start]
            placed.append(mid)

    track += noise * rng.standard_normal(len(track))
    track = np.clip(track, -1.0, 1.0)
    sf.write(str(path), track.astype(np.float32), sr)
    return placed

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="合成一段类钢琴测试音频")
    ap.add_argument("out", type=str, help="输出 wav 路径")
    ap.add_argument("--bpm", type=float, default=100.0)
    ap.add_argument("--with-bass", action="store_true", help="叠加低音声部")
    args = ap.parse_args()

    placed = make_melody_wav(args.out, bpm=args.bpm, with_bass=args.with_bass)
    print(f"已生成 {args.out}，放置了 {len(placed)} 个音符")
