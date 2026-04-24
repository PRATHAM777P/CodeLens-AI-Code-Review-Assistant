/**
 * Code Review Assistant — Frontend Logic
 * v2.0 — Security-hardened, feature-rich
 */

const API_BASE = "http://127.0.0.1:5000";
const MAX_HISTORY = 20;

/* ── State ───────────────────────────────────────────────────── */
let editor = null;
let currentResults = null;
let analysisHistory = [];

/* ── Monaco init ─────────────────────────────────────────────── */
require.config({ paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs" } });
require(["vs/editor/editor.main"], () => {
  editor = monaco.editor.create(document.getElementById("editor"), {
    value: getDefaultSnippet("python"),
    language: "python",
    theme: "vs-dark",
    automaticLayout: true,
    fontSize: 13,
    fontFamily: "'JetBrains Mono', monospace",
    lineNumbers: "on",
    minimap: { enabled: true },
    scrollBeyondLastLine: false,
    renderWhitespace: "selection",
    bracketPairColorization: { enabled: true },
    padding: { top: 12, bottom: 12 },
  });

  // Live code meta
  editor.onDidChangeModelContent(updateCodeMeta);
  updateCodeMeta();
});

function updateCodeMeta() {
  if (!editor) return;
  const model = editor.getModel();
  const lines = model.getLineCount();
  const chars = model.getValueLength();
  document.getElementById("codeMeta").textContent = `${lines} line${lines !== 1 ? "s" : ""} · ${chars.toLocaleString()} chars`;
}

/* ── Default code snippets ───────────────────────────────────── */
function getDefaultSnippet(lang) {
  const snippets = {
    python: `# Python example — try analyzing this!
def calculate_stats(numbers):
    total = 0
    for n in numbers:
        total = total + n
    average = total / len(numbers)  # potential ZeroDivisionError
    return {"total": total, "average": average}

data = [10, 20, 30, 40, 50]
print(calculate_stats(data))
`,
    javascript: `// JavaScript example
function fetchUserData(userId) {
  const url = "https://api.example.com/users/" + userId;  // potential injection
  return fetch(url)
    .then(response => response.json())
    .then(data => {
      console.log(data);
      return data;
    });
}
`,
    java: `public class Calculator {
    public static int divide(int a, int b) {
        return a / b;  // no division by zero check
    }

    public static void main(String[] args) {
        System.out.println(divide(10, 2));
    }
}
`,
    go: `package main

import "fmt"

func divide(a, b int) int {
    return a / b  // potential panic
}

func main() {
    fmt.Println(divide(10, 2))
}
`,
  };
  return snippets[lang] || `// Write your ${lang} code here\n`;
}

/* ── Language change ─────────────────────────────────────────── */
document.getElementById("language").addEventListener("change", (e) => {
  const lang = e.target.value;
  const monacoLang = { cpp: "cpp", c: "c", rust: "rust", typescript: "typescript" }[lang] || lang;
  if (editor) {
    monaco.editor.setModelLanguage(editor.getModel(), monacoLang);
    const current = editor.getValue().trim();
    // Only replace if it's still a default snippet
    const isDefault = Object.values({ python: true }).some(() =>
      current.startsWith("# Python example") || current.startsWith("// JavaScript") ||
      current.startsWith("public class") || current.startsWith("package main") ||
      current.startsWith("// Write your")
    );
    if (isDefault || current === "") {
      editor.setValue(getDefaultSnippet(lang));
    }
  }
});

/* ── Theme toggle ────────────────────────────────────────────── */
document.querySelectorAll(".theme-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".theme-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    if (editor) monaco.editor.setTheme(btn.dataset.theme);
  });
});

/* ── Tab switching (editor panel) ───────────────────────────── */
document.querySelectorAll(".tab[data-tab]").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab[data-tab]").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
  });
});

/* ── Tab switching (results panel) ──────────────────────────── */
document.querySelectorAll(".tab[data-result-tab]").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab[data-result-tab]").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".result-tab-content").forEach((c) => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`result-${tab.dataset.resultTab}`).classList.add("active");
  });
});

/* ── Prompt char counter ─────────────────────────────────────── */
document.getElementById("customPrompt").addEventListener("input", (e) => {
  const len = e.target.value.length;
  document.getElementById("promptCount").textContent = `${len} / 1000`;
});

/* ── Clear button ────────────────────────────────────────────── */
document.getElementById("clearBtn").addEventListener("click", () => {
  if (editor) editor.setValue("");
  document.getElementById("customPrompt").value = "";
  document.getElementById("promptCount").textContent = "0 / 1000";
});

/* ── Copy button ─────────────────────────────────────────────── */
document.getElementById("copyBtn").addEventListener("click", async () => {
  const code = editor ? editor.getValue() : "";
  if (!code.trim()) { showToast("Nothing to copy", "info"); return; }
  try {
    await navigator.clipboard.writeText(code);
    showToast("Code copied!", "success");
  } catch {
    showToast("Copy failed", "error");
  }
});

/* ── Export button ───────────────────────────────────────────── */
document.getElementById("exportBtn").addEventListener("click", () => {
  if (!currentResults) { showToast("No results to export", "info"); return; }
  const blob = new Blob([JSON.stringify(currentResults, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `code-review-${Date.now()}.json`;
  a.click();
  showToast("Results exported", "success");
});

/* ── Error banner ────────────────────────────────────────────── */
document.getElementById("errorClose").addEventListener("click", () => {
  document.getElementById("errorBanner").classList.add("hidden");
});

/* ── Health check ────────────────────────────────────────────── */
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    const badge = document.getElementById("statusBadge");
    if (res.ok) {
      badge.textContent = "● ONLINE";
      badge.classList.add("online");
    } else {
      badge.textContent = "● OFFLINE";
      badge.classList.remove("online");
    }
  } catch {
    // Server not available
  }
}
checkHealth();
setInterval(checkHealth, 15_000);

/* ── Main analyze ────────────────────────────────────────────── */
document.getElementById("analyzeBtn").addEventListener("click", analyze);

async function analyze() {
  if (!editor) return;
  const code = editor.getValue().trim();
  const language = document.getElementById("language").value;
  const prompt = document.getElementById("customPrompt").value.trim();

  if (!code) { showToast("Please write some code first", "error"); return; }
  if (code.length > 50_000) { showToast("Code is too long (max 50,000 chars)", "error"); return; }

  setLoading(true);
  hideError();

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language, prompt: prompt || undefined }),
      signal: AbortSignal.timeout(60_000),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Server returned an error");
      setLoading(false);
      return;
    }

    currentResults = data;
    renderResults(data);
    addToHistory({ code, language, prompt, results: data, time: new Date().toISOString() });
    showToast("Analysis complete!", "success");

    // Switch to overview tab
    document.querySelector(".tab[data-result-tab='overview']").click();

  } catch (err) {
    if (err.name === "TimeoutError") {
      showError("Request timed out. Is the Flask server running?");
    } else if (err.name === "TypeError") {
      showError("Cannot connect to server. Run: python backend/app.py");
    } else {
      showError(err.message || "Unknown error");
    }
  } finally {
    setLoading(false);
  }
}

/* ── Render results ──────────────────────────────────────────── */
function renderResults(data) {
  const { quality = [], security = [], suggestions = [], complexity = {}, custom_ai_response, lines, chars } = data;

  // Hide welcome, show grid
  document.getElementById("welcomeState").classList.add("hidden");
  const grid = document.getElementById("overviewGrid");
  grid.classList.remove("hidden");

  const qCount = quality.filter((q) => !q.startsWith("✅")).length;
  const sCount = security.filter((s) => !s.startsWith("✅")).length;

  setMetric("qualityCount", qCount, qCount === 0 ? "good" : qCount < 5 ? "warn" : "bad");
  setMetric("securityCount", sCount, sCount === 0 ? "good" : sCount < 3 ? "warn" : "bad");
  setMetric("suggestCount", suggestions.length, "good");
  setMetric("complexityLevel", complexity.overall || "?",
    { Low: "good", Medium: "warn", High: "bad", Critical: "bad" }[complexity.overall] || "");

  document.getElementById("complexityDetail").innerHTML =
    `<strong>Complexity:</strong> Cyclomatic ≈ ${complexity.cyclomatic ?? "N/A"} &nbsp;·&nbsp; ` +
    `Maintainability: ${complexity.maintainability ?? "N/A"}/100 &nbsp;·&nbsp; ` +
    `<em>${escHtml(complexity.summary || "")}</em>` +
    `<br><small style="color:var(--text-2)">${lines ?? "?"} lines · ${(chars ?? 0).toLocaleString()} chars</small>`;

  renderIssueList("qualityList", quality, "qualityBadge");
  renderIssueList("securityList", security, "securityBadge");
  renderIssueList("suggestionList", suggestions, "suggestBadge");

  // AI tab
  const aiBox = document.getElementById("aiResponseBox");
  if (custom_ai_response) {
    aiBox.innerHTML = escHtml(custom_ai_response).replace(/\n/g, "<br>");
  } else {
    aiBox.innerHTML = `<p class="ai-placeholder">No custom question was asked. Enter a question in the prompt field and re-run the analysis.</p>`;
  }
}

function setMetric(id, value, cls) {
  const el = document.getElementById(id);
  el.textContent = value;
  el.className = "metric-value " + (cls || "");
}

function renderIssueList(listId, items, badgeId) {
  const list = document.getElementById(listId);
  const badge = document.getElementById(badgeId);
  badge.textContent = items.length;
  list.innerHTML = "";
  items.forEach((item, i) => {
    const cls = classifyIssue(item);
    const div = document.createElement("div");
    div.className = `issue-item ${cls}`;
    div.style.animationDelay = `${i * 0.04}s`;
    div.innerHTML = `<div class="issue-dot"></div><span>${escHtml(item)}</span>`;
    list.appendChild(div);
  });
}

function classifyIssue(msg) {
  if (msg.startsWith("✅") || msg.toLowerCase().includes("no issue") || msg.toLowerCase().includes("no security")) return "ok";
  if (msg.startsWith("❌") || msg.toLowerCase().includes("error") || msg.toLowerCase().includes("critical")) return "error";
  if (msg.startsWith("⚠️") || msg.toLowerCase().includes("warning") || msg.toLowerCase().includes("warn")) return "warn";
  return "info";
}

/* ── History ─────────────────────────────────────────────────── */
function addToHistory(entry) {
  analysisHistory.unshift(entry);
  if (analysisHistory.length > MAX_HISTORY) analysisHistory.pop();
  renderHistory();
}

function renderHistory() {
  const list = document.getElementById("historyList");
  if (analysisHistory.length === 0) {
    list.innerHTML = `<div class="empty-state"><svg width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg><p>No history yet.</p></div>`;
    return;
  }
  list.innerHTML = "";
  analysisHistory.forEach((entry, i) => {
    const div = document.createElement("div");
    div.className = "history-item";
    const preview = entry.code.split("\n")[0].substring(0, 60);
    const time = new Date(entry.time).toLocaleTimeString();
    div.innerHTML = `
      <div class="history-item-lang">${entry.language}</div>
      <div class="history-item-preview">${escHtml(preview)}…</div>
      <div class="history-item-time">${time}</div>
    `;
    div.addEventListener("click", () => {
      if (editor) editor.setValue(entry.code);
      document.getElementById("language").value = entry.language;
      currentResults = entry.results;
      renderResults(entry.results);
      document.querySelector(".tab[data-tab='editor']").click();
      showToast("History loaded", "info");
    });
    list.appendChild(div);
  });
}

/* ── Toast & errors ──────────────────────────────────────────── */
function showToast(msg, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  toast.innerHTML = `<span>${icons[type] || ""}</span><span>${escHtml(msg)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "slideIn .3s ease reverse";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function showError(msg) {
  document.getElementById("errorMsg").textContent = msg;
  document.getElementById("errorBanner").classList.remove("hidden");
}
function hideError() {
  document.getElementById("errorBanner").classList.add("hidden");
}

/* ── Loader ──────────────────────────────────────────────────── */
function setLoading(on) {
  const btn = document.getElementById("analyzeBtn");
  const text = btn.querySelector(".btn-text");
  const loader = btn.querySelector(".btn-loader");
  btn.disabled = on;
  text.classList.toggle("hidden", on);
  loader.classList.toggle("hidden", !on);
}

/* ── Security: HTML escaping ─────────────────────────────────── */
function escHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(String(str)));
  return div.innerHTML;
}

/* ── Keyboard shortcut: Ctrl/Cmd+Enter to analyze ───────────── */
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    analyze();
  }
});
