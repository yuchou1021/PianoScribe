"""端到端转写管线：音频 -> 音符 -> MIDI -> MusicXML -> SVG。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import librosa

from .notation import notes_to_midi, notes_to_musicxml, quantize_notes
from .render import musicxml_to_svg, svg_to_png
from .transcribe import Note, get_engine


@dataclass
class PipelineResult:
    notes: list[Note]
    bpm: float
    engine: str
    duration: float
    files: dict[str, Path] = field(default_factory=dict)


def run_pipeline(audio_path: Path, out_dir: Path, engine_name: str = "auto",
                 render: bool = True) -> PipelineResult:
    """完整处理一段音频，产物写入 out_dir。"""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 转写
    engine = get_engine(engine_name)
    raw_notes = engine.transcribe(audio_path)

    # 2) 测速 + 量化
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    duration = float(len(y) / sr) if len(y) else 0.0
    bpm = 120.0
    if len(y) > 0:
        try:
            bpm = float(librosa.beat.tempo(y=y, sr=sr)[0])
        except Exception:
            pass
    bpm = max(40.0, min(208.0, bpm))
    notes = quantize_notes(raw_notes, bpm=bpm)

    # 3) MIDI
    midi_path = out_dir / "output.mid"
    notes_to_midi(notes, bpm=bpm, out_path=midi_path)

    # 4) MusicXML
    xml_path = out_dir / "output.musicxml"
    notes_to_musicxml(notes, bpm=bpm, out_path=xml_path)

    files = {"midi": midi_path, "musicxml": xml_path}

    # 5) 谱面渲染
    if render:
        svg_path = out_dir / "score.svg"
        try:
            musicxml_to_svg(xml_path, svg_path)
            files["svg"] = svg_path
        except Exception:
            pass
        png_path = out_dir / "score.png"
        if svg_path.exists():
            png = svg_to_png(svg_path, png_path)
            if png is not None:
                files["png"] = png

    return PipelineResult(notes=notes, bpm=bpm, engine=engine.name, duration=duration, files=files)
