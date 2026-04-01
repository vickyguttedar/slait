let chart;
let radarChart;
let currentTranscript = "";
let renderMode = "annotated";

const ANNOTATION_PATTERNS = [
  { key: "planning", label: "Planning", color: "bg-violet-500/25 text-violet-200", regex: /\b(plan|phase|roadmap|steps?|milestone|scope)\b/gi },
  { key: "constraints", label: "Constraints", color: "bg-amber-500/25 text-amber-200", regex: /\b(must|constraint|limit|cannot|do not|hard constraint)\b/gi },
  { key: "debugging", label: "Debugging", color: "bg-red-500/25 text-red-200", regex: /\b(debug|error|trace|failure|broken|fix)\b/gi },
  { key: "iteration", label: "Iteration", color: "bg-blue-500/25 text-blue-200", regex: /\b(iterate|iteration|refine|improve|next pass|retry)\b/gi },
  { key: "tool_usage", label: "Tool Usage", color: "bg-emerald-500/25 text-emerald-200", regex: /\b(tool|mcp|terminal|test|run|plugin|api)\b/gi },
  { key: "correction", label: "Correction", color: "bg-pink-500/25 text-pink-200", regex: /\b(correct|correction|wrong|mistake|adjust)\b/gi },
  { key: "context_management", label: "Context Management", color: "bg-indigo-500/25 text-indigo-200", regex: /\b(context|reference|assumption|dependency)\b/gi },
  { key: "understanding", label: "Understanding", color: "bg-cyan-500/25 text-cyan-200", regex: /\b(understand|goal|problem|requirement)\b/gi },
  { key: "chain_of_thought", label: "Chain-of-Thought", color: "bg-lime-500/25 text-lime-200", regex: /\b(think|reason|because|therefore|hypothesis)\b/gi }
];

function setStatus(message, isError = false) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = isError ? "mt-3 text-sm text-red-400" : "mt-3 text-sm text-slate-300";
}

function renderList(elementId, items) {
  const list = document.getElementById(elementId);
  list.innerHTML = "";
  if (!items || items.length === 0) {
    list.innerHTML = "<li class='text-slate-400'>No data</li>";
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.className = "bg-slate-800 rounded-md p-2";
    li.textContent = item;
    list.appendChild(li);
  }
}

function normalizeEvaluation(full) {
  if (full.chart_data) {
    return full;
  }
  return {
    overall_score: full.overall_score,
    label: full.label,
    chart_data: Object.entries(full.categories || {}).map(([category, data]) => ({
      category,
      score: data.score,
      confidence: data.confidence
    })),
    strengths: full.strengths || [],
    weaknesses: full.weaknesses || [],
    suggestions: full.suggestions || [],
    summary: full.summary || "",
    reflection: full.reflection || "",
    transcript_format: full.transcript_format || "unknown",
    phase_timeline: full.phase_timeline || [],
    metric_confidence: full.metric_confidence || Object.fromEntries(Object.entries(full.categories || {}).map(([k, v]) => [k, v.confidence]))
  };
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function annotateLine(line) {
  let html = escapeHtml(line);
  const hits = new Set();
  for (const pattern of ANNOTATION_PATTERNS) {
    const re = new RegExp(pattern.regex.source, "gi");
    html = html.replace(re, (m) => {
      hits.add(pattern.key);
      return `<mark class="rounded px-1 ${pattern.color} border border-slate-700">${m}</mark>`;
    });
  }
  return { html, hits: [...hits] };
}

function renderTranscript(text) {
  const viewer = document.getElementById("transcriptViewer");
  const cleaned = (text || "").trim();
  if (!cleaned) {
    viewer.innerHTML = "<span class='text-slate-500'>Transcript preview will appear here.</span>";
    return;
  }

  const lines = cleaned.split(/\r?\n/).slice(0, 200);
  viewer.innerHTML = "";
  for (const line of lines) {
    const row = document.createElement("div");
    row.className = "border-b border-slate-800 py-1";
    const lower = line.toLowerCase();
    if (lower.startsWith("user:")) {
      const content = line.slice(5);
      if (renderMode === "annotated") {
        row.innerHTML = `<span class="text-cyan-300 font-semibold mr-1">U</span>${annotateLine(content).html}`;
      } else {
        row.innerHTML = `<span class="text-cyan-300 font-semibold mr-1">U</span>${escapeHtml(content)}`;
      }
    } else if (lower.startsWith("assistant:")) {
      const content = line.slice(10);
      if (renderMode === "annotated") {
        row.innerHTML = `<span class="text-fuchsia-300 font-semibold mr-1">A</span>${annotateLine(content).html}`;
      } else {
        row.innerHTML = `<span class="text-fuchsia-300 font-semibold mr-1">A</span>${escapeHtml(content)}`;
      }
    } else {
      row.innerHTML = renderMode === "annotated" ? annotateLine(line).html : escapeHtml(line);
    }
    viewer.appendChild(row);
  }
}

function renderTags(chartData, phaseTimeline) {
  const cloud = document.getElementById("tagCloud");
  cloud.innerHTML = "";
  const colors = ["bg-cyan-500/20 text-cyan-300", "bg-fuchsia-500/20 text-fuchsia-300", "bg-emerald-500/20 text-emerald-300", "bg-amber-500/20 text-amber-300"];
  const tags = [...chartData.map((c) => c.category.replaceAll("_", " ")), ...phaseTimeline.map((p) => p.phase)];
  ANNOTATION_PATTERNS.forEach((p) => tags.push(p.label));
  [...new Set(tags)].forEach((tag, idx) => {
    const chip = document.createElement("span");
    chip.className = `text-xs px-2 py-1 rounded-full border border-slate-700 ${colors[idx % colors.length]}`;
    chip.textContent = tag;
    cloud.appendChild(chip);
  });
}

function renderMetricPanel(chartData, metricConfidence) {
  const panel = document.getElementById("metricPanel");
  panel.innerHTML = "";
  chartData.forEach((metric) => {
    const confidence = metricConfidence?.[metric.category] ?? metric.confidence ?? 0;
    const pct = Math.round((metric.score / 5) * 100);
    const confPct = Math.round(confidence * 100);
    const block = document.createElement("div");
    block.className = "bg-slate-950 border border-slate-700 rounded-lg p-3";
    block.innerHTML = `
      <div class="flex justify-between items-center text-sm mb-2">
        <span class="capitalize">${metric.category.replaceAll("_", " ")}</span>
        <span class="font-semibold">${metric.score.toFixed(1)}</span>
      </div>
      <div class="h-2 rounded bg-slate-800 overflow-hidden">
        <div class="h-full bg-emerald-400" style="width:${pct}%"></div>
      </div>
      <div class="text-[11px] text-slate-400 mt-2">confidence ${confPct}%</div>
    `;
    panel.appendChild(block);
  });
}

function renderCharts(chartData) {
  const labels = chartData.map((d) => d.category.replaceAll("_", " "));
  const scores = chartData.map((d) => d.score);
  const confidences = chartData.map((d) => d.confidence);

  const barCtx = document.getElementById("scoreChart");
  if (chart) chart.destroy();
  chart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Score (1-5)", data: scores, backgroundColor: "rgba(34,211,238,0.75)" },
        { label: "Confidence (0-1)", data: confidences, backgroundColor: "rgba(52,211,153,0.65)" }
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        x: { ticks: { color: "#e2e8f0" }, grid: { color: "rgba(148,163,184,0.15)" } },
        y: { beginAtZero: true, max: 5, ticks: { color: "#e2e8f0" }, grid: { color: "rgba(148,163,184,0.15)" } }
      }
    }
  });

  const radarCtx = document.getElementById("radarChart");
  if (radarChart) radarChart.destroy();
  radarChart = new Chart(radarCtx, {
    type: "radar",
    data: {
      labels,
      datasets: [{
        label: "Workflow Profile",
        data: scores,
        borderColor: "rgba(34,211,238,1)",
        backgroundColor: "rgba(34,211,238,0.18)",
        pointBackgroundColor: "rgba(34,211,238,1)"
      }]
    },
    options: {
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        r: {
          min: 0,
          max: 5,
          ticks: { color: "#e2e8f0", backdropColor: "transparent" },
          grid: { color: "rgba(148,163,184,0.2)" },
          angleLines: { color: "rgba(148,163,184,0.2)" },
          pointLabels: { color: "#cbd5e1" }
        }
      }
    }
  });
}

async function loadSamples() {
  try {
    const res = await fetch("/transcripts");
    const data = await res.json();
    const select = document.getElementById("sampleFile");
    const compareA = document.getElementById("compareA");
    const compareB = document.getElementById("compareB");
    for (const file of data.files || []) {
      const option = document.createElement("option");
      option.value = file;
      option.textContent = file;
      select.appendChild(option);
      compareA.appendChild(option.cloneNode(true));
      compareB.appendChild(option.cloneNode(true));
    }
  } catch {
    setStatus("Unable to load sample transcripts.", true);
  }
}

async function getSampleText(fileName) {
  const res = await fetch(`/transcripts/${encodeURIComponent(fileName)}`);
  if (!res.ok) {
    return "";
  }
  const data = await res.json();
  return data.content || "";
}

function renderEvaluation(data, transcriptText = "") {
  document.getElementById("overallScore").textContent = String(data.overall_score);
  document.getElementById("overallLabel").textContent = data.label;
  document.getElementById("summary").textContent = data.summary;
  document.getElementById("reflection").textContent = data.reflection || "";
  document.getElementById("transcriptMeta").textContent = `format: ${data.transcript_format || "unknown"}`;

  renderCharts(data.chart_data || []);
  renderMetricPanel(data.chart_data || [], data.metric_confidence || {});
  renderList("strengthsList", data.strengths || []);
  renderList("weaknessesList", data.weaknesses || []);
  renderList("suggestionsList", data.suggestions || []);
  renderList("timelineList", (data.phase_timeline || []).map((p) => `${p.phase}: messages ${p.start}-${p.end} (${p.messages})`));
  renderTags(data.chart_data || [], data.phase_timeline || []);
  renderTranscript(transcriptText || currentTranscript);
}

async function evaluateFromText(text) {
  const res = await fetch("/evaluate/dashboard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript_text: text })
  });
  return { res, transcript: text };
}

async function evaluateFromSample(path) {
  const transcript = await getSampleText(path);
  const res = await fetch("/evaluate/dashboard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript_path: `transcripts/${path}` })
  });
  return { res, transcript };
}

async function evaluateFromFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const text = await file.text();
  const res = await fetch("/evaluate/upload", { method: "POST", body: formData });
  return { res, transcript: text };
}

function clearUI() {
  document.getElementById("transcriptText").value = "";
  document.getElementById("transcriptFile").value = "";
  document.getElementById("sampleFile").value = "";
  document.getElementById("overallScore").textContent = "-";
  document.getElementById("overallLabel").textContent = "-";
  document.getElementById("summary").textContent = "";
  document.getElementById("reflection").textContent = "";
  document.getElementById("transcriptMeta").textContent = "";
  document.getElementById("compareOutput").textContent = "";
  renderList("strengthsList", []);
  renderList("weaknessesList", []);
  renderList("suggestionsList", []);
  renderList("timelineList", []);
  document.getElementById("metricPanel").innerHTML = "";
  document.getElementById("tagCloud").innerHTML = "";
  renderTranscript("");
  if (chart) { chart.destroy(); chart = null; }
  if (radarChart) { radarChart.destroy(); radarChart = null; }
  currentTranscript = "";
  setMode("annotated");
  setStatus("Cleared.");
}

function setMode(mode) {
  renderMode = mode;
  const annotated = document.getElementById("modeAnnotated");
  const full = document.getElementById("modeFull");
  if (mode === "annotated") {
    annotated.className = "px-3 py-1 rounded-full bg-cyan-600/30 text-cyan-300 border border-cyan-700";
    full.className = "px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700";
  } else {
    annotated.className = "px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700";
    full.className = "px-3 py-1 rounded-full bg-cyan-600/30 text-cyan-300 border border-cyan-700";
  }
  renderTranscript(currentTranscript);
}

async function handleEvaluate() {
  setStatus("Evaluating transcript...");
  const text = document.getElementById("transcriptText").value.trim();
  const file = document.getElementById("transcriptFile").files[0];
  const sample = document.getElementById("sampleFile").value;

  let action;
  if (text) {
    action = await evaluateFromText(text);
  } else if (file) {
    action = await evaluateFromFile(file);
  } else if (sample) {
    action = await evaluateFromSample(sample);
  } else {
    setStatus("Provide text, upload a file, or choose a sample transcript.", true);
    return;
  }

  if (!action.res.ok) {
    const errText = await action.res.text();
    setStatus(`Evaluation failed: ${errText}`, true);
    return;
  }

  currentTranscript = action.transcript || "";
  const raw = await action.res.json();
  const data = normalizeEvaluation(raw);
  renderEvaluation(data, currentTranscript);
  setStatus("Evaluation complete.");
}

async function handleCompare() {
  const a = document.getElementById("compareA").value;
  const b = document.getElementById("compareB").value;
  if (!a || !b) {
    setStatus("Select two sessions to compare.", true);
    return;
  }
  const payload = {
    sessions: [
      { name: "Session A", transcript_path: `transcripts/${a}` },
      { name: "Session B", transcript_path: `transcripts/${b}` }
    ]
  };
  const res = await fetch("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const out = document.getElementById("compareOutput");
  if (!res.ok) {
    out.textContent = await res.text();
    setStatus("Comparison failed.", true);
    return;
  }
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
  setStatus("Comparison complete.");
}

document.getElementById("evaluateBtn").addEventListener("click", handleEvaluate);
document.getElementById("compareBtn").addEventListener("click", handleCompare);
document.getElementById("clearBtn").addEventListener("click", clearUI);
document.getElementById("modeAnnotated").addEventListener("click", () => setMode("annotated"));
document.getElementById("modeFull").addEventListener("click", () => setMode("full"));
loadSamples();
renderTranscript("");
