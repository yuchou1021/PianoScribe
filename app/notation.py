"""音符 -> MIDI (pretty_midi) 与 MusicXML (music21) 转换。

量化以「整数网格单位」计算，避免浮点误差产生 music21 无法表达的时值
（例如 1.7499 拍这样的值）。
"""
from __future__ import annotations

import copy
from pathlib import Path

import pretty_midi
from music21 import clef, instrument, layout, meter, note as m21note, chord as m21chord, stream, tempo
from music21.tie import Tie

from .transcribe.base import Note

SPLIT_MIDI = 60      # 中央 C：>=60 高音谱表，<60 低音谱表
GRID_DIVISIONS = 4   # 一拍四等分 = 16 分音符网格
MAX_QL_PER_ELEMENT = 4.0  # 4/4 拍中单元素最长一小节


def quantize_notes(notes: list[Note], bpm: float, grid_divisions: int = GRID_DIVISIONS) -> list[Note]:
    """把音符起止吸附到节拍网格（整数网格单位），并合并同音高重叠。"""
    beat = 60.0 / bpm
    grid = beat / grid_divisions
    q: list[Note] = []
    for n in notes:
        su = int(round(n.start / grid))
        eu = int(round((n.start + n.duration) / grid))
        eu = max(eu, su + 1)  # 至少一个网格
        c = copy.copy(n)
        c.start = round(su * grid, 6)
        c.duration = round((eu - su) * grid, 6)
        q.append(c)

    q.sort(key=lambda n: (n.midi, n.start))
    merged: list[Note] = []
    for n in q:
        if merged and merged[-1].midi == n.midi and n.start <= merged[-1].end + 1e-6:
            prev = merged[-1]
            prev.duration = round(max(prev.duration, n.end - prev.start), 6)
        else:
            merged.append(copy.copy(n))
    merged.sort(key=lambda n: (n.start, n.midi))
    return merged


def notes_to_midi(notes: list[Note], bpm: float = 120.0, out_path: Path | None = None) -> pretty_midi.PrettyMIDI:
    """生成标准 MIDI 文件。"""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0, is_drum=False, name="Piano")
    for n in notes:
        vel = int(max(0, min(127, round(n.velocity))))
        inst.notes.append(
            pretty_midi.Note(velocity=vel, pitch=int(round(n.midi)), start=n.start, end=n.start + n.duration)
        )
    pm.instruments.append(inst)
    if out_path:
        pm.write(str(out_path))
    return pm


def _group_into_events(notes: list[Note], bpm: float, grid_divisions: int = GRID_DIVISIONS):
    """按网格对齐后分组：同一网格时刻的音符合成一个事件（和弦）。返回 (start, dur, midis)。"""
    beat = 60.0 / bpm
    grid = beat / grid_divisions
    buckets: dict[int, list[Note]] = {}
    for n in notes:
        key = int(round(n.start / grid))
        buckets.setdefault(key, []).append(n)
    events = []
    for key in sorted(buckets):
        ns = buckets[key]
        start_su = key
        end_su = max(int(round((n.start + n.duration) / grid)) for n in ns)
        events.append(
            (
                round(start_su * grid, 6),
                round((end_su - start_su) * grid, 6),
                sorted(n.midi for n in ns),
            )
        )
    return events


def _append_element(st, make_func, ql: float):
    """把元素追加进谱表流；超过一小节时拆分为多个元素（单音加连线）。"""
    remaining = ql
    first = True
    while remaining > MAX_QL_PER_ELEMENT + 1e-9:
        el = make_func(MAX_QL_PER_ELEMENT, tie_start=first, tie_stop=True)
        st.append(el)
        remaining -= MAX_QL_PER_ELEMENT
        first = False
    el = make_func(remaining, tie_start=not first, tie_stop=False)
    st.append(el)


def _build_staff(events: list, min_midi: int, max_midi: int, bpm: float,
                 staff_clef, grid_divisions: int = GRID_DIVISIONS) -> stream.Stream:
    beat = 60.0 / bpm
    grid = beat / grid_divisions
    st = stream.Stream()
    st.insert(0, meter.TimeSignature("4/4"))
    st.insert(0, staff_clef)
    cursor = 0.0
    for start, dur, midis in events:
        staff_midis = [m for m in midis if min_midi <= m < max_midi]
        if not staff_midis:
            continue
        gap = start - cursor
        if gap > 1e-6:
            gap_ql = round(gap / beat, 4)
            _append_element(st, lambda ql, **kw: m21note.Rest(quarterLength=ql), gap_ql)
        ql = round(dur / beat, 4)
        ql = max(ql, 0.25)
        if len(staff_midis) == 1:
            def make_note(ql, tie_start=False, tie_stop=False):
                el = m21note.Note(staff_midis[0], quarterLength=ql)
                if tie_start:
                    el.tie = Tie("start")
                elif tie_stop:
                    el.tie = Tie("stop")
                return el
            _append_element(st, make_note, ql)
        else:
            def make_chord(ql, **kw):
                return m21chord.Chord(staff_midis, quarterLength=ql)
            _append_element(st, make_chord, ql)
        cursor = start + dur
    # 末尾补休止，保证谱面完整
    if events:
        total = max(e[0] + e[1] for e in events)
        if total > cursor + 1e-6:
            tail_ql = round((total - cursor) / beat, 4)
            _append_element(st, lambda ql, **kw: m21note.Rest(quarterLength=ql), tail_ql)
    return st


def notes_to_musicxml(notes: list[Note], bpm: float = 120.0,
                      out_path: Path | None = None, split_midi: int = SPLIT_MIDI) -> stream.Score:
    """生成双谱表（高音+低音）钢琴谱的 MusicXML。"""
    events = _group_into_events(notes, bpm)
    if not events:
        events = [(0.0, 4 * 60.0 / bpm, [])]

    treble = _build_staff(events, split_midi, 128, bpm, clef.TrebleClef())
    bass = _build_staff(events, 0, split_midi, bpm, clef.BassClef())

    treble.insert(0, instrument.Piano())
    treble.insert(0, tempo.MetronomeMark(number=bpm))

    s = stream.Score()
    s.insert(0, layout.StaffGroup([treble, bass], name="Piano", abbreviation="Pno."))
    s.append(treble)
    s.append(bass)

    if out_path:
        s.write("musicxml", fp=str(out_path))
    return s

