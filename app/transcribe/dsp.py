"""经典 DSP 转写引擎（无任何 ML 依赖）。

策略：
  1. STFT -> 逐帧幅度谱
  2. 每帧用 scipy 找显著谱峰，映射为 MIDI 音高
  3. 逐帧跟踪音符活动，形成 note 事件（出现连续 N 帧视为起音，消失视为结束）
  4. 用谱通量检测的 onset 校正起音位置

适合单旋律与简单和弦；复杂钢琴织体请使用 Basic Pitch 引擎。
"""
from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
from scipy.signal import find_peaks

from .base import BaseEngine, Note, midi_from_freq


class DSPEngine(BaseEngine):
    name = "dsp"
    display_name = "DSP 引擎（经典算法，无 ML 依赖）"
    requires_ml = False

    def __init__(
        self,
        sr: int = 22050,
        n_fft: int = 2048,
        hop_length: int = 512,
        fmin: float = 55.0,          # A1
        fmax: float = 4186.0,        # C8
        peak_prominence_db: float = 3.0,
        floor_db: float = 55.0,      # 相对全局最大值的静音阈值
        min_note_ms: float = 70.0,   # 低于此长度的音符丢弃
        max_notes_per_frame: int = 5,
        onset_snap_window: float = 0.15,  # 起音吸附窗口（秒）
    ) -> None:
        self.sr = sr
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.fmin = fmin
        self.fmax = fmax
        self.peak_prominence_db = peak_prominence_db
        self.floor_db = floor_db
        self.min_note_ms = min_note_ms
        self.max_notes_per_frame = max_notes_per_frame
        self.onset_snap_window = onset_snap_window

    def transcribe(self, audio_path: Path) -> list[Note]:
        y, sr = librosa.load(str(audio_path), sr=self.sr, mono=True)
        if y.size == 0:
            return []

        S = np.abs(librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length))
        S_db = librosa.amplitude_to_db(S, ref=np.max)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)

        band = (freqs >= self.fmin) & (freqs <= self.fmax)
        freqs_b = freqs[band]
        S_b = S_db[band]
        time_per_frame = self.hop_length / sr
        floor = float(np.max(S_db)) - self.floor_db

        # midi -> [start_frame, last_frame, peak_mag_db]
        active: dict[int, list] = {}
        notes: list[Note] = []

        for f in range(S_b.shape[1]):
            frame = S_b[:, f]
            peaks, props = find_peaks(frame, prominence=self.peak_prominence_db)
            cands = [(p, float(frame[p])) for p in peaks if frame[p] >= floor]
            cands.sort(key=lambda t: t[1], reverse=True)
            cands = cands[: self.max_notes_per_frame]

            # 量化为 MIDI 并去重（同一音名只留最强）
            frame_notes: dict[int, float] = {}
            for p, mag in cands:
                mid = int(round(midi_from_freq(freqs_b[p])))
                frame_notes[mid] = max(frame_notes.get(mid, -np.inf), mag)

            # 关闭消失的音符
            for mid in list(active):
                if mid not in frame_notes:
                    start_f, last_f, peak_mag = active.pop(mid)
                    dur_s = (last_f + 1 - start_f) * time_per_frame
                    if dur_s >= self.min_note_ms / 1000.0:
                        notes.append(
                            Note(
                                midi=mid,
                                start=start_f * time_per_frame,
                                duration=dur_s,
                                velocity=self._velocity(peak_mag, floor, float(np.max(S_db))),
                            )
                        )

            # 开启/更新音符
            for mid, mag in frame_notes.items():
                if mid in active:
                    active[mid][1] = f
                    active[mid][2] = max(active[mid][2], mag)
                else:
                    active[mid] = [f, f, mag]

        # 收尾
        for mid, (start_f, last_f, peak_mag) in active.items():
            dur_s = (last_f + 1 - start_f) * time_per_frame
            if dur_s >= self.min_note_ms / 1000.0:
                notes.append(
                    Note(
                        midi=mid,
                        start=start_f * time_per_frame,
                        duration=dur_s,
                        velocity=self._velocity(peak_mag, floor, float(np.max(S_db))),
                    )
                )

        # onset 校正
        onsets = librosa.onset.onset_detect(
            y=y, sr=sr, hop_length=self.hop_length, backtrack=True
        )
        onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=self.hop_length)
        for n in notes:
            n.start = self._snap_to_onset(n.start, onset_times)

        notes.sort(key=lambda n: (n.start, n.midi))
        return notes

    @staticmethod
    def _velocity(mag_db: float, floor_db: float, max_db: float) -> float:
        span = max_db - floor_db
        if span <= 0:
            return 80.0
        ratio = (mag_db - floor_db) / span
        return float(np.clip(40 + 70 * ratio, 40, 110))

    def _snap_to_onset(self, t: float, onsets: np.ndarray) -> float:
        if onsets.size == 0:
            return t
        idx = int(np.argmin(np.abs(onsets - t)))
        nearest = float(onsets[idx])
        if abs(nearest - t) <= self.onset_snap_window:
            return nearest
        return t
