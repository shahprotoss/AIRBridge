(() => {
  "use strict";

  // Larger requests and a small number of concurrent files reduce round trips,
  // without introducing a file-size or batch-size limit.
  const CHUNK_BYTES = 16 * 1024 * 1024;
  const CONCURRENT_FILES = 3;
  const token = new URL(location.href).searchParams.get("k") || "";
  history.replaceState({}, "", "/");

  const input = document.getElementById("files");
  const send = document.getElementById("send");
  const selected = document.getElementById("selected");
  const status = document.getElementById("status");
  const progress = document.getElementById("progress");
  const bar = document.getElementById("bar");
  const speed = document.getElementById("speed");
  const i18n = window.AIRBridgeI18n;
  const t = i18n.t;
  let busy = false;
  let currentStatus = { key: "status_ready", args: {}, prefix: "" };
  let currentSpeed = null;

  function setStatus(key, args = {}, prefix = "") {
    currentStatus = { key, args, prefix };
    status.textContent = prefix + t(key, args);
  }

  function setSpeed(key, args = {}) {
    currentSpeed = { key, args };
    speed.textContent = t(key, args);
  }

  function error(key, values = {}) {
    const problem = new Error(key);
    problem.translationKey = key;
    problem.values = values;
    return problem;
  }

  document.querySelectorAll("[data-lang]").forEach(button => {
    button.addEventListener("click", () => {
      i18n.setLanguage(button.dataset.lang);
      selection();
      setStatus(currentStatus.key, currentStatus.args, currentStatus.prefix);
      if (currentSpeed) setSpeed(currentSpeed.key, currentSpeed.args);
      send.textContent = t(busy ? "sending" : "send_button");
    });
  });

  const fmt = n => {
    const units = ["B", "KB", "MB", "GB", "TB", "PB"];
    let i = 0;
    while (n >= 1024 && i < units.length - 1) {
      n /= 1024;
      i++;
    }
    return (i === 0 ? n : n.toFixed(1)) + " " + units[i];
  };
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  function selection() {
    const files = Array.from(input.files);
    selected.hidden = files.length === 0;
    selected.textContent = files.length ? t("selection", {
      count: files.length,
      size: fmt(files.reduce((sum, f) => sum + f.size, 0)),
      names: files.slice(0, 5).map(f => f.name).join(", ")
    }) : "";
    send.disabled = busy || files.length === 0;
  }
  input.addEventListener("change", selection);

  async function api(path, options = {}) {
    const response = await fetch(path, {
      cache: "no-store",
      ...options,
      headers: { "X-Drop-Token": token, ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw error("server_error", { code: response.status });
    return body;
  }

  function uploadChunk(offerId, index, offset, part, onProgress) {
    return new Promise((resolve, reject) => {
      const req = new XMLHttpRequest();
      req.open("POST", "/api/upload?id=" + encodeURIComponent(offerId) +
        "&index=" + index + "&offset=" + offset);
      req.setRequestHeader("X-Drop-Token", token);
      req.timeout = 5 * 60 * 1000;
      req.upload.onprogress = event => {
        if (event.lengthComputable) onProgress(event.loaded);
      };
      req.onload = () => {
        let body = {};
        try { body = JSON.parse(req.responseText); } catch (_) {}
        if (req.status === 200) resolve(body);
        else reject(error("server_error", { code: req.status }));
      };
      req.onerror = () => reject(error("connection_lost"));
      req.ontimeout = () => reject(error("upload_timeout"));
      req.send(part);
    });
  }

  async function uploadFile(offerId, index, file, report) {
    let offset = 0;
    // An empty file still needs one zero-byte request to create it on Windows.
    while (offset < file.size || (file.size === 0 && offset === 0)) {
      const end = Math.min(offset + CHUNK_BYTES, file.size);
      const chunk = file.slice(offset, end);
      let delivered = false;

      for (let attempt = 0; attempt < 4; attempt++) {
        try {
          const answer = await uploadChunk(offerId, index, offset, chunk, bytes => {
            report(index, offset + bytes);
          });
          if (answer.next_offset !== end && !(answer.done && end === file.size)) {
            throw error("chunk_mismatch");
          }
          delivered = true;
          break;
        } catch (err) {
          report(index, offset);
          // A server may have written a chunk even when its reply was lost.
          let state = null;
          try {
            state = await api("/api/status?id=" + encodeURIComponent(offerId) +
              "&index=" + index);
          } catch (_) {
            // Temporary network problem; retry.
          }
          if (state && state.file_offset === end && (end > offset || state.file_done)) {
            delivered = true;
            break;
          }
          if ((state && state.file_offset !== offset) || attempt === 3) throw err;
          await sleep(800 * (attempt + 1));
        }
      }
      if (!delivered) throw error("chunk_failed");
      offset = end;
      report(index, offset);
      if (file.size === 0) break;
    }
  }

  send.addEventListener("click", async () => {
    if (busy) return;
    const files = Array.from(input.files);
    if (!files.length) return;
    const total = files.reduce((sum, f) => sum + f.size, 0);
    busy = true;
    selection();
    status.classList.remove("is-success", "is-error");
    send.textContent = t("sending");
    currentSpeed = null;
    speed.textContent = "";
    progress.hidden = true;
    bar.style.width = "0%";

    try {
      setStatus("waiting");
      const offer = await api("/api/offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: files.map(f => ({ name: f.name, size: f.size })) })
      });
      let approval = null;
      for (let attempt = 0; attempt < 150; attempt++) {
        await sleep(2000);
        approval = await api("/api/status?id=" + encodeURIComponent(offer.id));
        if (approval.state !== "pending") break;
      }
      if (!approval || approval.state !== "accepted") {
        throw error(approval && approval.state === "declined"
          ? "approval_declined" : "approval_expired");
      }

      progress.hidden = false;
      const active = new Map();
      const started = performance.now();
      let sampleTime = started;
      let sampleBytes = 0;
      let rate = 0;
      let completedBytes = 0;
      let finished = 0;
      let nextIndex = 0;
      let lastRender = 0;
      let failed = false;

      function render(force = false) {
        const now = performance.now();
        if (!force && now - lastRender < 140) return;
        lastRender = now;
        const transferred = completedBytes + Array.from(active.values())
          .reduce((sum, bytes) => sum + bytes, 0);
        const elapsed = now - sampleTime;
        if (elapsed > 800) {
          rate = Math.max(0, (transferred - sampleBytes) * 1000 / elapsed);
          sampleBytes = transferred;
          sampleTime = now;
        }
        const percent = total ? Math.min(100, transferred / total * 100)
          : (finished / files.length * 100);
        bar.style.width = percent.toFixed(1) + "%";
        setStatus("progress_status", {
          count: finished, totalFiles: files.length,
          sent: fmt(transferred), totalSize: fmt(total)
        });
        setSpeed("live_speed", { rate: fmt(rate) });
      }

      function report(index, bytes) {
        active.set(index, bytes);
        render();
      }

      async function worker() {
        while (!failed) {
          const index = nextIndex++;
          if (index >= files.length) return;
          active.set(index, 0);
          try {
            await uploadFile(offer.id, index, files[index], report);
            active.delete(index);
            completedBytes += files[index].size;
            finished++;
            render(true);
          } catch (err) {
            failed = true;
            throw err;
          }
        }
      }
      const workers = Array.from(
        { length: Math.min(CONCURRENT_FILES, files.length) },
        () => worker()
      );
      const results = await Promise.allSettled(workers);
      const error = results.find(r => r.status === "rejected");
      if (error) throw error.reason;

      const duration = Math.max(0.001, (performance.now() - started) / 1000);
      setStatus("success", { count: files.length, size: fmt(total) });
      status.classList.add("is-success");
      setSpeed("average_speed", { rate: fmt(total / duration) });
      bar.style.width = "100%";
      input.value = "";
    } catch (err) {
      status.classList.add("is-error");
      setStatus(err.translationKey || "upload_failed", err.values || {}, "⚠ ");
    } finally {
      busy = false;
      send.textContent = t("send_button");
      selection();
    }
  });
})();
