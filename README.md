# Piano Scribe · 钢琴录音转谱

> 上传任意一段钢琴录音，自动生成可读的钢琴谱：**MIDI、MusicXML、以及渲染好的谱面图像（SVG/PNG）**。

这是一个把「录音 → 钢琴谱」想法落地为可运行软件的开源项目骨架：
内置了**经典 DSP 转写引擎**（零 ML 依赖，开箱即用）和 **Basic Pitch 深度学习引擎**（Spotify 开源，复调钢琴转录质量高）。

---

## ✨ 功能

- 🎵 上传音频（WAV / MP3 / FLAC / OGG / M4A / AAC …），≤ 100 MB
- 🧠 两种转写引擎，可自动选择：
  - `dsp`：经典信号处理（谱峰追踪 + 起音检测），无需任何 ML 依赖
  - `basicpitch`：Spotify Basic Pitch 深度学习模型，适合真实钢琴录音（需可选安装）
- 🎼 自动生成**双谱表（高音 + 低音）钢琴谱**，量化到节拍网格，估计速度（BPM）
- 📄 产物齐全：`.mid` / `.musicxml` / `score.svg` / `score.png` / `notes.json`
- 🌐 网页界面：拖拽上传（或一键「用示例音频试试」）→ 实时任务进度 → 在线播放原声 + 查看谱面 + 下载
- 🖥️ 命令行 CLI：适合批量处理与调试

---

## 🚀 快速开始（Windows / PowerShell）

> 需要 **Python 3.11**（依赖栈为兼容 Basic Pitch 已锁定版本）。

```powershell
cd piano-scribe
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

启动 Web 服务：

```powershell
python -m uvicorn app.main:app --reload --port 8000
# 浏览器打开 http://127.0.0.1:8000
# 首页即可点击「用示例音频试试」体验完整流程（内置合成钢琴旋律）
```

命令行试用（内置合成旋律，无真实录音也能立刻看到效果）：

```powershell
python scripts/demo.py work/demo_melody.wav -o work/demo
```

> 若还没有录音，可先用 `python -m tests.make_synth_audio work/demo_melody.wav` 合成一段测试音频。

---

## ⚡ 启用深度学习引擎（Basic Pitch，可选）

Basic Pitch 依赖 TensorFlow，并要求 `numpy<1.24`，请使用 **Python 3.11** 安装：

```powershell
python -m pip install -r requirements.txt -r requirements-ml.txt
```

安装后引擎会自动出现在网页下拉框 / CLI 的 `--engine basicpitch` 中；
未安装时 Web 服务照常运行（自动回退到 DSP 引擎）。

---

## 🧱 项目结构

```
piano-scribe/
├── app/
│   ├── main.py               # FastAPI 入口
│   ├── api.py                # 上传 / 任务 / 产物下载 API
│   ├── pipeline.py           # 端到端管线：音频→音符→MIDI→MusicXML→谱面
│   ├── notation.py           # 量化、MIDI 生成、双谱表 MusicXML（music21）
│   ├── render.py             # MusicXML → SVG（Verovio）/ PNG
│   ├── transcribe/
│   │   ├── base.py           # Note 数据结构 + 引擎接口
│   │   ├── dsp.py            # 经典 DSP 引擎（无 ML 依赖）
│   │   └── basicpitch.py     # Basic Pitch 深度学习引擎（可选）
│   └── static/               # 网页前端
├── scripts/demo.py           # 命令行演示
├── tests/                    # 单元测试 + 合成音频生成器
├── requirements.txt          # 基础依赖
└── requirements-ml.txt       # 可选 ML 依赖
```

---

## ⚙️ 工作原理

1. **转写**：音频 → 音符序列（时间、音高、力度）
2. **测速 + 量化**：librosa 估计 BPM，把起止时间吸附到 16 分音符网格，合并重叠音
3. **记谱**：按中央 C 分谱（高音/低音谱表），用 music21 生成 MusicXML
4. **排版**：Verovio（开源音乐排版引擎）渲染为 SVG，可选转 PNG
5. **分发**：Web 界面 / CLI 输出全部产物

详细设计见 [DESIGN.md](DESIGN.md)。

---

## 🧪 测试

```powershell
python -m unittest discover -s tests -v
```

---

## ⚠️ 已知限制（MVP）

- DSP 引擎对**简单旋律**效果较好，复杂和弦/织体建议用 Basic Pitch 引擎
- 节奏量化固定使用估计 BPM + 16 分音符网格，未做乐理级别的节奏重写
- 无自动指法、踏板、表情标记；调号默认 C 大调
- 未做多轨分离（人声+钢琴混录需先做音源分离）

---

## 🗺️ 路线图

见 [DESIGN.md](DESIGN.md) 第 8 节，包含 MVP → V1 → V2 的演进计划。

## 🙏 致谢

- [Spotify Basic Pitch](https://github.com/spotify/basic-pitch)
- [librosa](https://librosa.org) / [pretty_midi](https://github.com/craffel/pretty-midi) / [music21](https://www.music21.org) / [Verovio](https://www.verovio.org) / [FastAPI](https://fastapi.tiangolo.com)

