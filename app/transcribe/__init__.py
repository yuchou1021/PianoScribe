"""转写引擎注册表：自动探测可用的引擎。"""
from __future__ import annotations

import importlib.util

from .base import BaseEngine, Note  # noqa: F401
from .dsp import DSPEngine  # noqa: F401


def _basicpitch_available() -> bool:
    return importlib.util.find_spec("basic_pitch") is not None


_instances: dict[str, BaseEngine] = {}


def available_engines() -> dict[str, dict]:
    """返回可用引擎的元信息（不触发重型导入）。"""
    info: dict[str, dict] = {
        "dsp": {"name": "dsp", "display_name": DSPEngine.display_name, "requires_ml": False}
    }
    if _basicpitch_available():
        info["basicpitch"] = {
            "name": "basicpitch",
            "display_name": "Basic Pitch（Spotify 深度学习引擎）",
            "requires_ml": True,
        }
    return info


def get_engine(name: str = "auto") -> BaseEngine:
    """获取引擎实例；auto 时优先 Basic Pitch，其次 DSP。"""
    if name not in ("auto", "dsp", "basicpitch"):
        raise ValueError(f"未知引擎 {name!r}，可用：{', '.join(available_engines())}")
    if name == "auto":
        name = "basicpitch" if _basicpitch_available() else "dsp"
    if name == "dsp":
        engine: BaseEngine = DSPEngine()
    else:
        if not _basicpitch_available():
            raise RuntimeError("basic-pitch 未安装，请安装 requirements-ml.txt 中的依赖。")
        from .basicpitch import BasicPitchEngine

        engine = BasicPitchEngine()
    return engine
