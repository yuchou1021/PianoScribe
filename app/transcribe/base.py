"""转写引擎公共接口与共享数据类型。"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class Note:
    """一个被转写出来的音符。

    midi 为 MIDI 音高（60 = 中央 C / C4），start/duration 单位为秒。
    """

    midi: int
    start: float
    duration: float
    velocity: float = 80.0   # 0-127
    confidence: float = 1.0  # 0-1

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def name(self) -> str:
        return f"{_NOTE_NAMES[self.midi % 12]}{self.midi // 12 - 1}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["name"] = self.name
        d["end"] = round(self.end, 4)
        return d


class BaseEngine:
    """转写引擎基类。"""

    name: str = "base"
    display_name: str = "Base"
    requires_ml: bool = False

    def transcribe(self, audio_path: Path) -> list[Note]:
        raise NotImplementedError


def midi_from_freq(freq: float) -> float:
    """频率 (Hz) -> 小数 MIDI 音高。"""
    if freq <= 0:
        return 0.0
    return 69.0 + 12.0 * float(np.log2(freq / 440.0))


def freq_from_midi(midi: float) -> float:
    """MIDI 音高 -> 频率 (Hz)。"""
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)
