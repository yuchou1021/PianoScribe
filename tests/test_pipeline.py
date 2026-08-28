"""端到端与单元测试。运行：python -m unittest discover -s tests"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import run_pipeline
from app.transcribe.dsp import DSPEngine
from tests.make_synth_audio import make_melody_wav


class TestDSPEngine(unittest.TestCase):
    def test_monophonic_melody_detection(self):
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "melody.wav"
            expected = set(make_melody_wav(wav, with_bass=False))
            notes = DSPEngine().transcribe(wav)
            detected = set(n.midi for n in notes)
            hits = len(expected & detected)
            self.assertGreaterEqual(
                hits, max(2, int(len(expected) * 0.6)),
                f"命中 {hits}/{len(expected)}，检出音高：{sorted(detected)}",
            )


class TestPipeline(unittest.TestCase):
    def test_end_to_end_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            wav = td / "melody.wav"
            make_melody_wav(wav)
            out = td / "out"
            res = run_pipeline(wav, out, engine_name="dsp")
            self.assertGreater(len(res.notes), 0)
            for kind in ("midi", "musicxml", "svg"):
                self.assertIn(kind, res.files, f"缺少产物 {kind}")
                self.assertGreater(res.files[kind].stat().st_size, 0, f"{kind} 为空")

    def test_quantize_merges_overlaps(self):
        from app.notation import quantize_notes
        from app.transcribe.base import Note

        notes = [Note(midi=60, start=0.0, duration=1.0), Note(midi=60, start=0.4, duration=1.0)]
        q = quantize_notes(notes, bpm=120)
        self.assertEqual(len(q), 1)
        self.assertAlmostEqual(q[0].duration, 1.375, places=3)


if __name__ == "__main__":
    unittest.main()

