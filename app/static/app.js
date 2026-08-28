(() => {
  const $ = (id) => document.getElementById(id);
  const dropzone = $("dropzone"), fileInput = $("fileInput"), engineSel = $("engine");
  const transcribeBtn = $("transcribeBtn"), selected = $("selected");
  const progress = $("progress"), progressText = $("progressText");
  const errorBox = $("error"), result = $("result");

  let currentFile = null;
  let pollTimer = null;

  async function initEngines() {
    try {
      const res = await fetch("/api/engines");
      const data = await res.json();
      const names = { auto: "自动选择（推荐）" };
      Object.values(data.engines).forEach((e) => {
        names[e.name] = e.display_name + (e.requires_ml ? " ⚡" : "");
      });
      engineSel.innerHTML = Object.entries(names)
        .map(([v, label]) => `<option value="${v}">${label}</option>`)
        .join("");
    } catch (err) { /* 引擎列表加载失败不影响使用 */ }
  }

  function setFile(file) {
    currentFile = file;
    selected.textContent = `已选择：${file.name}（${(file.size / 1024 / 1024).toFixed(2)} MB）`;
    selected.classList.remove("hidden");
    transcribeBtn.disabled = false;
  }

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });
  ["dragover", "dragenter"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); }));
  dropzone.addEventListener("drop", (e) => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) setFile(f);
  });

  async function uploadAndRun(file) {
    hide(result); hide(errorBox); hide(progress);
    progress.classList.remove("hidden");
    progressText.textContent = "正在上传并排队…";
    transcribeBtn.disabled = true;

    const fd = new FormData();
    fd.append("file", file);
    fd.append("engine", engineSel.value);

    let job;
    try {
      const res = await fetch("/api/jobs", { method: "POST", body: fd });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`上传失败（HTTP ${res.status}）${detail}`);
      }
      job = await res.json();
    } catch (err) {
      showError(err.message);
      transcribeBtn.disabled = false;
      return;
    }
    pollTimer = setInterval(() => poll(job.job_id), 1000);
    poll(job.job_id);
  }

  transcribeBtn.addEventListener("click", () => { if (currentFile) uploadAndRun(currentFile); });

  const demoBtn = $("demoBtn");
  demoBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/static/demo_melody.wav");
      if (!res.ok) throw new Error("示例音频加载失败（HTTP " + res.status + "）");
      const blob = await res.blob();
      const file = new File([blob], "demo_melody.wav", { type: "audio/wav" });
      currentFile = file;
      selected.textContent = `已选择：${file.name}（${(file.size / 1024 / 1024).toFixed(2)} MB，示例音频）`;
      selected.classList.remove("hidden");
      await uploadAndRun(file);
    } catch (err) {
      showError(err.message);
    }
  });

  async function poll(jobId) {
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      const job = await res.json();
      if (job.status === "running") {
        progressText.textContent = "正在转写（深度学习模型可能需要十几秒到几分钟）…";
      } else if (job.status === "done") {
        clearInterval(pollTimer);
        renderResult(job);
      } else if (job.status === "failed") {
        clearInterval(pollTimer);
        showError("转写失败：" + (job.error || "未知错误"));
        transcribeBtn.disabled = false;
      }
    } catch (err) {
      clearInterval(pollTimer);
      showError("查询任务状态失败：" + err.message);
      transcribeBtn.disabled = false;
    }
  }

  function renderResult(job) {
    hide(progress); hide(errorBox);
    $("summaryMeta").innerHTML = `
      <span>引擎：<b>${job.engine || "—"}</b></span>
      <span>时长：<b>${job.duration ? job.duration.toFixed(1) : "—"} s</b></span>
      <span>音符数：<b>${job.note_count ?? "—"}</b></span>
      <span>估计速度：<b>${job.bpm ?? "—"} BPM</b></span>`;
    const files = job.files || {};
    $("dlMidi").href = files.midi || "#";
    $("dlXml").href = files.musicxml || "#";
    $("dlSvg").href = files.svg || "#";
    $("dlPng").href = files.png || "#";
    $("dlPng").classList.toggle("hidden", !files.png);

    if (files.input) {
      $("audioPlayer").src = files.input;
      $("audioWrap").classList.remove("hidden");
    }
    const score = $("score");
    if (files.svg) {
      score.innerHTML = "";
      fetch(files.svg).then((r) => r.text()).then((svg) => { score.innerHTML = svg; });
    } else {
      score.innerHTML = "<p style='color:var(--muted)'>谱面渲染失败，可下载 MIDI / MusicXML 用 MuseScore 打开。</p>";
    }

    const tbody = document.querySelector("#notesTable tbody");
    tbody.innerHTML = "";
    (job.notes || []).forEach((n, i) => {
      const tr = document.createElement("tr");
      [i + 1, n.name, n.midi, n.start.toFixed(3), n.duration.toFixed(3), Math.round(n.velocity)]
        .forEach((v) => { const td = document.createElement("td"); td.textContent = v; tr.appendChild(td); });
      tbody.appendChild(tr);
    });
    if (!job.notes || job.notes.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 6; td.textContent = "没有识别到音符";
      tr.appendChild(td); tbody.appendChild(tr);
    }

    result.classList.remove("hidden");
    result.scrollIntoView({ behavior: "smooth" });
    transcribeBtn.disabled = false;
  }

  function showError(msg) {
    hide(progress);
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }
  function hide(el) { el.classList.add("hidden"); }

  initEngines();
})();

