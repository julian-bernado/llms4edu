"use strict";

const PARTICIPANT_KEY = "llms4edu.participantName";
const SVG_NS = "http://www.w3.org/2000/svg";

function participantName() {
  return (localStorage.getItem(PARTICIPANT_KEY) || "").trim();
}

function requireParticipant() {
  const name = participantName();
  if (!name) {
    window.location.replace("/");
    return null;
  }
  document.querySelectorAll("[data-participant]").forEach((element) => {
    element.textContent = `Participant: ${name}`;
  });
  return name;
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let data;
  try {
    data = await response.json();
  } catch (_error) {
    throw new Error(`The server returned an unreadable response (${response.status}).`);
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status}).`);
  }
  return data;
}

function setStatus(element, message, isError = false) {
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("error", isError);
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function pathId(prefix) {
  const parts = window.location.pathname.split("/").filter(Boolean);
  if (parts.length !== 2 || parts[0] !== prefix || !parts[1]) return null;
  return parts[1];
}

function formatNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Failed";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(Number(value));
}

function svgElement(tag, attributes = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
  return node;
}

function svgText(parent, x, y, text, attributes = {}) {
  const node = svgElement("text", { x, y, ...attributes });
  node.textContent = text;
  parent.append(node);
}

function renderPie(container, summary) {
  container.replaceChildren();
  const counts = [Number(summary.true_count) || 0, Number(summary.false_count) || 0, Number(summary.null_count) || 0];
  const total = counts.reduce((sum, value) => sum + value, 0);
  const svg = svgElement("svg", { viewBox: "0 0 520 250", role: "img", "aria-label": `Boolean results: ${counts[0]} true, ${counts[1]} false, ${counts[2]} failed` });
  const colors = ["#245b43", "#b7695c", "#a7aea9"];
  const labels = ["True", "False", "Failed"];
  if (!total) {
    svgText(svg, 260, 125, "No results", { "text-anchor": "middle", fill: "#667169" });
    container.append(svg);
    return;
  }
  let angle = -Math.PI / 2;
  counts.forEach((count, index) => {
    if (!count) return;
    const next = angle + (count / total) * Math.PI * 2;
    const largeArc = next - angle > Math.PI ? 1 : 0;
    const x1 = 125 + 90 * Math.cos(angle);
    const y1 = 125 + 90 * Math.sin(angle);
    const x2 = 125 + 90 * Math.cos(next);
    const y2 = 125 + 90 * Math.sin(next);
    const d = count === total
      ? "M 125 35 A 90 90 0 1 1 124.99 35 Z"
      : `M 125 125 L ${x1} ${y1} A 90 90 0 ${largeArc} 1 ${x2} ${y2} Z`;
    svg.append(svgElement("path", { d, fill: colors[index], stroke: "#fff", "stroke-width": 2 }));
    angle = next;
  });
  labels.forEach((label, index) => {
    const y = 80 + index * 48;
    svg.append(svgElement("rect", { x: 285, y: y - 14, width: 16, height: 16, rx: 2, fill: colors[index] }));
    svgText(svg, 315, y, `${label}: ${counts[index]}`, { fill: "#17211c", "font-size": 16, "font-family": "system-ui, sans-serif" });
  });
  container.append(svg);
}

function histogramBins(values) {
  const numbers = values.map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  if (!numbers.length) return [];
  const min = numbers[0];
  const max = numbers[numbers.length - 1];
  if (min === max) return [{ start: min, end: max, count: numbers.length }];
  const binCount = Math.min(10, Math.max(3, Math.ceil(Math.sqrt(numbers.length))));
  const width = (max - min) / binCount;
  const bins = Array.from({ length: binCount }, (_, index) => ({ start: min + index * width, end: min + (index + 1) * width, count: 0 }));
  numbers.forEach((value) => {
    const index = Math.min(Math.floor((value - min) / width), binCount - 1);
    bins[index].count += 1;
  });
  return bins;
}

function renderHistogram(container, values) {
  container.replaceChildren();
  const bins = histogramBins(Array.isArray(values) ? values : []);
  const svg = svgElement("svg", { viewBox: "0 0 560 280", role: "img", "aria-label": `Histogram of ${values?.length || 0} numeric results` });
  if (!bins.length) {
    svgText(svg, 280, 140, "No numeric results", { "text-anchor": "middle", fill: "#667169" });
    container.append(svg);
    return;
  }
  const left = 48, top = 20, chartWidth = 490, chartHeight = 205;
  const maxCount = Math.max(...bins.map((bin) => bin.count), 1);
  svg.append(svgElement("line", { x1: left, y1: top + chartHeight, x2: left + chartWidth, y2: top + chartHeight, stroke: "#8d978f" }));
  const barWidth = chartWidth / bins.length;
  bins.forEach((bin, index) => {
    const height = (bin.count / maxCount) * (chartHeight - 12);
    const x = left + index * barWidth + 2;
    const y = top + chartHeight - height;
    svg.append(svgElement("rect", { x, y, width: Math.max(barWidth - 4, 1), height, rx: 2, fill: "#245b43" }));
    if (bin.count) svgText(svg, x + (barWidth - 4) / 2, y - 5, bin.count, { "text-anchor": "middle", fill: "#17211c", "font-size": 11 });
  });
  const first = bins[0].start;
  const last = bins[bins.length - 1].end;
  svgText(svg, left, 252, formatNumber(first), { "text-anchor": "start", fill: "#667169", "font-size": 12 });
  svgText(svg, left + chartWidth, 252, formatNumber(last), { "text-anchor": "end", fill: "#667169", "font-size": 12 });
  svgText(svg, left + chartWidth / 2, 273, "Value", { "text-anchor": "middle", fill: "#667169", "font-size": 12 });
  container.append(svg);
}

function renderSummary(container, entries) {
  container.replaceChildren();
  entries.forEach(([label, value]) => {
    container.append(element("dt", "", label), element("dd", "", value));
  });
}

function renderPreprocess(result) {
  const section = document.querySelector("#results-section");
  if (!result || result.activity !== "preprocess") return;
  const type = result.output_type;
  const radio = document.querySelector(`input[name="output-type"][value="${type}"]`);
  if (radio) radio.checked = true;
  const prompt = document.querySelector("#user-prompt");
  if (prompt) prompt.value = result.user_prompt || "";

  if (type === "boolean") {
    renderPie(document.querySelector("#preprocess-chart"), result.summary || {});
    renderSummary(document.querySelector("#preprocess-summary"), [
      ["True", result.summary?.true_count ?? 0],
      ["False", result.summary?.false_count ?? 0],
      ["Failed", result.summary?.null_count ?? 0],
    ]);
  } else {
    renderHistogram(document.querySelector("#preprocess-chart"), result.summary?.values || []);
    renderSummary(document.querySelector("#preprocess-summary"), [
      ["Minimum", formatNumber(result.summary?.min)],
      ["Q1", formatNumber(result.summary?.q1)],
      ["Median", formatNumber(result.summary?.median)],
      ["Q3", formatNumber(result.summary?.q3)],
      ["Maximum", formatNumber(result.summary?.max)],
    ]);
  }

  const items = Array.isArray(result.items) ? result.items : [];
  const list = document.querySelector("#preprocess-items");
  list.replaceChildren();
  items.forEach((item) => {
    const row = element("div", "result-row");
    const link = element("a", "", item.title || item.id);
    link.href = `/syllabus/${encodeURIComponent(item.id)}`;
    let value;
    let valueClass = "result-value";
    if (item.value === null || item.value === undefined) {
      value = "Failed";
      valueClass += " value-failed";
    } else if (type === "boolean") {
      value = item.value ? "True" : "False";
      valueClass += item.value ? " value-true" : " value-false";
    } else {
      value = formatNumber(item.value);
    }
    row.append(link, element("span", valueClass, value));
    list.append(row);
  });
  document.querySelector("#result-item-count").textContent = `(${items.length})`;
  section.hidden = false;
}

function renderAnalysis(result) {
  if (!result || result.activity !== "analysis") return;
  const prompt = document.querySelector("#user-prompt");
  if (prompt) prompt.value = result.user_prompt || "";
  const groups = document.querySelector("#analysis-results");
  groups.replaceChildren();
  const transcripts = Array.isArray(result.transcripts) ? result.transcripts : [];
  const withMatches = transcripts.filter((transcript) => Array.isArray(transcript.matches) && transcript.matches.length);
  if (!withMatches.length) {
    groups.append(element("p", "empty-state", "No matching utterances were identified."));
  }
  withMatches.forEach((transcript) => {
    const group = element("section", "transcript-group");
    const heading = element("h3");
    const link = element("a", "", transcript.name || transcript.id);
    link.href = `/transcript/${encodeURIComponent(transcript.id)}`;
    heading.append(link);
    group.append(heading, element("span", "match-count", `${transcript.matches.length} ${transcript.matches.length === 1 ? "match" : "matches"}`));
    transcript.matches.forEach((match) => {
      const matchBox = element("article", "match");
      const speaker = match.speaker || "Unknown speaker";
      const label = match.turn == null || match.turn === "" ? speaker : `Turn ${match.turn} · ${speaker}`;
      matchBox.append(
        element("p", "match-speaker", label),
        element("p", "match-utterance", match.utterance || ""),
        element("p", "match-context", match.context ? `Context: ${match.context}` : "Context unavailable"),
      );
      group.append(matchBox);
    });
    groups.append(group);
  });
  const total = Number(result.total_matches) || 0;
  document.querySelector("#match-total").textContent = `${total} ${total === 1 ? "match" : "matches"}`;
  document.querySelector("#results-section").hidden = false;
}

async function loadSystemPrompt(activity, outputType) {
  const textarea = document.querySelector("#system-prompt");
  textarea.value = "Loading…";
  const params = new URLSearchParams({ activity });
  if (outputType) params.set("output_type", outputType);
  try {
    const data = await api(`/api/system_prompt?${params}`);
    textarea.value = data.system_prompt || "";
  } catch (error) {
    textarea.value = "Unable to load the system prompt.";
    setStatus(document.querySelector("#run-message"), error.message, true);
  }
}

async function loadSavedResult(name, activity, renderer) {
  try {
    const data = await api(`/api/result?${new URLSearchParams({ name, activity })}`);
    if (data.result) renderer(data.result);
  } catch (error) {
    setStatus(document.querySelector("#run-message"), `Could not load saved result: ${error.message}`, true);
  }
}

function updateProgress(status) {
  const progress = document.querySelector("#run-progress");
  const total = Math.max(Number(status.total) || 0, 1);
  const completed = Math.max(Number(status.completed) || 0, 0);
  progress.max = total;
  progress.value = Math.min(completed, total);
  progress.textContent = `${Math.round((completed / total) * 100)}%`;
  document.querySelector("#progress-count").textContent = `${completed} / ${Number(status.total) || 0}`;
}

async function pollJob(jobId, renderer) {
  while (true) {
    const status = await api(`/api/status/${encodeURIComponent(jobId)}`);
    updateProgress(status);
    if (status.status === "done") {
      if (!status.result) throw new Error("The run finished without a result.");
      renderer(status.result);
      return;
    }
    if (status.status === "error") throw new Error(status.error || "The run failed.");
    if (status.status !== "running") throw new Error(`Unknown job status: ${status.status}`);
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
}

function configureRun({ name, activity, count, renderer, outputType }) {
  const button = document.querySelector("#run-button");
  const message = document.querySelector("#run-message");
  button.addEventListener("click", async () => {
    const prompt = document.querySelector("#user-prompt").value.trim();
    if (!prompt) {
      setStatus(message, "Enter a prompt before running.", true);
      document.querySelector("#user-prompt").focus();
      return;
    }
    const noun = activity === "preprocess" ? "syllabi" : "transcripts";
    if (!window.confirm(`Are you sure you want to run this over all ${count} ${noun}?`)) return;
    button.disabled = true;
    setStatus(message, "Starting run…");
    document.querySelector("#progress-section").hidden = false;
    document.querySelector("#run-progress").removeAttribute("value");
    document.querySelector("#progress-count").textContent = `0 / ${count}`;
    try {
      const body = { name, activity, user_prompt: prompt };
      if (outputType) body.output_type = outputType();
      const data = await api("/api/run", { method: "POST", body: JSON.stringify(body) });
      if (!data.job_id) throw new Error("The server did not return a job ID.");
      setStatus(message, "Run in progress…");
      await pollJob(data.job_id, renderer);
      setStatus(message, "Run complete. Results are shown below.");
      document.querySelector("#results-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setStatus(message, error.message, true);
    } finally {
      button.disabled = false;
    }
  });
}

async function initPreprocess(name) {
  const selectedType = () => document.querySelector('input[name="output-type"]:checked').value;
  document.querySelectorAll('input[name="output-type"]').forEach((radio) => {
    radio.addEventListener("change", () => loadSystemPrompt("preprocess", selectedType()));
  });
  configureRun({ name, activity: "preprocess", count: 50, renderer: renderPreprocess, outputType: selectedType });
  await Promise.all([loadSystemPrompt("preprocess", selectedType()), loadSavedResult(name, "preprocess", renderPreprocess)]);
  await loadSystemPrompt("preprocess", selectedType());
}

async function initAnalysis(name) {
  configureRun({ name, activity: "analysis", count: 30, renderer: renderAnalysis });
  await Promise.all([loadSystemPrompt("analysis"), loadSavedResult(name, "analysis", renderAnalysis)]);
}

async function initSyllabi() {
  const status = document.querySelector("#list-status");
  try {
    const data = await api("/api/syllabi");
    const items = Array.isArray(data.items) ? data.items : [];
    const list = document.querySelector("#syllabi-list");
    items.forEach((item) => {
      const link = element("a", "source-item");
      link.href = `/syllabus/${encodeURIComponent(item.id)}`;
      const copy = element("span");
      copy.append(element("span", "source-title", item.title || item.id));
      const metadata = [item.id, item.course_number, item.year].filter((value) => value !== null && value !== undefined && value !== "").join(" · ");
      copy.append(element("span", "source-meta", metadata));
      link.append(copy, element("span", "source-arrow", "→"));
      list.append(link);
    });
    setStatus(status, `${items.length} ${items.length === 1 ? "syllabus" : "syllabi"}`);
  } catch (error) {
    setStatus(status, error.message, true);
  }
}

async function initSyllabus() {
  const id = pathId("syllabus");
  const status = document.querySelector("#detail-status");
  if (!id) return setStatus(status, "Invalid syllabus ID.", true);
  try {
    const data = await api(`/api/syllabi/${encodeURIComponent(id)}`);
    document.title = `${data.title || "Syllabus"} · Workshop`;
    const content = document.querySelector("#syllabus-content");
    content.innerHTML = data.html || ""; // API contract guarantees safe, pre-rendered HTML.
    content.hidden = false;
    status.hidden = true;
  } catch (error) {
    setStatus(status, error.message, true);
  }
}

async function initTranscripts() {
  const status = document.querySelector("#list-status");
  try {
    const data = await api("/api/transcripts");
    const items = Array.isArray(data.items) ? data.items : [];
    const list = document.querySelector("#transcripts-list");
    items.forEach((item) => {
      const link = element("a", "source-item");
      link.href = `/transcript/${encodeURIComponent(item.id)}`;
      const copy = element("span");
      copy.append(element("span", "source-title", item.name || item.id));
      const count = Number(item.num_utterances) || 0;
      copy.append(element("span", "source-meta", `${count} ${count === 1 ? "utterance" : "utterances"}`));
      link.append(copy, element("span", "source-arrow", "→"));
      list.append(link);
    });
    setStatus(status, `${items.length} ${items.length === 1 ? "transcript" : "transcripts"}`);
  } catch (error) {
    setStatus(status, error.message, true);
  }
}

async function initTranscript() {
  const id = pathId("transcript");
  const status = document.querySelector("#detail-status");
  if (!id) return setStatus(status, "Invalid transcript ID.", true);
  try {
    const data = await api(`/api/transcripts/${encodeURIComponent(id)}`);
    document.title = `${data.name || "Transcript"} · Workshop`;
    document.querySelector("#transcript-name").textContent = data.name || data.id;
    const rows = document.querySelector("#transcript-rows");
    const utterances = Array.isArray(data.utterances) ? data.utterances : [];
    utterances.forEach((utterance) => {
      const row = element("tr");
      row.append(element("td", "", utterance.turn), element("td", "", utterance.speaker), element("td", "", utterance.text));
      rows.append(row);
    });
    document.querySelector("#transcript-content").hidden = false;
    status.hidden = true;
  } catch (error) {
    setStatus(status, error.message, true);
  }
}

function initName() {
  const input = document.querySelector("#participant-name");
  input.value = participantName();
  document.querySelector("#name-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) return;
    localStorage.setItem(PARTICIPANT_KEY, name);
    window.location.assign("/home");
  });
}

async function init() {
  const page = document.body.dataset.page;
  if (page === "name") return initName();
  const name = requireParticipant();
  if (!name) return;
  const handlers = {
    home: () => {},
    preprocess: () => initPreprocess(name),
    analysis: () => initAnalysis(name),
    syllabi: initSyllabi,
    syllabus: initSyllabus,
    transcripts: initTranscripts,
    transcript: initTranscript,
  };
  await handlers[page]?.();
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch((error) => {
    const target = document.querySelector("#run-message, #list-status, #detail-status");
    setStatus(target, error.message || "Something went wrong.", true);
  });
});
