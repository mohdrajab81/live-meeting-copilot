(function () {
  const MAX_ROWS = 300;
  const STICKY_THRESHOLD = 80;
  const UI_PREFS_KEY = "translator_ui_prefs_v1";

  const FONT_STACKS = {
    Manrope: "Manrope, sans-serif",
    "Segoe UI": '"Segoe UI", Tahoma, sans-serif',
    Arial: "Arial, sans-serif",
    "Noto Sans Arabic": '"Noto Sans Arabic", sans-serif',
  };

  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const reconnectBadge = document.getElementById("reconnectBadge");

  const timeline = document.getElementById("timeline");
  const timelineDivider = document.getElementById("timelineDivider");
  const timelineWrap = document.querySelector(".timeline-wrap");
  const enInterim = document.getElementById("enInterim");
  const arInterim = document.getElementById("arInterim");
  const transcriptSearch = document.getElementById("transcriptSearch");
  const logsEl = document.getElementById("logs");
  const logsSearch = document.getElementById("logsSearch");

  const startBtn = document.getElementById("startBtn");
  const stopBtn = document.getElementById("stopBtn");
  const clearBtn = document.getElementById("clearBtn");

  const clockNow = document.getElementById("clockNow");
  const sessionStart = document.getElementById("sessionStart");
  const recordTimer = document.getElementById("recordTimer");

  const cfgLang = document.getElementById("cfgLang");
  const cfgCaptureMode = document.getElementById("cfgCaptureMode");
  const cfgAudioSource = document.getElementById("cfgAudioSource");
  const cfgInputDeviceId = document.getElementById("cfgInputDeviceId");
  const dualInputGroup = document.getElementById("dualInputGroup");
  const cfgLocalSpeakerLabel = document.getElementById("cfgLocalSpeakerLabel");
  const cfgLocalInputDeviceId = document.getElementById("cfgLocalInputDeviceId");
  const cfgRemoteSpeakerLabel = document.getElementById("cfgRemoteSpeakerLabel");
  const cfgRemoteInputDeviceId = document.getElementById("cfgRemoteInputDeviceId");
  const refreshAudioDevicesBtn = document.getElementById("refreshAudioDevicesBtn");
  const audioDevicesList = document.getElementById("audioDevicesList");
  const audioDevicesHint = document.getElementById("audioDevicesHint");
  const cfgEnd = document.getElementById("cfgEnd");
  const cfgInitial = document.getElementById("cfgInitial");
  const cfgMaxFinals = document.getElementById("cfgMaxFinals");
  const cfgDebug = document.getElementById("cfgDebug");
  const showTs = document.getElementById("showTs");
  const cfgCoachEnabled = document.getElementById("cfgCoachEnabled");
  const cfgCoachTriggerSpeaker = document.getElementById("cfgCoachTriggerSpeaker");
  const cfgCoachCooldownSec = document.getElementById("cfgCoachCooldownSec");
  const cfgCoachMaxTurns = document.getElementById("cfgCoachMaxTurns");
  const cfgCoachInstruction = document.getElementById("cfgCoachInstruction");
  const fontFamily = document.getElementById("fontFamily");
  const fontScale = document.getElementById("fontScale");
  const fontScaleVal = document.getElementById("fontScaleVal");
  const applyConfigBtn = document.getElementById("applyConfigBtn");
  const saveConfigBtn = document.getElementById("saveConfigBtn");
  const reloadConfigBtn = document.getElementById("reloadConfigBtn");

  const copyLogsBtn = document.getElementById("copyLogsBtn");
  const clearLogsBtn = document.getElementById("clearLogsBtn");
  const exportLogsBtn = document.getElementById("exportLogsBtn");
  const exportLogsFromExportBtn = document.getElementById("exportLogsFromExportBtn");
  const exportTranscriptJsonBtn = document.getElementById("exportTranscriptJsonBtn");
  const exportTranscriptCsvBtn = document.getElementById("exportTranscriptCsvBtn");

  const coachPrompt = document.getElementById("coachPrompt");
  const askCoachBtn = document.getElementById("askCoachBtn");
  const clearCoachBtn = document.getElementById("clearCoachBtn");
  const coachHintsEl = document.getElementById("coachHints");
  const coachStatusEl = document.getElementById("coachStatus");

  const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
  const tabPanes = Array.from(document.querySelectorAll(".tab-pane"));

  const state = {
    socket: null,
    reconnectAttempts: 0,
    reconnectTimer: null,
    finals: [],
    livePartials: {},
    logs: [],
    coachHints: [],
    coachPending: false,
    coachConfigured: false,
    sessionStartedTs: null,
    recording: {
      started_ts: null,
      accumulated_ms: 0,
      total_ms: 0,
    },
    ui: {
      showTs: true,
      fontFamily: "Manrope",
      fontScale: 1,
      livePanelHeight: 180,
    },
    filters: {
      transcript: "",
      logs: "",
    },
    audioDevices: [],
  };

  function wsUrl() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws`;
  }

  function tsToMs(ts) {
    if (!ts) return Date.now();
    return ts > 10_000_000_000 ? Number(ts) : Number(ts) * 1000;
  }

  function formatTime(ts) {
    return new Date(tsToMs(ts)).toLocaleTimeString();
  }

  function formatDuration(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const hh = String(Math.floor(total / 3600)).padStart(2, "0");
    const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
    const ss = String(total % 60).padStart(2, "0");
    return `${hh}:${mm}:${ss}`;
  }

  function normalizeText(text) {
    return String(text || "").toLocaleLowerCase();
  }

  function isNearBottom(el) {
    return (el.scrollHeight - el.scrollTop - el.clientHeight) < STICKY_THRESHOLD;
  }

  function scrollToBottom(el) {
    el.scrollTop = el.scrollHeight;
  }

  function setStatus(text, mode) {
    statusDot.classList.remove("connected", "listening");
    if (mode === "listening") statusDot.classList.add("listening");
    if (mode === "connected") statusDot.classList.add("connected");
    statusText.textContent = text || "idle";
  }

  function logLineText(log) {
    return `[${formatTime(log.ts)}] [${log.level || "info"}] ${log.message || ""}`;
  }

  function addLog(level, message, ts, prepend) {
    const line = document.createElement("div");
    line.className = "line";
    line.textContent = logLineText({ level, message, ts });

    if (prepend) logsEl.prepend(line);
    else logsEl.appendChild(line);

    while (logsEl.children.length > 400) logsEl.removeChild(logsEl.lastChild);
  }

  function filteredLogs() {
    const query = normalizeText(state.filters.logs).trim();
    if (!query) return [...state.logs];
    return state.logs.filter((log) => {
      const line = `${log.level || ""} ${log.message || ""} ${formatTime(log.ts)}`;
      return normalizeText(line).includes(query);
    });
  }

  function renderLogs() {
    logsEl.innerHTML = "";
    const newestFirst = filteredLogs().reverse();
    newestFirst.forEach((log) => addLog(log.level, log.message, log.ts, false));
  }

  function makeTimelineRow(item) {
    const row = document.createElement("div");
    row.className = "row";

    const enCell = document.createElement("div");
    const enMeta = document.createElement("div");
    enMeta.className = "meta";
    const enTag = document.createElement("span");
    enTag.className = "speaker-tag";
    enTag.textContent = item.speaker_label || "Speaker";
    const ts1 = document.createElement("div");
    ts1.className = "ts";
    ts1.textContent = formatTime(item.ts);
    enMeta.appendChild(enTag);
    enMeta.appendChild(ts1);
    const enLine = document.createElement("div");
    enLine.className = "line en";
    enLine.textContent = item.en || "";
    enCell.appendChild(enMeta);
    enCell.appendChild(enLine);

    const arCell = document.createElement("div");
    const arMeta = document.createElement("div");
    arMeta.className = "meta";
    const arTag = document.createElement("span");
    arTag.className = "speaker-tag";
    arTag.textContent = item.speaker_label || "Speaker";
    const ts2 = document.createElement("div");
    ts2.className = "ts";
    ts2.textContent = formatTime(item.ts);
    arMeta.appendChild(arTag);
    arMeta.appendChild(ts2);
    const arLine = document.createElement("div");
    arLine.className = "line ar";
    arLine.textContent = item.ar || "";
    arCell.appendChild(arMeta);
    arCell.appendChild(arLine);

    row.appendChild(enCell);
    row.appendChild(arCell);
    return row;
  }

  function filteredFinals() {
    const query = normalizeText(state.filters.transcript).trim();
    if (!query) return [...state.finals];
    return state.finals.filter((item) => {
      const line = `${item.speaker_label || ""} ${item.en || ""} ${item.ar || ""} ${formatTime(item.ts)}`;
      return normalizeText(line).includes(query);
    });
  }

  function appendFinal(item) {
    const normalized = {
      en: item.en || "",
      ar: item.ar || "",
      speaker: item.speaker || "default",
      speaker_label: item.speaker_label || "Speaker",
      ts: item.ts || Date.now() / 1000,
    };
    state.finals.push(normalized);

    while (state.finals.length > MAX_ROWS) state.finals.shift();
    renderFinals(true);
  }

  function renderFinals(keepBottomIfNear) {
    const sticky = keepBottomIfNear ? isNearBottom(timeline) : false;
    timeline.innerHTML = "";
    filteredFinals().forEach((item) => timeline.appendChild(makeTimelineRow(item)));
    if (sticky) scrollToBottom(timeline);
  }

  function renderLivePartials() {
    const entries = Object.values(state.livePartials).sort((a, b) => (a.ts || 0) - (b.ts || 0));
    enInterim.textContent = entries.map((x) => `[${x.speaker_label}] ${x.en || ""}`.trim()).join("\n");
    arInterim.textContent = entries.map((x) => `[${x.speaker_label}] ${x.ar || ""}`.trim()).join("\n");
  }

  function renderCoachHints() {
    coachHintsEl.innerHTML = "";
    const mergedByGroup = new Map();
    const ordered = [...state.coachHints];
    ordered.forEach((hint, idx) => {
      const gid = hint.group_id || `manual-${idx}`;
      const prev = mergedByGroup.get(gid);
      if (!prev) {
        mergedByGroup.set(gid, hint);
        return;
      }
      const prevKind = prev.hint_kind || "";
      const nextKind = hint.hint_kind || "";
      if (prevKind === "quick" && nextKind === "deep") {
        mergedByGroup.set(gid, hint);
      } else if (prev.ts <= hint.ts) {
        mergedByGroup.set(gid, hint);
      }
    });
    const hints = Array.from(mergedByGroup.values()).reverse();
    hints.forEach((hint) => {
      const card = document.createElement("div");
      card.className = "coach-item";

      const meta = document.createElement("div");
      meta.className = "coach-meta";
      const kind = hint.hint_kind || "manual";
      const kindLabel = kind === "quick" ? "Quick" : (kind === "deep" ? "Verified" : "Manual");
      meta.textContent = `${formatTime(hint.ts)} | ${kindLabel} | Trigger: ${hint.speaker_label || "Manual"}`;

      const text = document.createElement("div");
      text.className = "coach-text";
      text.textContent = hint.suggestion || "";

      card.appendChild(meta);
      if (hint.trigger_en) {
        const q = document.createElement("div");
        q.className = "muted";
        q.textContent = `Based on: ${hint.trigger_en}`;
        card.appendChild(q);
      }
      card.appendChild(text);
      coachHintsEl.appendChild(card);
    });

    const statusParts = [];
    statusParts.push(state.coachConfigured ? "Configured" : "Not configured");
    if (state.coachPending) statusParts.push("Generating...");
    coachStatusEl.textContent = statusParts.join(" | ");
  }

  async function clearTranscript() {
    await request("/api/transcript/clear", "POST");
    state.finals = [];
    state.livePartials = {};
    timeline.innerHTML = "";
    renderLivePartials();
  }

  function syncCaptureModeUI() {
    const isDual = cfgCaptureMode.value === "dual";
    dualInputGroup.style.display = isDual ? "block" : "none";
    cfgAudioSource.disabled = isDual;
    cfgInputDeviceId.disabled = isDual || cfgAudioSource.value !== "device_id";
    cfgCoachTriggerSpeaker.value = isDual ? "remote" : (cfgCoachTriggerSpeaker.value || "default");
    if (audioDevicesHint) {
      if (isDual) {
        audioDevicesHint.textContent = "Dual mode: configure local and remote device IDs below.";
      } else {
        audioDevicesHint.textContent = cfgAudioSource.value === "device_id"
          ? "Select/paste the exact device ID from the list below."
          : "Using Windows default microphone input.";
      }
    }
  }

  function setConfigUI(config) {
    cfgLang.value = config.recognition_language || "en-US";
    cfgCaptureMode.value = config.capture_mode || "single";
    cfgAudioSource.value = config.audio_source || "default";
    cfgInputDeviceId.value = config.input_device_id || "";
    cfgLocalSpeakerLabel.value = config.local_speaker_label || "You";
    cfgLocalInputDeviceId.value = config.local_input_device_id || "";
    cfgRemoteSpeakerLabel.value = config.remote_speaker_label || "Remote";
    cfgRemoteInputDeviceId.value = config.remote_input_device_id || "";
    cfgEnd.value = Number(config.end_silence_ms || 250);
    cfgInitial.value = Number(config.initial_silence_ms || 3000);
    cfgMaxFinals.value = Number(config.max_finals || 200);
    cfgDebug.checked = !!config.debug;
    cfgCoachEnabled.checked = !!config.coach_enabled;
    cfgCoachTriggerSpeaker.value = config.coach_trigger_speaker || "remote";
    cfgCoachCooldownSec.value = Number(config.coach_cooldown_sec || 8);
    cfgCoachMaxTurns.value = Number(config.coach_max_turns || 8);
    cfgCoachInstruction.value = config.coach_instruction || "";
    syncCaptureModeUI();
    syncAudioSourceUI();
  }

  function syncAudioSourceUI() {
    const isDevice = cfgAudioSource.value === "device_id";
    const isDual = cfgCaptureMode.value === "dual";
    cfgInputDeviceId.disabled = isDual || !isDevice;
    audioDevicesList.disabled = false;
    if (audioDevicesHint && !isDual) {
      audioDevicesHint.textContent = isDevice
        ? "Select/paste the exact device ID from the list below."
        : "Using Windows default microphone input.";
    }
  }

  function renderAudioDeviceOptions() {
    if (!audioDevicesList) return;
    audioDevicesList.innerHTML = "";
    state.audioDevices.forEach((dev) => {
      const opt = document.createElement("option");
      opt.value = dev.id || "";
      opt.label = `${dev.label || dev.id}`;
      audioDevicesList.appendChild(opt);
    });
  }

  async function loadAudioDevices() {
    const out = await request("/api/audio/devices", "GET");
    state.audioDevices = Array.isArray(out.devices) ? out.devices : [];
    renderAudioDeviceOptions();
  }

  function loadUiPrefs() {
    try {
      const raw = localStorage.getItem(UI_PREFS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (typeof parsed.showTs === "boolean") state.ui.showTs = parsed.showTs;
      if (typeof parsed.fontFamily === "string") state.ui.fontFamily = parsed.fontFamily;
      if (typeof parsed.fontScale === "number") state.ui.fontScale = parsed.fontScale;
      if (typeof parsed.livePanelHeight === "number") state.ui.livePanelHeight = parsed.livePanelHeight;
    } catch (_err) {
      // ignore bad local preferences
    }
  }

  function saveUiPrefs() {
    localStorage.setItem(UI_PREFS_KEY, JSON.stringify(state.ui));
  }

  function applyFontSettings() {
    const selectedFamily = FONT_STACKS[state.ui.fontFamily] || FONT_STACKS.Manrope;
    const scale = Number(state.ui.fontScale) || 1;

    document.documentElement.style.setProperty("--ui-font", selectedFamily);
    document.documentElement.style.setProperty("--line-en-size", `${(1.32 * scale).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--line-ar-size", `${(1.72 * scale).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--live-en-size", `${(1.38 * scale).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--live-ar-size", `${(1.80 * scale).toFixed(2)}rem`);

    fontFamily.value = state.ui.fontFamily;
    fontScale.value = String(scale);
    fontScaleVal.textContent = `${Math.round(scale * 100)}%`;
  }

  function applyTimestampVisibility() {
    if (state.ui.showTs) timeline.classList.add("show-ts");
    else timeline.classList.remove("show-ts");
    showTs.checked = state.ui.showTs;
  }

  function clampLiveHeight(px) {
    if (!timelineWrap) return 180;
    const wrapH = Math.max(240, Math.floor(timelineWrap.clientHeight || 0));
    const minH = 90;
    const maxH = Math.floor(wrapH * 0.55);
    return Math.max(minH, Math.min(maxH, Math.floor(px)));
  }

  function applyLivePanelHeight(px) {
    const height = clampLiveHeight(px);
    state.ui.livePanelHeight = height;
    if (timelineWrap) {
      timelineWrap.style.setProperty("--live-panel-height", `${height}px`);
    }
  }

  function setupTimelineDivider() {
    if (!timelineDivider || !timelineWrap) return;
    const onDrag = (clientY) => {
      const rect = timelineWrap.getBoundingClientRect();
      const nextHeight = rect.bottom - clientY;
      applyLivePanelHeight(nextHeight);
    };

    const startDrag = (ev) => {
      ev.preventDefault();
      const move = (e) => {
        if (e.touches && e.touches[0]) onDrag(e.touches[0].clientY);
        else onDrag(e.clientY);
      };
      const stop = () => {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", stop);
        document.removeEventListener("touchmove", move);
        document.removeEventListener("touchend", stop);
        saveUiPrefs();
      };

      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", stop);
      document.addEventListener("touchmove", move, { passive: false });
      document.addEventListener("touchend", stop);
    };

    timelineDivider.addEventListener("mousedown", startDrag);
    timelineDivider.addEventListener("touchstart", startDrag, { passive: false });
    window.addEventListener("resize", () => applyLivePanelHeight(state.ui.livePanelHeight));
  }

  function setRecording(recording) {
    if (!recording) return;
    state.recording.started_ts = recording.started_ts || null;
    state.recording.accumulated_ms = Number(recording.accumulated_ms || 0);
    state.recording.total_ms = Number(recording.total_ms || 0);
  }

  function computeRecordedMs() {
    let total = Number(state.recording.accumulated_ms || 0);
    if (state.recording.started_ts) {
      total += Math.max(0, (Date.now() - tsToMs(state.recording.started_ts)));
    } else {
      total = Math.max(total, Number(state.recording.total_ms || 0));
    }
    return Math.floor(total);
  }

  function renderTimeStrip() {
    clockNow.textContent = `Now ${new Date().toLocaleTimeString()}`;
    sessionStart.textContent = state.sessionStartedTs
      ? `Session ${formatTime(state.sessionStartedTs)}`
      : "Session --:--:--";
    recordTimer.textContent = `Record ${formatDuration(computeRecordedMs())}`;
  }

  function setActiveTab(tabId) {
    tabButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabId));
    tabPanes.forEach((pane) => pane.classList.toggle("active", pane.id === tabId));
  }

  function renderSnapshot(msg) {
    state.finals = (msg.finals || []).map((f) => ({
      en: f.en || "",
      ar: f.ar || "",
      speaker: f.speaker || "default",
      speaker_label: f.speaker_label || "Speaker",
      ts: f.ts || Date.now() / 1000,
    }));

    state.livePartials = {};
    (msg.live_partials || []).forEach((p) => {
      const key = p.speaker || "default";
      state.livePartials[key] = {
        speaker: key,
        speaker_label: p.speaker_label || "Speaker",
        en: p.en || "",
        ar: p.ar || "",
        ts: p.ts || Date.now() / 1000,
      };
    });

    state.logs = (msg.logs || []).map((l) => ({
      level: l.level || "info",
      message: l.message || "",
      ts: l.ts || Date.now() / 1000,
    }));

    const coach = msg.coach || {};
    state.coachConfigured = !!coach.configured;
    state.coachPending = !!coach.pending;
    state.coachHints = Array.isArray(coach.hints) ? coach.hints : [];

    state.sessionStartedTs = msg.session_started_ts || null;
    setRecording(msg.recording || null);

    renderFinals();
    renderLogs();
    renderLivePartials();
    renderCoachHints();
    setStatus(msg.status || "idle", msg.running ? "listening" : "connected");
    applyTimestampVisibility();
    renderTimeStrip();
  }

  async function request(path, method, body) {
    const res = await fetch(path, {
      method: method || "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `${path} failed`);
    }
    return res.json().catch(() => ({}));
  }

  async function applyConfig() {
    const payload = {
      recognition_language: cfgLang.value.trim(),
      capture_mode: cfgCaptureMode.value || "single",
      audio_source: cfgAudioSource.value || "default",
      input_device_id: cfgInputDeviceId.value.trim(),
      local_speaker_label: cfgLocalSpeakerLabel.value.trim() || "You",
      local_input_device_id: cfgLocalInputDeviceId.value.trim(),
      remote_speaker_label: cfgRemoteSpeakerLabel.value.trim() || "Remote",
      remote_input_device_id: cfgRemoteInputDeviceId.value.trim(),
      coach_enabled: cfgCoachEnabled.checked,
      coach_trigger_speaker: cfgCoachTriggerSpeaker.value || "remote",
      coach_cooldown_sec: Number(cfgCoachCooldownSec.value),
      coach_max_turns: Number(cfgCoachMaxTurns.value),
      coach_instruction: cfgCoachInstruction.value.trim(),
      end_silence_ms: Number(cfgEnd.value),
      initial_silence_ms: Number(cfgInitial.value),
      max_finals: Number(cfgMaxFinals.value),
      debug: cfgDebug.checked,
    };
    await request("/api/config", "PUT", payload);
  }

  async function saveConfig() {
    await request("/api/config/save", "POST");
  }

  async function reloadConfig() {
    const out = await request("/api/config/reload", "POST");
    if (out.config) setConfigUI(out.config);
  }

  function reconnectDelayMs() {
    const n = Math.min(state.reconnectAttempts, 6);
    return Math.min(1000 * (2 ** n), 15000);
  }

  function scheduleReconnect() {
    clearTimeout(state.reconnectTimer);
    reconnectBadge.classList.remove("hidden");
    const wait = reconnectDelayMs();
    state.reconnectTimer = setTimeout(connectSocket, wait);
  }

  function escapeCsv(value) {
    const text = String(value == null ? "" : value);
    const escaped = text.replace(/"/g, '""');
    return `"${escaped}"`;
  }

  function downloadFile(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function exportLogsText() {
    const content = state.logs.map((log) => logLineText(log)).join("\n");
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(`logs-${stamp}.txt`, content, "text/plain;charset=utf-8");
  }

  function exportTranscriptJson() {
    const data = {
      exported_at: new Date().toISOString(),
      total_entries: state.finals.length,
      transcript: state.finals.map((item, idx) => ({
        index: idx + 1,
        speaker: item.speaker || "default",
        speaker_label: item.speaker_label || "Speaker",
        time_local: formatTime(item.ts),
        time_unix_sec: item.ts,
        english: item.en,
        arabic: item.ar,
      })),
      coach_hints: state.coachHints,
    };
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `transcript-translation-${stamp}.json`,
      `${JSON.stringify(data, null, 2)}\n`,
      "application/json;charset=utf-8"
    );
  }

  function exportTranscriptCsv() {
    const lines = ["index,speaker,speaker_label,time_local,time_unix_sec,english,arabic"];
    state.finals.forEach((item, idx) => {
      lines.push(
        [
          idx + 1,
          escapeCsv(item.speaker || "default"),
          escapeCsv(item.speaker_label || "Speaker"),
          formatTime(item.ts),
          item.ts,
          escapeCsv(item.en),
          escapeCsv(item.ar),
        ].join(",")
      );
    });
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `transcript-translation-${stamp}.csv`,
      `${lines.join("\n")}\n`,
      "text/csv;charset=utf-8"
    );
  }

  async function copyLogs() {
    const text = state.logs.map((log) => logLineText(log)).join("\n");
    if (!text.trim()) return;
    await navigator.clipboard.writeText(text);
  }

  async function clearLogs() {
    await request("/api/logs/clear", "POST");
    state.logs = [];
    logsEl.innerHTML = "";
  }

  async function askCoach() {
    const prompt = (coachPrompt.value || "").trim();
    if (!prompt) return;
    askCoachBtn.disabled = true;
    try {
      await request("/api/coach/ask", "POST", { prompt, speaker_label: "Manual" });
      coachPrompt.value = "";
    } finally {
      askCoachBtn.disabled = false;
    }
  }

  async function clearCoach() {
    await request("/api/coach/clear", "POST");
    state.coachHints = [];
    renderCoachHints();
  }

  function handleMessage(msg) {
    if (msg.type === "snapshot") {
      renderSnapshot(msg);
      if (msg.config) setConfigUI(msg.config);
      return;
    }

    if (msg.type === "status") {
      setStatus(msg.status || "idle", msg.running ? "listening" : "connected");
      setRecording(msg.recording || null);
      renderTimeStrip();
      return;
    }

    if (msg.type === "partial") {
      const key = msg.speaker || "default";
      state.livePartials[key] = {
        speaker: key,
        speaker_label: msg.speaker_label || "Speaker",
        en: msg.en || "",
        ar: msg.ar || "",
        ts: Date.now() / 1000,
      };
      renderLivePartials();
      return;
    }

    if (msg.type === "final") {
      appendFinal(msg);
      if (msg.speaker) delete state.livePartials[msg.speaker];
      else state.livePartials = {};
      renderLivePartials();
      return;
    }

    if (msg.type === "coach") {
      state.coachHints.push(msg);
      while (state.coachHints.length > 120) state.coachHints.shift();
      state.coachPending = (msg.hint_kind || "") === "quick";
      renderCoachHints();
      return;
    }

    if (msg.type === "log") {
      const log = {
        level: msg.level || "info",
        message: msg.message || "",
        ts: msg.ts || Date.now() / 1000,
      };
      state.logs.push(log);
      while (state.logs.length > 1000) state.logs.shift();
      if ((msg.message || "").includes("Coach request failed")) {
        state.coachPending = false;
        renderCoachHints();
      }
      renderLogs();
    }
  }

  function connectSocket() {
    const ws = new WebSocket(wsUrl());
    state.socket = ws;

    ws.onopen = () => {
      state.reconnectAttempts = 0;
      reconnectBadge.classList.add("hidden");
      if (!statusDot.classList.contains("listening")) setStatus("connected", "connected");
    };

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      handleMessage(msg);
    };

    ws.onerror = () => {
      setStatus("connection error", "connected");
    };

    ws.onclose = () => {
      setStatus("disconnected", "connected");
      state.reconnectAttempts += 1;
      scheduleReconnect();
    };
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });

  startBtn.addEventListener("click", () => request("/api/start", "POST").catch((e) => alert(e.message)));
  stopBtn.addEventListener("click", () => request("/api/stop", "POST").catch((e) => alert(e.message)));
  clearBtn.addEventListener("click", () => clearTranscript().catch((e) => alert(e.message)));

  applyConfigBtn.addEventListener("click", () => applyConfig().catch((e) => alert(e.message)));
  saveConfigBtn.addEventListener("click", () => saveConfig().catch((e) => alert(e.message)));
  reloadConfigBtn.addEventListener("click", () => reloadConfig().catch((e) => alert(e.message)));

  showTs.addEventListener("change", () => {
    state.ui.showTs = showTs.checked;
    applyTimestampVisibility();
    saveUiPrefs();
  });

  fontFamily.addEventListener("change", () => {
    state.ui.fontFamily = fontFamily.value;
    applyFontSettings();
    saveUiPrefs();
  });

  fontScale.addEventListener("input", () => {
    state.ui.fontScale = Number(fontScale.value);
    applyFontSettings();
    saveUiPrefs();
  });

  cfgCaptureMode.addEventListener("change", () => {
    syncCaptureModeUI();
    syncAudioSourceUI();
  });
  cfgAudioSource.addEventListener("change", syncAudioSourceUI);
  refreshAudioDevicesBtn.addEventListener("click", () => {
    loadAudioDevices().catch((e) => alert(e.message));
  });

  transcriptSearch.addEventListener("input", () => {
    state.filters.transcript = transcriptSearch.value;
    renderFinals();
  });

  logsSearch.addEventListener("input", () => {
    state.filters.logs = logsSearch.value;
    renderLogs();
  });

  askCoachBtn.addEventListener("click", () => askCoach().catch((e) => alert(e.message)));
  clearCoachBtn.addEventListener("click", () => clearCoach().catch((e) => alert(e.message)));

  copyLogsBtn.addEventListener("click", () => copyLogs().catch((e) => alert(e.message)));
  clearLogsBtn.addEventListener("click", () => clearLogs().catch((e) => alert(e.message)));
  exportLogsBtn.addEventListener("click", exportLogsText);
  exportLogsFromExportBtn.addEventListener("click", exportLogsText);
  exportTranscriptJsonBtn.addEventListener("click", exportTranscriptJson);
  exportTranscriptCsvBtn.addEventListener("click", exportTranscriptCsv);

  loadUiPrefs();
  applyTimestampVisibility();
  applyFontSettings();
  applyLivePanelHeight(state.ui.livePanelHeight);
  setupTimelineDivider();

  request("/api/state")
    .then((snapshot) => {
      renderSnapshot(snapshot);
      if (snapshot.config) setConfigUI(snapshot.config);
    })
    .catch(() => {});

  loadAudioDevices().catch(() => {});

  connectSocket();
  setInterval(renderTimeStrip, 500);
})();
