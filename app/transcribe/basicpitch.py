"""Basic Pitch（Spotify 开源）深度学习转写引擎。

对复调钢琴织体的转写质量远高于纯 DSP 方法。
该引擎需要额外安装 requirements-ml.txt 中的依赖（tensorflow + basic-pitch），
模块导入被延迟到实例化时，因此未安装 ML 环境时 Web 服务也能正常启动。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from .base import BaseEngine, Note


class BasicPitchEngine(BaseEngine):
    name = "basicpitch"
    display_name = "Basic Pitch（Spotify 深度学习引擎）"
    requires_ml = True

    def __init__(self) -> None:
        try:
            import basic_pitch  # noqa: F401  (deferred heavy import)
            self._patch_scipy_compat()
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "basic-pitch 未安装或其 TensorFlow 依赖不可用。"
                "请先执行: pip install -r requirements-ml.txt"
            ) from exc

    @staticmethod
    def _patch_scipy_compat() -> None:
        """兼容新版 scipy：scipy.signal.gaussian 在 scipy>=1.13 被移除。"""
        import scipy.signal

        if not hasattr(scipy.signal, "gaussian"):
            from scipy.signal import windows as _windows

            scipy.signal.gaussian = _windows.gaussian  # type: ignore[attr-defined]

    def transcribe(self, audio_path: Path) -> list[Note]:
        import sys

        # basic_pitch 的日志带 emoji，在 GBK 控制台下会崩溃；强制 UTF-8 输出
        for _stream in (sys.stdout, sys.stderr):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        from basic_pitch.inference import predict_and_save
        import pretty_midi

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            predict_and_save(
                [str(audio_path)],
                str(out_dir),
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=True,
            )
            midi_path = out_dir / f"{audio_path.stem}_basic_pitch.mid"
            pm = pretty_midi.PrettyMIDI(str(midi_path))
            notes: list[Note] = []
            for inst in pm.instruments:
                if inst.is_drum:
                    continue
                for n in inst.notes:
                    notes.append(
                        Note(
                            midi=int(round(n.pitch)),
                            start=float(n.start),
                            duration=float(max(n.end - n.start, 0.05)),
                            velocity=float(np.clip(n.velocity, 0, 127)),
                            confidence=1.0,
                        )
                    )
        notes.sort(key=lambda n: (n.start, n.midi))
        return notes


