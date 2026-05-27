const API_BASE = "/api";
let currentSource = "image";
let currentFilePath = null;
let currentFileUrl = null;
let currentFileName = null;
let currentFileSize = 0;
let ws = null;
let mediaStream = null;
let streamActive = false;
let isSegmenting = false;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const uploadArea = $("#upload-area");
const uploadContent = $("#upload-content");
const uploadPreview = $("#upload-preview");
const fileInput = $("#file-input");
const previewImg = $("#preview-img");
const previewVideo = $("#preview-video");
const btnSegment = $("#btn-segment");
const btnChange = $("#btn-change");
const originalView = $("#original-view");
const originalVideoView = $("#original-video-view");
const segmentedView = $("#segmented-view");
const segmentedVideoView = $("#segmented-video-view");
const originalPane = $("#original-pane");
const segmentedPane = $("#segmented-pane");
const viewerStats = $("#viewer-stats");
const statsMasks = $("#stats-masks");
const statsTime = $("#stats-time");
const sourceName = $("#source-name");
const modelSelect = $("#model-select");
const modelStatus = $("#model-status");
const streamControls = $("#stream-controls");
const webcamFeed = $("#webcam-feed");
const btnStartStream = $("#btn-start-stream");
const btnStopStream = $("#btn-stop-stream");
const progressBar = $("#progress-bar");
const progressText = $("#progress-text");
const metadataSection = $("#metadata-section");
const metadataGrid = $("#metadata-grid");
const historyToggle = $("#history-toggle");
const historyList = $("#history-list");
const historyCount = $("#history-count");

document.addEventListener("DOMContentLoaded", async () => {
  await loadModels();
  await checkStatus();
  setupTabs();
  setupDragDrop();
  setupButtons();
  setupModelSwitch();
  setupHistory();
});

// ---- API ----

async function loadModels() {
  try {
    const res = await fetch(`${API_BASE}/models`);
    const data = await res.json();
    modelSelect.innerHTML = "";
    data.models.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.name;
      opt.textContent = m.display_name;
      if (m.loaded) opt.selected = true;
      modelSelect.appendChild(opt);
    });
  } catch (e) {
    console.error("Failed to load models", e);
  }
}

async function checkStatus() {
  try {
    const res = await fetch(`${API_BASE}/status`);
    const data = await res.json();
    modelStatus.textContent = data.model_loaded ? "ready" : "not loaded";
    modelStatus.className = `status-badge ${data.model_loaded ? "ready" : "error"}`;
  } catch (e) {
    modelStatus.textContent = "offline";
    modelStatus.className = "status-badge error";
  }
}

async function switchModel(name) {
  const fd = new FormData();
  fd.append("model_name", name);
  modelStatus.textContent = "loading...";
  modelStatus.className = "status-badge loading";
  try {
    await fetch(`${API_BASE}/models/switch`, { method: "POST", body: fd });
    await checkStatus();
  } catch (e) {
    modelStatus.textContent = "error";
    modelStatus.className = "status-badge error";
  }
}

// ---- Tabs ----

function setupTabs() {
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentSource = tab.dataset.source;
      switchSource(currentSource);
    });
  });
}

function switchSource(source) {
  resetViewer();
  clearMetadata();
  const isStream = source === "stream";

  uploadArea.classList.toggle("hidden", isStream);
  streamControls.classList.toggle("hidden", !isStream);

  if (isStream) {
    stopStream();
    fileInput.value = "";
    currentFilePath = null;
  } else {
    if (mediaStream) stopStream();
    resetUpload();
  }

  fileInput.accept = source === "image" ? "image/*" : "video/*";
}

// ---- Upload ----

function setupDragDrop() {
  uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
  });
  uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("dragover");
  });
  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length) handleFile(files[0]);
  });

  uploadContent.addEventListener("click", () => {
    if (uploadPreview.classList.contains("hidden")) {
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
  });
}

function handleFile(file) {
  currentFileName = file.name;
  currentFileSize = file.size;
  const isVideo = file.type.startsWith("video/");

  if (isVideo && currentSource === "image") {
    $$(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelector('.tab[data-source="video"]').classList.add("active");
    currentSource = "video";
  }

  const url = URL.createObjectURL(file);
  uploadContent.classList.add("hidden");
  uploadPreview.classList.remove("hidden");

  if (isVideo) {
    previewImg.classList.add("hidden");
    previewVideo.classList.remove("hidden");
    previewVideo.src = url;
    previewVideo.onloadedmetadata = () => showMetadata(file, previewVideo);
  } else {
    previewVideo.classList.add("hidden");
    previewImg.classList.remove("hidden");
    previewImg.src = url;
    previewImg.onload = () => showMetadata(file, previewImg);
  }

  sourceName.textContent = file.name;
  currentFilePath = null;
  currentFileUrl = null;
  uploadToServer(file);
}

async function uploadToServer(file) {
  const fd = new FormData();
  fd.append("file", file);
  btnSegment.disabled = true;
  btnSegment.textContent = "Uploading...";

  try {
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
    const data = await res.json();
    if (data.error) {
      alert(data.error);
      resetUpload();
      return;
    }
    currentFilePath = data.file_path;
    const rel = currentFilePath.split("uploads/")[1] || currentFilePath;
    currentFileUrl = `/uploads/${rel}`;
    btnSegment.disabled = false;
    btnSegment.textContent = "Segment";
    showOriginal();
  } catch (e) {
    alert("Upload failed");
    resetUpload();
  }
}

function showOriginal() {
  if (!currentFileUrl) return;
  const isVideo = currentSource === "video";

  if (isVideo) {
    originalVideoView.classList.remove("hidden");
    originalView.classList.add("hidden");
    originalVideoView.src = currentFileUrl;
  } else {
    originalView.classList.remove("hidden");
    originalVideoView.classList.add("hidden");
    originalView.src = currentFileUrl;
  }
  originalPane.querySelector(".viewer-placeholder").classList.add("hidden");
}

// ---- Metadata ----

function showMetadata(file, media) {
  const items = [];
  items.push({ label: "Name", value: file.name });
  items.push({ label: "Size", value: formatFileSize(file.size) });

  if (media.tagName === "IMG") {
    items.push({ label: "Dimensions", value: `${media.naturalWidth} × ${media.naturalHeight} px` });
    items.push({ label: "Megapixels", value: ((media.naturalWidth * media.naturalHeight) / 1e6).toFixed(2) });
  } else if (media.tagName === "VIDEO") {
    items.push({ label: "Dimensions", value: `${media.videoWidth} × ${media.videoHeight} px` });
    items.push({ label: "Duration", value: formatDuration(media.duration) });
  }

  metadataGrid.innerHTML = items.map((i) =>
    `<div class="metadata-item"><span class="metadata-label">${i.label}</span><span class="metadata-value">${i.value}</span></div>`
  ).join("");
  metadataSection.classList.remove("hidden");
}

function clearMetadata() {
  metadataSection.classList.add("hidden");
  metadataGrid.innerHTML = "";
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// ---- Segmentation ----

async function runSegmentation() {
  if (!currentFilePath || isSegmenting) return;

  isSegmenting = true;
  btnSegment.disabled = true;
  btnSegment.textContent = "Segmenting";
  progressBar.classList.remove("hidden");
  progressText.textContent = "Segmenting...";

  const fd = new FormData();
  fd.append("file_path", currentFilePath);
  if (currentSource !== "video") {
    fd.append("model_name", modelSelect.value);
  }

  const t0 = performance.now();
  const endpoint = currentSource === "video" ? `${API_BASE}/segment/video` : `${API_BASE}/segment`;

  try {
    const res = await fetch(endpoint, { method: "POST", body: fd });
    const data = await res.json();

    if (data.error) {
      alert(data.error);
      isSegmenting = false;
      btnSegment.disabled = false;
      btnSegment.textContent = "Segment";
      progressBar.classList.add("hidden");
      return;
    }

    const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
    statsTime.textContent = `Time: ${elapsed}s`;

    if (currentSource === "video") {
      segmentedVideoView.classList.remove("hidden");
      segmentedView.classList.add("hidden");
      segmentedVideoView.src = data.video_url;
      segmentedPane.querySelector(".viewer-placeholder").classList.add("hidden");
      statsMasks.textContent = `Frames: ${data.frames_processed || 0}`;
      addHistoryItem({
        file_name: currentFileName,
        model_name: modelSelect.value,
        mask_count: data.frames_processed || 0,
        computation_time: parseFloat(elapsed),
        timestamp: new Date().toISOString(),
        original_url: currentFileUrl,
        overlay_url: data.video_url,
        is_video: true,
      });
    } else {
      segmentedView.classList.remove("hidden");
      segmentedVideoView.classList.add("hidden");
      segmentedView.src = data.overlay_url;
      segmentedPane.querySelector(".viewer-placeholder").classList.add("hidden");
      statsMasks.textContent = `Masks: ${data.num_masks || 0}`;
      addHistoryItem({
        file_name: currentFileName,
        model_name: data.model_name,
        mask_count: data.num_masks || 0,
        computation_time: data.computation_time || parseFloat(elapsed),
        timestamp: new Date().toISOString(),
        original_url: currentFileUrl,
        overlay_url: data.overlay_url,
        mask_url: data.mask_url,
        is_video: false,
      });
    }

    viewerStats.classList.remove("hidden");
  } catch (e) {
    alert("Segmentation failed");
  }

  isSegmenting = false;
  btnSegment.disabled = false;
  btnSegment.textContent = "Segment";
  progressBar.classList.add("hidden");
}

// ---- Stream ----

function setupStream() {
  btnStartStream.addEventListener("click", startStream);
  btnStopStream.addEventListener("click", stopStream);
}

async function startStream() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
    webcamFeed.srcObject = mediaStream;
    streamActive = true;

    btnStartStream.classList.add("hidden");
    btnStopStream.classList.remove("hidden");

    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}${API_BASE}/stream`);

    ws.onopen = () => {
      segmentedPane.querySelector(".viewer-placeholder").classList.add("hidden");
      sendFrames();
    };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.overlay) {
        segmentedView.src = `data:image/jpeg;base64,${data.overlay}`;
        segmentedView.classList.remove("hidden");
      }
    };

    ws.onclose = () => cleanupStream();
    ws.onerror = () => cleanupStream();
  } catch (e) {
    alert("Camera access denied or not available");
  }
}

function sendFrames() {
  if (!streamActive || !ws || ws.readyState !== WebSocket.OPEN) {
    streamActive = false;
    return;
  }

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");
  canvas.width = webcamFeed.videoWidth || 640;
  canvas.height = webcamFeed.videoHeight || 480;
  ctx.drawImage(webcamFeed, 0, 0);
  const b64 = canvas.toDataURL("image/jpeg", 0.6);

  ws.send(JSON.stringify({ action: "segment", image: b64 }));
  setTimeout(sendFrames, 200);
}

function stopStream() {
  streamActive = false;
  if (ws) {
    ws.close();
    ws = null;
  }
  cleanupStream();
}

function cleanupStream() {
  streamActive = false;
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop());
    mediaStream = null;
  }
  btnStartStream.classList.remove("hidden");
  btnStopStream.classList.add("hidden");
  webcamFeed.srcObject = null;
}

// ---- History ----

function setupHistory() {
  historyToggle.addEventListener("click", () => {
    historyList.classList.toggle("hidden");
  });
  loadHistory();
}

async function loadHistory() {
  try {
    const res = await fetch(`${API_BASE}/history`);
    const data = await res.json();
    const tasks = data.tasks || [];
    renderHistory(tasks);
  } catch (e) {
    console.error("Failed to load history", e);
  }
}

function renderHistory(tasks) {
  historyList.innerHTML = "";
  const visible = !historyList.classList.contains("hidden");
  historyList.classList.remove("hidden");

  if (tasks.length === 0) {
    historyList.innerHTML = '<div class="history-empty">No tasks yet</div>';
    historyCount.textContent = "0";
    if (!visible) historyList.classList.add("hidden");
    return;
  }

  historyCount.textContent = tasks.length;

  tasks.forEach((t) => {
    const item = document.createElement("div");
    item.className = "history-item";
    item.dataset.taskId = t.task_id;

    const isVideo = t.mask_url === null || t.mask_url === undefined;
    const overlaySrc = t.overlay_url || "";
    const originalSrc = t.original_url || "";
    const date = t.timestamp ? new Date(t.timestamp).toLocaleString() : "";

    item.innerHTML = `
      <div class="history-thumbs">
        <img class="history-thumb" src="${originalSrc}" alt="original" loading="lazy"
          onerror="this.style.display='none'" />
        <img class="history-thumb" src="${overlaySrc}" alt="segmented" loading="lazy"
          onerror="this.style.display='none'" />
      </div>
      <div class="history-info">
        <div class="history-info-name">${escapeHtml(t.file_name || "unknown")}</div>
        <div class="history-info-meta">
          <span>${isVideo ? "Frames" : "Masks"}: ${t.mask_count}</span>
          <span>${t.computation_time ? t.computation_time + "s" : ""}</span>
          <span>${t.model_name || ""}</span>
          <span>${date}</span>
        </div>
      </div>
    `;

    item.addEventListener("click", () => restoreHistoryItem(t));
    historyList.appendChild(item);
  });

  if (!visible) historyList.classList.add("hidden");
}

function addHistoryItem(data) {
  loadHistory();
}

function restoreHistoryItem(task) {
  if (task.original_url) {
    const isVideo = task.is_video || task.mask_url === null || task.mask_url === undefined;
    if (isVideo) {
      originalVideoView.classList.remove("hidden");
      originalView.classList.add("hidden");
      originalVideoView.src = task.original_url;
    } else {
      originalView.classList.remove("hidden");
      originalVideoView.classList.add("hidden");
      originalView.src = task.original_url;
    }
    originalPane.querySelector(".viewer-placeholder").classList.add("hidden");
    currentFileUrl = task.original_url;
    currentFileName = task.file_name;
  }

  if (task.overlay_url) {
    if (task.is_video || task.mask_url === null || task.mask_url === undefined) {
      segmentedVideoView.classList.remove("hidden");
      segmentedView.classList.add("hidden");
      segmentedVideoView.src = task.overlay_url;
      segmentedPane.querySelector(".viewer-placeholder").classList.add("hidden");
      statsMasks.textContent = `Frames: ${task.mask_count || 0}`;
    } else {
      segmentedView.classList.remove("hidden");
      segmentedVideoView.classList.add("hidden");
      segmentedView.src = task.overlay_url;
      segmentedPane.querySelector(".viewer-placeholder").classList.add("hidden");
      statsMasks.textContent = `Masks: ${task.mask_count || 0}`;
    }
  }

  viewerStats.classList.remove("hidden");
  statsTime.textContent = `Time: ${task.computation_time || "?"}s`;

  sourceName.textContent = task.file_name || "";
}

// ---- Helpers ----

function resetUpload() {
  uploadContent.classList.remove("hidden");
  uploadPreview.classList.add("hidden");
  previewImg.src = "";
  previewVideo.src = "";
  fileInput.value = "";
  currentFilePath = null;
  currentFileUrl = null;
  currentFileName = null;
  currentFileSize = 0;
  btnSegment.disabled = false;
  btnSegment.textContent = "Segment";
  clearMetadata();
}

function resetViewer() {
  originalView.classList.add("hidden");
  originalVideoView.classList.add("hidden");
  segmentedView.classList.add("hidden");
  segmentedVideoView.classList.add("hidden");
  viewerStats.classList.add("hidden");
  originalPane.querySelector(".viewer-placeholder").classList.remove("hidden");
  segmentedPane.querySelector(".viewer-placeholder").classList.remove("hidden");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function setupButtons() {
  btnSegment.addEventListener("click", runSegmentation);
  btnChange.addEventListener("click", resetUpload);
  setupStream();
}

function setupModelSwitch() {
  modelSelect.addEventListener("change", () => {
    switchModel(modelSelect.value);
  });
}
