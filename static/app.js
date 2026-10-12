// Vanilla-JS frontend for LeafCheck.
// No external CDN requests, no framework. Talks to the same FastAPI
// service that hosts this page.

import { t, I18N } from "./i18n.js";

const $ = (sel) => document.querySelector(sel);

const state = {
  lang: localStorage.getItem("leafcheck.lang") === "bn" ? "bn" : "en",
  file: null,
};

function applyI18n() {
  document.documentElement.lang = state.lang;
  for (const id of ["title", "tagline", "pickOrDrop", "pickButton", "useCamera", "predict", "disclaimer"]) {
    const el = document.getElementById(id);
    if (el) el.textContent = t(id, state.lang);
  }
  document.getElementById("langToggle").textContent = t("langToggle", state.lang);
}

function setLang(lang) {
  state.lang = lang;
  localStorage.setItem("leafcheck.lang", lang);
  applyI18n();
  renderResult(state.lastResult);
}

function pickFile() {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = "image/jpeg,image/png,image/webp";
  inp.onchange = () => {
    if (inp.files && inp.files[0]) {
      onFile(inp.files[0]);
    }
  };
  inp.click();
}

async function takePhoto() {
  // The browser's getUserMedia / <input type="file" capture="environment">
  // path is the simplest portable thing and avoids the canvas/cap quirks
  // of older mobile browsers.
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = "image/*";
  inp.setAttribute("capture", "environment");
  inp.onchange = () => {
    if (inp.files && inp.files[0]) onFile(inp.files[0]);
  };
  inp.click();
}

async function onFile(file) {
  // Client-side guard: reject anything > 5 MB before we even try the
  // upload (server enforces the same limit but this saves a round-trip).
  if (file.size > 5 * 1024 * 1024) {
    showError(state.lang === "bn"
      ? "ফাইল ৫ মেগাবাইটের বেশি।"
      : "File is larger than 5 MB.");
    return;
  }
  state.file = file;
  const url = URL.createObjectURL(file);
  $("#preview").src = url;
  $("#preview").style.display = "block";
  $("#dropzone").classList.add("has-file");
  $("#predict").disabled = false;
}

async function downscaleIfNeeded(file, maxDim = 1024) {
  // Client-side downscale to ≤ maxDim before upload (F6.AC3).
  const url = URL.createObjectURL(file);
  const img = await new Promise((res, rej) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = rej;
    i.src = url;
  });
  if (img.naturalWidth <= maxDim && img.naturalHeight <= maxDim) {
    URL.revokeObjectURL(url);
    return file;
  }
  const scale = Math.min(maxDim / img.naturalWidth, maxDim / img.naturalHeight);
  const w = Math.round(img.naturalWidth * scale);
  const h = Math.round(img.naturalHeight * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, w, h);
  const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.85));
  URL.revokeObjectURL(url);
  return new File([blob], file.name.replace(/\.[^.]+$/, "") + ".jpg", {
    type: "image/jpeg",
  });
}

async function predict() {
  if (!state.file) return;
  $("#predict").disabled = true;
  $("#predict").textContent = t("predicting", state.lang);
  $("#result").innerHTML = "";
  try {
    const downscaled = await downscaleIfNeeded(state.file);
    const fd = new FormData();
    fd.append("file", downscaled, downscaled.name);
    const r = await fetch("/api/predict", { method: "POST", body: fd });
    if (!r.ok) {
      const j = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(j.detail || `${r.status}`);
    }
    const result = await r.json();
    state.lastResult = result;
    renderResult(result);
  } catch (err) {
    showError(String(err.message || err));
  } finally {
    $("#predict").disabled = false;
    $("#predict").textContent = t("predict", state.lang);
  }
}

function renderResult(result) {
  const el = $("#result");
  if (!result) {
    el.innerHTML = "";
    return;
  }
  if (result.not_sure) {
    const tips = t("retakeTips", state.lang)
      .map((tip) => `<li>${escapeHtml(tip)}</li>`)
      .join("");
    el.innerHTML = `
      <div class="card not-sure">
        <h2>${escapeHtml(t("notSure", state.lang))}</h2>
        <ul>${tips}</ul>
      </div>`;
    return;
  }
  const top = result.top_k[0];
  const others = result.top_k.slice(1);
  const adviceHtml = result.advice
    ? `<div class="advice"><h3>${escapeHtml(t("advice", state.lang))}</h3>
         <p>${escapeHtml(state.lang === "bn" ? result.advice.bn : result.advice.en)}</p></div>`
    : "";
  const otherHtml = others.length
    ? `<details><summary>${escapeHtml(t("otherGuesses", state.lang))}</summary>
        <ul class="other">${others
          .map((o) => `<li><span class="cls">${escapeHtml(o.class)}</span>
            <span class="conf">${(o.confidence * 100).toFixed(1)}%</span></li>`)
          .join("")}</ul></details>`
    : "";
  el.innerHTML = `
    <div class="card">
      <h2>${escapeHtml(t("topClass", state.lang))}</h2>
      <div class="top">
        <span class="cls">${escapeHtml(top.class)}</span>
        <div class="bar"><div class="fill" style="width: ${(top.confidence * 100).toFixed(1)}%"></div></div>
        <span class="conf">${(top.confidence * 100).toFixed(1)}%</span>
      </div>
      ${otherHtml}
      ${adviceHtml}
    </div>`;
}

function showError(msg) {
  $("#result").innerHTML = `
    <div class="card error">
      <h2>${escapeHtml(t("error", state.lang))}</h2>
      <p>${escapeHtml(msg)}</p>
    </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function wireDropzone() {
  const dz = $("#dropzone");
  ["dragenter", "dragover"].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.add("dragging");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.remove("dragging");
    })
  );
  dz.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFile(e.dataTransfer.files[0]);
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  applyI18n();
  $("#pickButton").addEventListener("click", pickFile);
  $("#useCamera").addEventListener("click", takePhoto);
  $("#predict").addEventListener("click", predict);
  $("#langToggle").addEventListener("click", () => setLang(state.lang === "en" ? "bn" : "en"));
  wireDropzone();
});