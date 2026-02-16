(function () {
  const MAX_ROWS = 300;
  const STICKY_THRESHOLD = 80;
  const UI_PREFS_KEY = "translator_ui_prefs_v1";
  const BOOKMARKS_KEY = "translator_bookmarks_v1";
  const THEMES = ["dark", "light", "graphite", "sand"];

  const FONT_STACKS = {
    Manrope: "Manrope, sans-serif",
    "Segoe UI": '"Segoe UI", Tahoma, sans-serif',
    Arial: "Arial, sans-serif",
    "IBM Plex Sans Arabic": '"IBM Plex Sans Arabic", sans-serif',
    "Noto Sans Arabic": '"Noto Sans Arabic", sans-serif',
  };

  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const reconnectBadge = document.getElementById("reconnectBadge");
  const telemetryWs = document.getElementById("telemetryWs");
  const telemetryTr = document.getElementById("telemetryTr");

  const timeline = document.getElementById("timeline");
  const timelineDivider = document.getElementById("timelineDivider");
  const timelineWrap = document.querySelector(".timeline-wrap");
  const enInterim = document.getElementById("enInterim");
  const arInterim = document.getElementById("arInterim");
  const enLiveLabel = document.getElementById("enLiveLabel");
  const arLiveLabel = document.getElementById("arLiveLabel");
  const enLiveState = document.getElementById("enLiveState");
  const arLiveState = document.getElementById("arLiveState");
  const transcriptSearch = document.getElementById("transcriptSearch");
  const logsEl = document.getElementById("logs");
  const logsSearch = document.getElementById("logsSearch");

  const startBtn = document.getElementById("startBtn");
  const stopBtn = document.getElementById("stopBtn");
  const clearBtn = document.getElementById("clearBtn");
  const themeToggleBtn = document.getElementById("themeToggleBtn");

  const clockNow = document.getElementById("clockNow");
  const sessionStart = document.getElementById("sessionStart");
  const recordTimer = document.getElementById("recordTimer");
  const silenceGuardChip = document.getElementById("silenceGuardChip");

  const cfgLang = document.getElementById("cfgLang");
  const cfgCaptureMode = document.getElementById("cfgCaptureMode");
  const singleInputGroup = document.getElementById("singleInputGroup");
  const cfgAudioSource = document.getElementById("cfgAudioSource");
  const cfgInputDeviceId = document.getElementById("cfgInputDeviceId");
  const dualInputGroup = document.getElementById("dualInputGroup");
  const cfgLocalSpeakerLabel = document.getElementById("cfgLocalSpeakerLabel");
  const cfgLocalInputDeviceId = document.getElementById("cfgLocalInputDeviceId");
  const cfgRemoteSpeakerLabel = document.getElementById("cfgRemoteSpeakerLabel");
  const cfgRemoteInputDeviceId = document.getElementById("cfgRemoteInputDeviceId");
  const audioDevicesHint = document.getElementById("audioDevicesHint");
  const cfgEnd = document.getElementById("cfgEnd");
  const cfgEndRange = document.getElementById("cfgEndRange");
  const cfgInitial = document.getElementById("cfgInitial");
  const cfgMaxFinals = document.getElementById("cfgMaxFinals");
  const cfgDebug = document.getElementById("cfgDebug");
  const showTs = document.getElementById("showTs");
  const cfgCoachEnabled = document.getElementById("cfgCoachEnabled");
  const cfgCoachTriggerSpeaker = document.getElementById("cfgCoachTriggerSpeaker");
  const cfgCoachCooldownSec = document.getElementById("cfgCoachCooldownSec");
  const cfgCoachCooldownSecRange = document.getElementById("cfgCoachCooldownSecRange");
  const cfgCoachMaxTurns = document.getElementById("cfgCoachMaxTurns");
  const cfgCoachMaxTurnsRange = document.getElementById("cfgCoachMaxTurnsRange");
  const coachPresetRow = document.getElementById("coachPresetRow");
  const cfgPartialTranslateMinIntervalSec = document.getElementById("cfgPartialTranslateMinIntervalSec");
  const cfgPartialTranslateMinIntervalSecRange = document.getElementById("cfgPartialTranslateMinIntervalSecRange");
  const cfgAutoStopSilenceSec = document.getElementById("cfgAutoStopSilenceSec");
  const cfgAutoStopSilenceSecRange = document.getElementById("cfgAutoStopSilenceSecRange");
  const autoStopPresets = document.getElementById("autoStopPresets");
  const autoStopHint = document.getElementById("autoStopHint");
  const cfgMaxSessionSec = document.getElementById("cfgMaxSessionSec");
  const cfgMaxSessionSecRange = document.getElementById("cfgMaxSessionSecRange");
  const cfgCoachInstruction = document.getElementById("cfgCoachInstruction");
  const fontFamilyEn = document.getElementById("fontFamilyEn");
  const fontFamilyAr = document.getElementById("fontFamilyAr");
  const fontScaleEn = document.getElementById("fontScaleEn");
  const fontScaleEnVal = document.getElementById("fontScaleEnVal");
  const fontScaleAr = document.getElementById("fontScaleAr");
  const fontScaleArVal = document.getElementById("fontScaleArVal");
  const applyConfigBtn = document.getElementById("applyConfigBtn");
  const saveConfigBtn = document.getElementById("saveConfigBtn");
  const reloadConfigBtn = document.getElementById("reloadConfigBtn");
  const restoreDefaultsBtn = document.getElementById("restoreDefaultsBtn");
  const settingsDirtyIndicator = document.getElementById("settingsDirtyIndicator");
  const settingsTab = document.getElementById("settingsTab");

  const copyLogsBtn = document.getElementById("copyLogsBtn");
  const clearLogsBtn = document.getElementById("clearLogsBtn");
  const exportLogsBtn = document.getElementById("exportLogsBtn");
  const exportTranscriptJsonBtn = document.getElementById("exportTranscriptJsonBtn");
  const exportTranscriptCsvBtn = document.getElementById("exportTranscriptCsvBtn");
  const exportBookmarksJsonBtn = document.getElementById("exportBookmarksJsonBtn");
  const exportBookmarksCsvBtn = document.getElementById("exportBookmarksCsvBtn");
  const bookmarksOnlyBtn = document.getElementById("bookmarksOnlyBtn");
  const bookmarkMenu = document.getElementById("bookmarkMenu");
  const bookmarkMenuEditBtn = document.getElementById("bookmarkMenuEditBtn");
  const bookmarkMenuRemoveBtn = document.getElementById("bookmarkMenuRemoveBtn");
  const bookmarkModal = document.getElementById("bookmarkModal");
  const bookmarkModalTitle = document.getElementById("bookmarkModalTitle");
  const bookmarkNoteInput = document.getElementById("bookmarkNoteInput");
  const bookmarkModalSaveBtn = document.getElementById("bookmarkModalSaveBtn");
  const bookmarkModalCancelBtn = document.getElementById("bookmarkModalCancelBtn");

  const coachPrompt = document.getElementById("coachPrompt");
  const askCoachBtn = document.getElementById("askCoachBtn");
  const clearCoachBtn = document.getElementById("clearCoachBtn");
  const coachHintsEl = document.getElementById("coachHints");
  const coachStatusEl = document.getElementById("coachStatus");

  const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
  const tabPanes = Array.from(document.querySelectorAll(".tab-pane"));
  const settingsAccordions = Array.from(document.querySelectorAll(".settings-accordion"));
  const toastHost = document.getElementById("toastHost");

  const state = {
    socket: null,
    reconnectAttempts: 0,
    reconnectTimer: null,
    finals: [],
    livePartials: {},
    liveHeldFinal: null,
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
      fontFamilyEn: "Manrope",
      fontFamilyAr: "Noto Sans Arabic",
      fontScaleEn: 1,
      fontScaleAr: 1,
      livePanelHeight: 220,
      theme: "dark",
      settingsAccordions: {},
    },
    filters: {
      transcript: "",
      logs: "",
      bookmarksOnly: false,
    },
    audioDevices: [],
    currentConfig: {},
    lastSpeechActivityTs: null,
    running: false,
    configDirty: false,
    wsConnected: false,
    recognitionStatus: "idle",
    telemetry: {
      latestMs: null,
      p50Ms: null,
      estimatedCostUsd: null,
    },
    bookmarks: {},
    bookmarkUi: {
      menuKey: "",
      modalKey: "",
      modalMode: "add",
    },
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

  function formatTimeWithMs(ts) {
    const d = new Date(tsToMs(ts));
    const base = d.toLocaleTimeString();
    const ms = String(d.getMilliseconds()).padStart(3, "0");
    return `${base}.${ms}`;
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

  function finalKey(item) {
    const segmentId = String(item.segment_id || "").trim();
    const revision = Number(item.revision || 0);
    const tsMs = Math.round(Number(item.ts || 0) * 1000);
    const speaker = String(item.speaker || "default");
    const en = String(item.en || "");
    const ar = String(item.ar || "");
    if (segmentId) {
      return `${segmentId}:${revision}:${tsMs}:${speaker}:${en.length}:${ar.length}`;
    }
    return `${speaker}:${tsMs}:${en}:${ar}`;
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
    state.recognitionStatus = text || "idle";
    renderTelemetryHud();
  }

  function renderTelemetryHud() {
    const wsText = state.wsConnected ? "WS Online" : "WS Offline";
    const latest = Number(state.telemetry.latestMs);
    const p50 = Number(state.telemetry.p50Ms);
    const latencyText = (Number.isFinite(latest) && latest >= 0)
      ? `Tr ${latest}ms (p50 ${Number.isFinite(p50) && p50 >= 0 ? p50 : latest}ms)`
      : "Tr --";
    if (telemetryWs) telemetryWs.textContent = wsText;
    if (telemetryTr) telemetryTr.textContent = latencyText;
  }

  function showToast(message, type, options) {
    if (!toastHost) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type || "info"}`;
    const msg = document.createElement("div");
    msg.className = "toast-msg";
    msg.textContent = String(message || "");
    toast.appendChild(msg);

    const actions = Array.isArray(options?.actions) ? options.actions : [];
    if (actions.length) {
      const wrap = document.createElement("div");
      wrap.className = "toast-actions";
      actions.forEach((action) => {
        const btn = document.createElement("button");
        btn.className = "toast-action-btn";
        btn.type = "button";
        btn.textContent = action.label;
        btn.addEventListener("click", async () => {
          try {
            if (typeof action.onClick === "function") await action.onClick();
          } catch (err) {
            // no-op
          } finally {
            toast.remove();
          }
        });
        wrap.appendChild(btn);
      });
      toast.appendChild(wrap);
    }

    toastHost.appendChild(toast);
    const ttl = Number(options?.ttlMs || (type === "error" ? 7000 : 4500));
    setTimeout(() => toast.remove(), ttl);
  }

  async function withBusy(button, pendingLabel, fn) {
    const original = button.textContent;
    button.disabled = true;
    button.classList.add("is-loading");
    if (pendingLabel) button.textContent = pendingLabel;
    try {
      await fn();
    } finally {
      button.disabled = false;
      button.classList.remove("is-loading");
      button.textContent = original;
    }
  }

  function notifyError(err) {
    const message = err?.message || String(err || "Unknown error");
    showToast(message, "error");
  }

  function validateStartInputs() {
    const isDual = (cfgCaptureMode && cfgCaptureMode.value === "dual");
    if (!isDual) return { ok: true, message: "" };

    const localId = String(cfgLocalInputDeviceId?.value || "").trim();
    const remoteId = String(cfgRemoteInputDeviceId?.value || "").trim();
    if (localId && remoteId) return { ok: true, message: "" };

    const missing = [];
    if (!localId) missing.push("Your Input Device");
    if (!remoteId) missing.push("Remote Input Device");
    return {
      ok: false,
      message: `Dual Input needs both devices selected. Missing: ${missing.join(", ")}`,
    };
  }

  function setConfigDirty(dirty) {
    state.configDirty = !!dirty;
    if (!settingsDirtyIndicator) return;
    settingsDirtyIndicator.classList.toggle("hidden", !state.configDirty);
  }

  function logLineText(log) {
    return `[${formatTimeWithMs(log.ts)}] [${log.level || "info"}] ${log.message || ""}`;
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
    const key = finalKey(item);
    row.dataset.key = key;
    const bookmark = state.bookmarks[key] || null;

    const enCell = document.createElement("div");
    enCell.className = "entry-card";
    if (bookmark) enCell.classList.add("is-bookmarked");
    const enMeta = document.createElement("div");
    enMeta.className = "meta";
    const enTag = document.createElement("span");
    enTag.className = "speaker-tag";
    enTag.textContent = item.speaker_label || "Speaker";
    const bmBtn = document.createElement("button");
    bmBtn.type = "button";
    bmBtn.className = "bookmark-btn";
    if (bookmark) bmBtn.classList.add("active");
    if (bookmark && bookmark.note) bmBtn.classList.add("has-note");
    bmBtn.textContent = "★";
    bmBtn.dataset.key = key;
    bmBtn.title = bookmark
      ? `Bookmarked${bookmark.note ? `: ${bookmark.note}` : ""}. Click to remove.`
      : "Bookmark this row (optional note)";
    const ts1 = document.createElement("div");
    ts1.className = "ts";
    ts1.textContent = formatTime(item.ts);
    enMeta.appendChild(enTag);
    enMeta.appendChild(bmBtn);
    enMeta.appendChild(ts1);
    const enLine = document.createElement("div");
    enLine.className = "line en";
    enLine.textContent = item.en || "";
    enCell.appendChild(enMeta);
    enCell.appendChild(enLine);

    const arCell = document.createElement("div");
    arCell.className = "entry-card";
    if (bookmark) arCell.classList.add("is-bookmarked");
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
    return state.finals.filter((item) => {
      const key = finalKey(item);
      if (state.filters.bookmarksOnly && !state.bookmarks[key]) return false;
      if (!query) return true;
      const line = `${item.speaker_label || ""} ${item.en || ""} ${item.ar || ""} ${formatTime(item.ts)}`;
      const note = state.bookmarks[key]?.note || "";
      return normalizeText(`${line} ${note}`).includes(query);
    });
  }

  function appendFinal(item) {
    const normalized = {
      en: item.en || "",
      ar: item.ar || "",
      speaker: item.speaker || "default",
      speaker_label: item.speaker_label || "Speaker",
      segment_id: item.segment_id || "",
      revision: Number(item.revision || 0),
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
    const partialEntries = Object.values(state.livePartials).sort((a, b) => (a.ts || 0) - (b.ts || 0));
    const useLive = partialEntries.length > 0;
    const heldEntry = (!useLive && state.liveHeldFinal) ? [state.liveHeldFinal] : [];
    const entries = useLive ? partialEntries : heldEntry;

    const enText = entries.map((x) => `${x.en || ""}`.trim()).join("\n").trim();
    const arText = entries.map((x) => `${x.ar || ""}`.trim()).join("\n").trim();
    const speakerLabel = entries.length ? (entries[entries.length - 1].speaker_label || "Speaker") : "Speaker";

    if (enLiveLabel) enLiveLabel.textContent = speakerLabel;
    if (arLiveLabel) arLiveLabel.textContent = speakerLabel;

    enInterim.textContent = enText;
    arInterim.textContent = arText;

    const hasHeld = !useLive && heldEntry.length > 0;
    const enState = useLive && enText ? "live" : (hasHeld && enText ? "held" : "idle");
    const arState = useLive && arText ? "live" : (hasHeld && arText ? "held" : "idle");

    enInterim.classList.toggle("interim", enState === "live");
    arInterim.classList.toggle("interim", arState === "live");

    setLiveStateChip(enLiveState, enState);
    setLiveStateChip(arLiveState, arState);
  }

  function setLiveStateChip(el, mode) {
    if (!el) return;
    el.classList.remove("is-live", "is-held");
    if (mode === "live") {
      el.textContent = "Live";
      el.classList.add("is-live");
      return;
    }
    if (mode === "held") {
      el.textContent = "Last final";
      el.classList.add("is-held");
      return;
    }
    el.textContent = "Waiting";
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
      if (prev.ts <= hint.ts) {
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
      const kindLabel = kind === "deep" ? "Auto" : "Manual";
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
    statusParts.push(state.coachConfigured ? "Coach ready" : "Coach unavailable");
    if (state.coachPending) {
      statusParts.push("Generating reply...");
    } else if (hints.length === 0) {
      statusParts.push("No suggestions yet");
    }
    coachStatusEl.textContent = statusParts.join(" | ");
  }

  async function clearTranscript() {
    await request("/api/transcript/clear", "POST");
    state.finals = [];
    state.livePartials = {};
    state.liveHeldFinal = null;
    state.bookmarks = {};
    saveBookmarks();
    timeline.innerHTML = "";
    renderLivePartials();
  }

  function syncCaptureModeUI() {
    const isDual = cfgCaptureMode.value === "dual";
    if (singleInputGroup) singleInputGroup.style.display = isDual ? "none" : "block";
    dualInputGroup.style.display = isDual ? "block" : "none";
    cfgAudioSource.disabled = isDual;
    cfgInputDeviceId.disabled = isDual || cfgAudioSource.value !== "device_id";
    cfgAudioSource.title = isDual ? "Disabled in dual mode (local/remote device selectors are used)." : "";
    cfgInputDeviceId.title = isDual
      ? "Ignored in dual mode."
      : (cfgAudioSource.value !== "device_id" ? "Enable 'Specific Device' to use this field." : "");
    if (audioDevicesHint) {
      if (isDual) {
        audioDevicesHint.textContent = (
          "Dual mode: top 'Audio Input Source' and 'Input Device' are ignored. "
          + "Choose Local and Remote devices below."
        );
      } else {
        audioDevicesHint.textContent = cfgAudioSource.value === "device_id"
          ? "Select a specific device from the dropdown."
          : "Using Windows default microphone input.";
      }
    }
    syncCoachControlsUI();
  }

  function setConfigUI(config) {
    state.currentConfig = { ...config };
    renderAudioDeviceOptions(config);
    cfgLang.value = config.recognition_language || "en-US";
    cfgCaptureMode.value = config.capture_mode || "single";
    cfgAudioSource.value = config.audio_source || "default";
    cfgInputDeviceId.value = config.input_device_id || "";
    cfgLocalSpeakerLabel.value = config.local_speaker_label || "You";
    cfgLocalInputDeviceId.value = config.local_input_device_id || "";
    cfgRemoteSpeakerLabel.value = config.remote_speaker_label || "Remote";
    cfgRemoteInputDeviceId.value = config.remote_input_device_id || "";
    const endSilenceMs = clampNumber(config.end_silence_ms, 50, 10000, 250);
    cfgEnd.value = endSilenceMs;
    if (cfgEndRange) cfgEndRange.value = endSilenceMs;
    cfgInitial.value = Number(config.initial_silence_ms || 3000);
    cfgMaxFinals.value = Number(config.max_finals || 5000);
    cfgDebug.checked = !!config.debug;
    cfgCoachEnabled.checked = !!config.coach_enabled;
    const trigger = String(config.coach_trigger_speaker || "remote");
    cfgCoachTriggerSpeaker.value = trigger === "default" ? "remote" : trigger;
    cfgCoachCooldownSec.value = clampNumber(config.coach_cooldown_sec, 0, 120, 8);
    if (cfgCoachCooldownSecRange) cfgCoachCooldownSecRange.value = cfgCoachCooldownSec.value;
    cfgCoachMaxTurns.value = clampNumber(config.coach_max_turns, 2, 30, 8);
    if (cfgCoachMaxTurnsRange) cfgCoachMaxTurnsRange.value = cfgCoachMaxTurns.value;
    renderCoachPresetState();
    if (cfgPartialTranslateMinIntervalSec) {
      const interval = clampDecimal(config.partial_translate_min_interval_sec, 0.2, 3.0, 0.6, 1);
      cfgPartialTranslateMinIntervalSec.value = interval;
      if (cfgPartialTranslateMinIntervalSecRange) cfgPartialTranslateMinIntervalSecRange.value = interval;
    }
    if (cfgAutoStopSilenceSec) {
      const minutes = clampDecimal((Number(config.auto_stop_silence_sec || 75) / 60), 0, 5, 1.25, 2);
      cfgAutoStopSilenceSec.value = minutes;
      if (cfgAutoStopSilenceSecRange) cfgAutoStopSilenceSecRange.value = minutes;
      renderAutoStopHint();
      renderAutoStopPresetState();
    }
    if (cfgMaxSessionSec) {
      const minutes = clampNumber(Math.round(Number(config.max_session_sec || 3600) / 60), 5, 180, 60);
      cfgMaxSessionSec.value = minutes;
      if (cfgMaxSessionSecRange) cfgMaxSessionSecRange.value = minutes;
    }
    cfgCoachInstruction.value = config.coach_instruction || "";
    syncCaptureModeUI();
    syncAudioSourceUI();
    syncCoachControlsUI();
    setConfigDirty(false);
  }

  function syncAudioSourceUI() {
    const isDevice = cfgAudioSource.value === "device_id";
    const isDual = cfgCaptureMode.value === "dual";
    cfgInputDeviceId.disabled = isDual || !isDevice;
    cfgLocalInputDeviceId.disabled = !isDual;
    cfgRemoteInputDeviceId.disabled = !isDual;
    cfgInputDeviceId.title = isDual
      ? "Ignored in dual mode."
      : (!isDevice ? "Enable 'Specific Device' to use this field." : "");
    if (audioDevicesHint && !isDual) {
      audioDevicesHint.textContent = isDevice
        ? "Select a specific device from the dropdown."
        : "Using Windows default microphone input.";
    }
  }

  function syncCoachControlsUI() {
    const coachEnabled = !!(cfgCoachEnabled && cfgCoachEnabled.checked);
    const isDual = cfgCaptureMode.value === "dual";

    const disableAllCoachInputs = !coachEnabled;
    const disableTriggerSpeaker = disableAllCoachInputs || !isDual;

    if (cfgCoachTriggerSpeaker) {
      cfgCoachTriggerSpeaker.disabled = disableTriggerSpeaker;
      cfgCoachTriggerSpeaker.title = disableAllCoachInputs
        ? "Enable Auto Interview Coach to edit this."
        : (!isDual ? "In Single Input mode, trigger speaker selection is not used." : "");
    }
    if (cfgCoachCooldownSec) cfgCoachCooldownSec.disabled = disableAllCoachInputs;
    if (cfgCoachCooldownSecRange) cfgCoachCooldownSecRange.disabled = disableAllCoachInputs;
    if (cfgCoachMaxTurns) cfgCoachMaxTurns.disabled = disableAllCoachInputs;
    if (cfgCoachMaxTurnsRange) cfgCoachMaxTurnsRange.disabled = disableAllCoachInputs;
    if (cfgCoachInstruction) cfgCoachInstruction.disabled = disableAllCoachInputs;

    if (coachPresetRow) {
      coachPresetRow.querySelectorAll(".preset-btn").forEach((btn) => {
        btn.disabled = disableAllCoachInputs;
      });
    }
  }

  function clampNumber(value, min, max, fallback) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.min(max, Math.max(min, Math.round(n)));
  }

  function clampDecimal(value, min, max, fallback, decimals) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    const bounded = Math.min(max, Math.max(min, n));
    const factor = 10 ** Math.max(0, Number(decimals || 0));
    return Math.round(bounded * factor) / factor;
  }

  function syncEndSilenceControls(source) {
    const raw = source === "range" ? cfgEndRange.value : cfgEnd.value;
    const bounded = clampNumber(raw, 50, 10000, 250);
    cfgEnd.value = bounded;
    if (cfgEndRange) cfgEndRange.value = bounded;
  }

  function syncPartialIntervalControls(source) {
    if (!cfgPartialTranslateMinIntervalSec) return;
    const raw = (
      source === "range" && cfgPartialTranslateMinIntervalSecRange
        ? cfgPartialTranslateMinIntervalSecRange.value
        : cfgPartialTranslateMinIntervalSec.value
    );
    const bounded = clampDecimal(raw, 0.2, 3.0, 0.6, 1);
    cfgPartialTranslateMinIntervalSec.value = bounded;
    if (cfgPartialTranslateMinIntervalSecRange) cfgPartialTranslateMinIntervalSecRange.value = bounded;
  }

  function syncAutoStopControls(source) {
    if (!cfgAutoStopSilenceSec) return;
    const raw = (
      source === "range" && cfgAutoStopSilenceSecRange
        ? cfgAutoStopSilenceSecRange.value
        : cfgAutoStopSilenceSec.value
    );
    const bounded = clampDecimal(raw, 0, 5, 1.25, 2);
    cfgAutoStopSilenceSec.value = bounded;
    if (cfgAutoStopSilenceSecRange) cfgAutoStopSilenceSecRange.value = bounded;
    renderAutoStopHint();
    renderAutoStopPresetState();
  }

  function syncMaxSessionControls(source) {
    if (!cfgMaxSessionSec) return;
    const raw = (
      source === "range" && cfgMaxSessionSecRange
        ? cfgMaxSessionSecRange.value
        : cfgMaxSessionSec.value
    );
    const bounded = clampNumber(raw, 5, 180, 60);
    cfgMaxSessionSec.value = bounded;
    if (cfgMaxSessionSecRange) cfgMaxSessionSecRange.value = bounded;
  }

  function syncCoachCooldownControls(source) {
    if (!cfgCoachCooldownSec) return;
    const raw = (
      source === "range" && cfgCoachCooldownSecRange
        ? cfgCoachCooldownSecRange.value
        : cfgCoachCooldownSec.value
    );
    const bounded = clampNumber(raw, 0, 120, 8);
    cfgCoachCooldownSec.value = bounded;
    if (cfgCoachCooldownSecRange) cfgCoachCooldownSecRange.value = bounded;
    renderCoachPresetState();
  }

  function syncCoachTurnsControls(source) {
    if (!cfgCoachMaxTurns) return;
    const raw = (
      source === "range" && cfgCoachMaxTurnsRange
        ? cfgCoachMaxTurnsRange.value
        : cfgCoachMaxTurns.value
    );
    const bounded = clampNumber(raw, 2, 30, 8);
    cfgCoachMaxTurns.value = bounded;
    if (cfgCoachMaxTurnsRange) cfgCoachMaxTurnsRange.value = bounded;
    renderCoachPresetState();
  }

  function renderCoachPresetState() {
    if (!coachPresetRow || !cfgCoachCooldownSec || !cfgCoachMaxTurns) return;
    const cooldown = clampNumber(cfgCoachCooldownSec.value, 0, 120, 8);
    const turns = clampNumber(cfgCoachMaxTurns.value, 2, 30, 8);
    coachPresetRow.querySelectorAll(".preset-btn").forEach((btn) => {
      const p = String(btn.getAttribute("data-preset") || "");
      const active = (
        (p === "conservative" && cooldown === 15 && turns === 4)
        || (p === "balanced" && cooldown === 8 && turns === 8)
        || (p === "aggressive" && cooldown === 2 && turns === 12)
      );
      btn.classList.toggle("active", active);
    });
  }

  function renderAutoStopHint() {
    if (!autoStopHint || !cfgAutoStopSilenceSec) return;
    const minutes = clampDecimal(cfgAutoStopSilenceSec.value, 0, 5, 1.25, 2);
    autoStopHint.textContent = minutes <= 0
      ? "Auto-stop disabled. Session will keep running until you stop manually."
      : `Auto-stop after ${minutes} min with no recognized speech.`;
  }

  function renderAutoStopPresetState() {
    if (!autoStopPresets || !cfgAutoStopSilenceSec) return;
    const minutes = clampDecimal(cfgAutoStopSilenceSec.value, 0, 5, 1.25, 2);
    autoStopPresets.querySelectorAll(".preset-btn").forEach((btn) => {
      const val = Number(btn.getAttribute("data-minutes") || -1);
      btn.classList.toggle("active", Math.abs(val - minutes) < 0.001);
    });
  }

  function renderSilenceGuardChip() {
    if (!silenceGuardChip || !cfgAutoStopSilenceSec) return;
    const silenceLimitMin = clampDecimal(cfgAutoStopSilenceSec.value, 0, 5, 1.25, 2);
    const silenceLimitSec = Math.round(silenceLimitMin * 60);
    if (silenceLimitSec <= 0) {
      silenceGuardChip.textContent = "Auto-stop Off";
      return;
    }
    if (!state.running) {
      silenceGuardChip.textContent = `Auto-stop ${silenceLimitMin}m`;
      return;
    }
    const lastTs = Number(state.lastSpeechActivityTs || Date.now() / 1000);
    const elapsedSec = Math.max(0, Math.floor((Date.now() / 1000) - lastTs));
    const remaining = Math.max(0, silenceLimitSec - elapsedSec);
    silenceGuardChip.textContent = remaining <= 15
      ? `Stopping in ${remaining}s`
      : `Auto-stop ${silenceLimitMin}m`;
  }

  function renderAudioDeviceOptions(configOverride) {
    const config = configOverride || state.currentConfig || {};
    const targets = [
      { el: cfgInputDeviceId, selected: config.input_device_id || cfgInputDeviceId.value || "" },
      { el: cfgLocalInputDeviceId, selected: config.local_input_device_id || cfgLocalInputDeviceId.value || "" },
      { el: cfgRemoteInputDeviceId, selected: config.remote_input_device_id || cfgRemoteInputDeviceId.value || "" },
    ];

    targets.forEach((target) => {
      const select = target.el;
      if (!select) return;

      const selected = String(target.selected || "").trim();
      select.innerHTML = "";

      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "Select device...";
      select.appendChild(blank);

      state.audioDevices.forEach((dev) => {
        const id = String(dev.id || "").trim();
        const label = String(dev.label || id || "Unknown device").trim();
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = label || "Unknown device";
        select.appendChild(opt);
      });

      if (selected && !state.audioDevices.some((dev) => String(dev.id || "").trim() === selected)) {
        const missing = document.createElement("option");
        missing.value = selected;
        missing.textContent = "[Unavailable configured device]";
        select.appendChild(missing);
      }

      select.value = selected;
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
      if (typeof parsed.fontFamilyEn === "string") state.ui.fontFamilyEn = parsed.fontFamilyEn;
      if (typeof parsed.fontFamilyAr === "string") state.ui.fontFamilyAr = parsed.fontFamilyAr;
      if (typeof parsed.fontFamily === "string") state.ui.fontFamilyEn = parsed.fontFamily;
      if (typeof parsed.fontScaleEn === "number") state.ui.fontScaleEn = parsed.fontScaleEn;
      if (typeof parsed.fontScaleAr === "number") state.ui.fontScaleAr = parsed.fontScaleAr;
      if (typeof parsed.fontScale === "number") {
        state.ui.fontScaleEn = parsed.fontScale;
        state.ui.fontScaleAr = parsed.fontScale;
      }
      if (typeof parsed.livePanelHeight === "number") state.ui.livePanelHeight = parsed.livePanelHeight;
      if (THEMES.includes(parsed.theme)) state.ui.theme = parsed.theme;
      if (parsed.settingsAccordions && typeof parsed.settingsAccordions === "object") {
        state.ui.settingsAccordions = parsed.settingsAccordions;
      }
    } catch (_err) {
      // ignore bad local preferences
    }
  }

  function saveUiPrefs() {
    localStorage.setItem(UI_PREFS_KEY, JSON.stringify(state.ui));
  }

  function loadBookmarks() {
    try {
      const raw = localStorage.getItem(BOOKMARKS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        state.bookmarks = parsed;
      }
    } catch (_err) {
      state.bookmarks = {};
    }
  }

  function saveBookmarks() {
    localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(state.bookmarks));
  }

  function pruneBookmarksToFinals() {
    const valid = new Set(state.finals.map((x) => finalKey(x)));
    const next = {};
    Object.entries(state.bookmarks || {}).forEach(([key, val]) => {
      if (valid.has(key)) next[key] = val;
    });
    state.bookmarks = next;
    saveBookmarks();
  }

  function closeBookmarkMenu() {
    state.bookmarkUi.menuKey = "";
    if (bookmarkMenu) bookmarkMenu.classList.add("hidden");
  }

  function openBookmarkMenuFor(key, anchorEl) {
    if (!bookmarkMenu || !anchorEl) return;
    state.bookmarkUi.menuKey = key;
    bookmarkMenu.classList.remove("hidden");
    const rect = anchorEl.getBoundingClientRect();
    const menuRect = bookmarkMenu.getBoundingClientRect();
    const top = Math.min(window.innerHeight - menuRect.height - 10, rect.bottom + 6);
    const left = Math.min(window.innerWidth - menuRect.width - 10, rect.left);
    bookmarkMenu.style.top = `${Math.max(10, top)}px`;
    bookmarkMenu.style.left = `${Math.max(10, left)}px`;
  }

  function closeBookmarkModal() {
    state.bookmarkUi.modalKey = "";
    if (bookmarkModal) bookmarkModal.classList.add("hidden");
    if (bookmarkNoteInput) bookmarkNoteInput.value = "";
  }

  function openBookmarkModal(mode, key) {
    if (!bookmarkModal || !bookmarkNoteInput || !bookmarkModalTitle) return;
    state.bookmarkUi.modalMode = mode;
    state.bookmarkUi.modalKey = key;
    const existing = state.bookmarks[key] || null;
    bookmarkModalTitle.textContent = mode === "edit" ? "Edit bookmark note" : "Add bookmark note";
    bookmarkNoteInput.value = existing?.note || "";
    bookmarkModal.classList.remove("hidden");
    setTimeout(() => bookmarkNoteInput.focus(), 0);
  }

  function toggleBookmarkForKey(key, options) {
    const opts = options || {};
    const existing = state.bookmarks[key];
    if (existing) {
      if (opts.forceRemove) {
        delete state.bookmarks[key];
        saveBookmarks();
        renderFinals(true);
        showToast("Bookmark removed.", "info");
        return;
      }
      if (opts.anchorEl) openBookmarkMenuFor(key, opts.anchorEl);
      return;
    }
    if (!Object.prototype.hasOwnProperty.call(opts, "note")) {
      openBookmarkModal("add", key);
      return;
    }
    const note = String(opts.note || "");
    state.bookmarks[key] = {
      note: note.trim(),
      created_ts: Date.now() / 1000,
    };
    saveBookmarks();
    renderFinals(true);
    showToast("Bookmark added.", "success");
  }

  function applySettingsAccordionPrefs() {
    if (!settingsAccordions.length) return;
    settingsAccordions.forEach((el) => {
      const key = String(el.dataset.accordion || "").trim();
      if (!key) return;
      const pref = state.ui.settingsAccordions[key];
      if (typeof pref === "boolean") {
        el.open = pref;
      }
    });
  }

  function bindSettingsAccordionPrefs() {
    if (!settingsAccordions.length) return;
    settingsAccordions.forEach((el) => {
      el.addEventListener("toggle", () => {
        const key = String(el.dataset.accordion || "").trim();
        if (!key) return;
        state.ui.settingsAccordions[key] = !!el.open;
        saveUiPrefs();
      });
    });
  }

  function applyFontSettings() {
    const selectedFamilyEn = FONT_STACKS[state.ui.fontFamilyEn] || FONT_STACKS.Manrope;
    const selectedFamilyAr = FONT_STACKS[state.ui.fontFamilyAr] || FONT_STACKS["Noto Sans Arabic"];
    const scaleEn = Number(state.ui.fontScaleEn) || 1;
    const scaleAr = Number(state.ui.fontScaleAr) || 1;

    document.documentElement.style.setProperty("--ui-font-en", selectedFamilyEn);
    document.documentElement.style.setProperty("--ui-font-ar", selectedFamilyAr);
    document.documentElement.style.setProperty("--line-en-size", `${(1.32 * scaleEn).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--line-ar-size", `${(1.72 * scaleAr).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--live-en-size", `${(1.38 * scaleEn).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--live-ar-size", `${(1.80 * scaleAr).toFixed(2)}rem`);

    if (fontFamilyEn) fontFamilyEn.value = state.ui.fontFamilyEn;
    if (fontFamilyAr) fontFamilyAr.value = state.ui.fontFamilyAr;
    if (fontScaleEn) fontScaleEn.value = String(scaleEn);
    if (fontScaleEnVal) fontScaleEnVal.textContent = `${Math.round(scaleEn * 100)}%`;
    if (fontScaleAr) fontScaleAr.value = String(scaleAr);
    if (fontScaleArVal) fontScaleArVal.textContent = `${Math.round(scaleAr * 100)}%`;
  }

  function applyTheme() {
    const next = THEMES.includes(state.ui.theme) ? state.ui.theme : "dark";
    document.body.setAttribute("data-theme", next);
    if (themeToggleBtn) {
      const pretty = next.charAt(0).toUpperCase() + next.slice(1);
      themeToggleBtn.textContent = `Theme: ${pretty}`;
      themeToggleBtn.title = "Switch theme";
    }
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
      segment_id: f.segment_id || "",
      revision: Number(f.revision || 0),
      ts: f.ts || Date.now() / 1000,
    }));
    pruneBookmarksToFinals();

    state.livePartials = {};
    (msg.live_partials || []).forEach((p) => {
      const key = p.speaker || "default";
      state.livePartials[key] = {
        speaker: key,
        speaker_label: p.speaker_label || "Speaker",
        segment_id: p.segment_id || "",
        revision: Number(p.revision || 0),
        en: p.en || "",
        ar: p.ar || "",
        ts: p.ts || Date.now() / 1000,
      };
    });

    state.liveHeldFinal = null;
    if (!Object.keys(state.livePartials).length && state.finals.length > 0) {
      const latest = state.finals.reduce((best, cur) => (
        Number(cur.ts || 0) >= Number(best.ts || 0) ? cur : best
      ), state.finals[0]);
      state.liveHeldFinal = {
        en: latest.en || "",
        ar: latest.ar || "",
        speaker: latest.speaker || "default",
        speaker_label: latest.speaker_label || "Speaker",
        segment_id: latest.segment_id || "",
        revision: Number(latest.revision || 0),
        ts: latest.ts || Date.now() / 1000,
      };
    }

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
    state.running = !!msg.running;
    state.lastSpeechActivityTs = Date.now() / 1000;
    const telemetry = msg.telemetry || {};
    state.telemetry.latestMs = telemetry.translation_latest_ms ?? null;
    state.telemetry.p50Ms = telemetry.translation_p50_ms ?? null;
    state.telemetry.estimatedCostUsd = telemetry.estimated_cost_usd ?? null;
    setRecording(msg.recording || null);

    renderFinals();
    renderLogs();
    renderLivePartials();
    renderCoachHints();
    setStatus(msg.status || "idle", msg.running ? "listening" : "connected");
    applyTimestampVisibility();
    renderSilenceGuardChip();
    renderTimeStrip();
    renderTelemetryHud();
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
    const existing = state.currentConfig || {};
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
      coach_cooldown_sec: clampNumber(cfgCoachCooldownSec.value, 0, 120, 8),
      coach_max_turns: clampNumber(cfgCoachMaxTurns.value, 2, 30, 8),
      partial_translate_min_interval_sec: cfgPartialTranslateMinIntervalSec
        ? clampDecimal(cfgPartialTranslateMinIntervalSec.value, 0.2, 3.0, 0.6, 1)
        : Number(existing.partial_translate_min_interval_sec || 0.6),
      auto_stop_silence_sec: cfgAutoStopSilenceSec
        ? clampNumber(Math.round(clampDecimal(cfgAutoStopSilenceSec.value, 0, 5, 1.25, 2) * 60), 0, 300, 75)
        : Number(existing.auto_stop_silence_sec || 75),
      max_session_sec: cfgMaxSessionSec
        ? clampNumber(clampNumber(cfgMaxSessionSec.value, 5, 180, 60) * 60, 300, 10800, 3600)
        : Number(existing.max_session_sec || 3600),
      coach_instruction: cfgCoachInstruction.value.trim(),
      end_silence_ms: clampNumber(cfgEnd.value, 50, 10000, 250),
      initial_silence_ms: Number(cfgInitial.value),
      max_finals: Number(cfgMaxFinals.value),
      debug: cfgDebug.checked,
    };
    const out = await request("/api/config", "PUT", payload);
    if (out && out.config) {
      setConfigUI(out.config);
    }
    return out;
  }

  async function saveConfig() {
    if (state.configDirty) {
      await applyConfig();
    }
    await request("/api/config/save", "POST");
  }

  async function reloadConfig() {
    const out = await request("/api/config/reload", "POST");
    if (out.config) setConfigUI(out.config);
  }

  async function restoreDefaults() {
    const out = await request("/api/config/reset-defaults", "POST");
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
    const content = `\ufeff${state.logs.map((log) => logLineText(log)).join("\r\n")}`;
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(`logs-${stamp}.txt`, content, "text/plain;charset=utf-8");
  }

  function exportTranscriptJson() {
    const rows = state.finals.map((item, idx) => {
      const key = finalKey(item);
      const bm = state.bookmarks[key] || null;
      return {
        index: idx + 1,
        speaker: item.speaker || "default",
        speaker_label: item.speaker_label || "Speaker",
        time_local: formatTime(item.ts),
        time_unix_sec: item.ts,
        english: item.en,
        arabic: item.ar,
        bookmarked: !!bm,
        bookmark_note: bm?.note || "",
      };
    });
    const bookmarks = rows.filter((x) => x.bookmarked);
    const data = {
      exported_at: new Date().toISOString(),
      total_entries: rows.length,
      transcript: rows,
      bookmarks,
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
    const lines = ["index,speaker,speaker_label,time_local,time_unix_sec,bookmarked,bookmark_note,english,arabic"];
    state.finals.forEach((item, idx) => {
      const key = finalKey(item);
      const bm = state.bookmarks[key] || null;
      lines.push(
        [
          idx + 1,
          escapeCsv(item.speaker || "default"),
          escapeCsv(item.speaker_label || "Speaker"),
          formatTime(item.ts),
          item.ts,
          bm ? "1" : "0",
          escapeCsv(bm?.note || ""),
          escapeCsv(item.en),
          escapeCsv(item.ar),
        ].join(",")
      );
    });
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `transcript-translation-${stamp}.csv`,
      `\ufeff${lines.join("\r\n")}\r\n`,
      "text/csv;charset=utf-8"
    );
  }

  function collectBookmarksForExport() {
    return state.finals
      .map((item, idx) => {
        const key = finalKey(item);
        const bm = state.bookmarks[key] || null;
        if (!bm) return null;
        return {
          index: idx + 1,
          speaker: item.speaker || "default",
          speaker_label: item.speaker_label || "Speaker",
          time_local: formatTime(item.ts),
          time_unix_sec: item.ts,
          note: bm.note || "",
          english: item.en || "",
          arabic: item.ar || "",
        };
      })
      .filter(Boolean);
  }

  function exportBookmarksJson() {
    const bookmarks = collectBookmarksForExport();
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `bookmarks-${stamp}.json`,
      `${JSON.stringify({ exported_at: new Date().toISOString(), count: bookmarks.length, bookmarks }, null, 2)}\n`,
      "application/json;charset=utf-8"
    );
  }

  function exportBookmarksCsv() {
    const rows = collectBookmarksForExport();
    const lines = ["index,speaker,speaker_label,time_local,time_unix_sec,note,english,arabic"];
    rows.forEach((r) => {
      lines.push(
        [
          r.index,
          escapeCsv(r.speaker),
          escapeCsv(r.speaker_label),
          r.time_local,
          r.time_unix_sec,
          escapeCsv(r.note),
          escapeCsv(r.english),
          escapeCsv(r.arabic),
        ].join(",")
      );
    });
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `bookmarks-${stamp}.csv`,
      `\ufeff${lines.join("\r\n")}\r\n`,
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
    await withBusy(askCoachBtn, "Asking", async () => {
      await request("/api/coach/ask", "POST", { prompt, speaker_label: "Manual" });
      coachPrompt.value = "";
      showToast("Coach response received.", "success");
    });
  }

  async function clearCoach() {
    await request("/api/coach/clear", "POST");
    state.coachHints = [];
    renderCoachHints();
    showToast("Coach history cleared.", "info");
  }

  function handleMessage(msg) {
    if (msg.type === "snapshot") {
      renderSnapshot(msg);
      if (msg.config) setConfigUI(msg.config);
      return;
    }

    if (msg.type === "status") {
      setStatus(msg.status || "idle", msg.running ? "listening" : "connected");
      state.running = !!msg.running;
      if (state.running) state.lastSpeechActivityTs = Date.now() / 1000;
      setRecording(msg.recording || null);
      renderSilenceGuardChip();
      renderTimeStrip();
      renderTelemetryHud();
      return;
    }

    if (msg.type === "telemetry") {
      state.telemetry.latestMs = msg.translation_latest_ms ?? null;
      state.telemetry.p50Ms = msg.translation_p50_ms ?? null;
      state.telemetry.estimatedCostUsd = msg.estimated_cost_usd ?? null;
      state.running = !!msg.recognition_running;
      state.recognitionStatus = msg.recognition_status || state.recognitionStatus;
      renderTelemetryHud();
      return;
    }

    if (msg.type === "partial") {
      const key = msg.speaker || "default";
      state.lastSpeechActivityTs = Date.now() / 1000;
      state.liveHeldFinal = null;
      state.livePartials = {};
      state.livePartials[key] = {
        speaker: key,
        speaker_label: msg.speaker_label || "Speaker",
        segment_id: msg.segment_id || "",
        revision: Number(msg.revision || 0),
        en: msg.en || "",
        ar: msg.ar || "",
        ts: Date.now() / 1000,
      };
      renderLivePartials();
      renderSilenceGuardChip();
      return;
    }

    if (msg.type === "final") {
      state.lastSpeechActivityTs = Date.now() / 1000;
      appendFinal(msg);
      state.liveHeldFinal = {
        en: msg.en || "",
        ar: msg.ar || "",
        speaker: msg.speaker || "default",
        speaker_label: msg.speaker_label || "Speaker",
        segment_id: msg.segment_id || "",
        revision: Number(msg.revision || 0),
        ts: msg.ts || Date.now() / 1000,
      };
      state.livePartials = {};
      renderLivePartials();
      renderSilenceGuardChip();
      return;
    }

    if (msg.type === "final_patch") {
      const segmentId = msg.segment_id || "";
      const revision = Number(msg.revision || 0);
      if (!segmentId) return;
      const idx = state.finals.findIndex((x) => x.segment_id === segmentId && Number(x.revision || 0) === revision);
      if (idx < 0) return;
      state.finals[idx] = {
        ...state.finals[idx],
        ar: msg.ar || "",
      };
      if (
        state.liveHeldFinal
        && state.liveHeldFinal.segment_id === segmentId
        && Number(state.liveHeldFinal.revision || 0) === revision
      ) {
        state.liveHeldFinal = {
          ...state.liveHeldFinal,
          ar: msg.ar || "",
        };
        renderLivePartials();
      }
      renderFinals(true);
      return;
    }

    if (msg.type === "coach") {
      state.coachHints.push(msg);
      while (state.coachHints.length > 120) state.coachHints.shift();
      state.coachPending = false;
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
      if ((msg.message || "").startsWith("Auto-stopping after ")) {
        showToast(msg.message, "warning", {
          ttlMs: 9000,
          actions: [
            {
              label: "Resume",
              onClick: async () => {
                await request("/api/start", "POST");
                showToast("Session resumed.", "success");
              },
            },
          ],
        });
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
      state.running = false;
      state.wsConnected = true;
      renderSilenceGuardChip();
      renderTelemetryHud();
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
      state.running = false;
      state.wsConnected = false;
      renderSilenceGuardChip();
      renderTelemetryHud();
      scheduleReconnect();
    };
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });

  startBtn.addEventListener("click", () => withBusy(startBtn, "Starting", async () => {
    const v = validateStartInputs();
    if (!v.ok) {
      showToast(v.message, "warning");
      throw new Error(v.message);
    }
    await request("/api/start", "POST");
    showToast("Start requested.", "info");
  }).catch(notifyError));
  stopBtn.addEventListener("click", () => withBusy(stopBtn, "Stopping", async () => {
    await request("/api/stop", "POST");
    showToast("Stop requested.", "info");
  }).catch(notifyError));
  clearBtn.addEventListener("click", () => {
    const confirmed = window.confirm("Clear the full transcript now? This cannot be undone.");
    if (!confirmed) return;
    withBusy(clearBtn, "Clearing", async () => {
      await clearTranscript();
      showToast("Transcript cleared.", "info");
    }).catch(notifyError);
  });

  applyConfigBtn.addEventListener("click", () => withBusy(applyConfigBtn, "Applying", async () => {
    await applyConfig();
    setConfigDirty(false);
    showToast("Configuration applied.", "success");
  }).catch(notifyError));
  saveConfigBtn.addEventListener("click", () => withBusy(saveConfigBtn, "Saving", async () => {
    await saveConfig();
    setConfigDirty(false);
    showToast("Configuration saved.", "success");
  }).catch(notifyError));
  reloadConfigBtn.addEventListener("click", () => withBusy(reloadConfigBtn, "Reloading", async () => {
    await reloadConfig();
    setConfigDirty(false);
    showToast("Configuration reloaded.", "success");
  }).catch(notifyError));
  if (restoreDefaultsBtn) {
    restoreDefaultsBtn.addEventListener("click", () => withBusy(restoreDefaultsBtn, "Restoring", async () => {
      await restoreDefaults();
      setConfigDirty(false);
      showToast("System defaults restored.", "success");
    }).catch(notifyError));
  }

  showTs.addEventListener("change", () => {
    state.ui.showTs = showTs.checked;
    applyTimestampVisibility();
    saveUiPrefs();
  });

  if (fontFamilyEn) {
    fontFamilyEn.addEventListener("change", () => {
      state.ui.fontFamilyEn = fontFamilyEn.value;
      applyFontSettings();
      saveUiPrefs();
    });
  }
  if (fontFamilyAr) {
    fontFamilyAr.addEventListener("change", () => {
      state.ui.fontFamilyAr = fontFamilyAr.value;
      applyFontSettings();
      saveUiPrefs();
    });
  }

  if (fontScaleEn) {
    fontScaleEn.addEventListener("input", () => {
      state.ui.fontScaleEn = Number(fontScaleEn.value);
      applyFontSettings();
      saveUiPrefs();
    });
  }
  if (fontScaleAr) {
    fontScaleAr.addEventListener("input", () => {
      state.ui.fontScaleAr = Number(fontScaleAr.value);
      applyFontSettings();
      saveUiPrefs();
    });
  }
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const idx = Math.max(0, THEMES.indexOf(state.ui.theme));
      state.ui.theme = THEMES[(idx + 1) % THEMES.length];
      applyTheme();
      saveUiPrefs();
    });
  }

  cfgCaptureMode.addEventListener("change", () => {
    syncCaptureModeUI();
    syncAudioSourceUI();
  });
  if (cfgCoachEnabled) {
    cfgCoachEnabled.addEventListener("change", () => {
      syncCoachControlsUI();
    });
  }
  cfgAudioSource.addEventListener("change", syncAudioSourceUI);
  if (cfgEndRange) {
    cfgEndRange.addEventListener("input", () => syncEndSilenceControls("range"));
    cfgEndRange.addEventListener("change", () => syncEndSilenceControls("range"));
  }
  cfgEnd.addEventListener("input", () => syncEndSilenceControls("number"));
  cfgEnd.addEventListener("change", () => syncEndSilenceControls("number"));
  if (cfgPartialTranslateMinIntervalSecRange) {
    cfgPartialTranslateMinIntervalSecRange.addEventListener("input", () => syncPartialIntervalControls("range"));
    cfgPartialTranslateMinIntervalSecRange.addEventListener("change", () => syncPartialIntervalControls("range"));
  }
  if (cfgPartialTranslateMinIntervalSec) {
    cfgPartialTranslateMinIntervalSec.addEventListener("input", () => syncPartialIntervalControls("number"));
    cfgPartialTranslateMinIntervalSec.addEventListener("change", () => syncPartialIntervalControls("number"));
  }
  if (cfgAutoStopSilenceSecRange) {
    cfgAutoStopSilenceSecRange.addEventListener("input", () => syncAutoStopControls("range"));
    cfgAutoStopSilenceSecRange.addEventListener("change", () => syncAutoStopControls("range"));
  }
  if (cfgAutoStopSilenceSec) {
    cfgAutoStopSilenceSec.addEventListener("input", () => syncAutoStopControls("number"));
    cfgAutoStopSilenceSec.addEventListener("change", () => syncAutoStopControls("number"));
  }
  if (cfgMaxSessionSecRange) {
    cfgMaxSessionSecRange.addEventListener("input", () => syncMaxSessionControls("range"));
    cfgMaxSessionSecRange.addEventListener("change", () => syncMaxSessionControls("range"));
  }
  if (cfgMaxSessionSec) {
    cfgMaxSessionSec.addEventListener("input", () => syncMaxSessionControls("number"));
    cfgMaxSessionSec.addEventListener("change", () => syncMaxSessionControls("number"));
  }
  if (cfgCoachCooldownSecRange) {
    cfgCoachCooldownSecRange.addEventListener("input", () => syncCoachCooldownControls("range"));
    cfgCoachCooldownSecRange.addEventListener("change", () => syncCoachCooldownControls("range"));
  }
  if (cfgCoachCooldownSec) {
    cfgCoachCooldownSec.addEventListener("input", () => syncCoachCooldownControls("number"));
    cfgCoachCooldownSec.addEventListener("change", () => syncCoachCooldownControls("number"));
  }
  if (cfgCoachMaxTurnsRange) {
    cfgCoachMaxTurnsRange.addEventListener("input", () => syncCoachTurnsControls("range"));
    cfgCoachMaxTurnsRange.addEventListener("change", () => syncCoachTurnsControls("range"));
  }
  if (cfgCoachMaxTurns) {
    cfgCoachMaxTurns.addEventListener("input", () => syncCoachTurnsControls("number"));
    cfgCoachMaxTurns.addEventListener("change", () => syncCoachTurnsControls("number"));
  }
  if (coachPresetRow) {
    coachPresetRow.querySelectorAll(".preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const preset = String(btn.getAttribute("data-preset") || "");
        if (preset === "conservative") {
          cfgCoachCooldownSec.value = 15;
          cfgCoachMaxTurns.value = 4;
        } else if (preset === "aggressive") {
          cfgCoachCooldownSec.value = 2;
          cfgCoachMaxTurns.value = 12;
        } else {
          cfgCoachCooldownSec.value = 8;
          cfgCoachMaxTurns.value = 8;
        }
        syncCoachCooldownControls("number");
        syncCoachTurnsControls("number");
        setConfigDirty(true);
      });
    });
  }
  if (autoStopPresets) {
    autoStopPresets.querySelectorAll(".preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const minutes = clampDecimal(btn.getAttribute("data-minutes"), 0, 5, 1.25, 2);
        cfgAutoStopSilenceSec.value = minutes;
        syncAutoStopControls("number");
      });
    });
  }
  if (settingsTab) {
    settingsTab.addEventListener("input", (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const id = target.id || "";
      const ignore = (
        id === "showTs"
        || id === "fontFamilyEn"
        || id === "fontFamilyAr"
        || id === "fontScaleEn"
        || id === "fontScaleAr"
        || id === "themeToggleBtn"
      );
      if (ignore) return;
      if (target.closest(".settings-actions")) return;
      setConfigDirty(true);
    });
    settingsTab.addEventListener("change", (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const id = target.id || "";
      const ignore = (
        id === "showTs"
        || id === "fontFamilyEn"
        || id === "fontFamilyAr"
        || id === "fontScaleEn"
        || id === "fontScaleAr"
        || id === "themeToggleBtn"
      );
      if (ignore) return;
      if (target.closest(".settings-actions")) return;
      setConfigDirty(true);
    });
  }
  transcriptSearch.addEventListener("input", () => {
    state.filters.transcript = transcriptSearch.value;
    renderFinals();
  });

  logsSearch.addEventListener("input", () => {
    state.filters.logs = logsSearch.value;
    renderLogs();
  });

  askCoachBtn.addEventListener("click", () => askCoach().catch(notifyError));
  clearCoachBtn.addEventListener("click", () => clearCoach().catch(notifyError));

  copyLogsBtn.addEventListener("click", () => copyLogs().then(() => showToast("Logs copied.", "success")).catch(notifyError));
  clearLogsBtn.addEventListener("click", () => withBusy(clearLogsBtn, "Clearing", async () => {
    await clearLogs();
    showToast("Logs cleared.", "info");
  }).catch(notifyError));
  exportLogsBtn.addEventListener("click", () => {
    exportLogsText();
    showToast("Logs exported.", "success");
  });
  if (exportTranscriptJsonBtn) {
    exportTranscriptJsonBtn.addEventListener("click", () => {
      exportTranscriptJson();
      showToast("Transcript JSON exported.", "success");
    });
  }
  if (exportTranscriptCsvBtn) {
    exportTranscriptCsvBtn.addEventListener("click", () => {
      exportTranscriptCsv();
      showToast("Transcript CSV exported.", "success");
    });
  }
  if (exportBookmarksJsonBtn) {
    exportBookmarksJsonBtn.addEventListener("click", () => {
      exportBookmarksJson();
      showToast("Bookmarks JSON exported.", "success");
    });
  }
  if (exportBookmarksCsvBtn) {
    exportBookmarksCsvBtn.addEventListener("click", () => {
      exportBookmarksCsv();
      showToast("Bookmarks CSV exported.", "success");
    });
  }
  if (bookmarksOnlyBtn) {
    bookmarksOnlyBtn.addEventListener("click", () => {
      state.filters.bookmarksOnly = !state.filters.bookmarksOnly;
      bookmarksOnlyBtn.classList.toggle("active", state.filters.bookmarksOnly);
      bookmarksOnlyBtn.setAttribute("aria-pressed", state.filters.bookmarksOnly ? "true" : "false");
      renderFinals();
    });
  }
  timeline.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;
    const btn = target.closest(".bookmark-btn");
    if (!btn) return;
    closeBookmarkMenu();
    const key = String(btn.getAttribute("data-key") || "").trim();
    if (!key) return;
    toggleBookmarkForKey(key, { forceRemove: !!ev.shiftKey, anchorEl: btn });
  });
  if (bookmarkMenuEditBtn) {
    bookmarkMenuEditBtn.addEventListener("click", () => {
      const key = state.bookmarkUi.menuKey;
      if (!key) return;
      closeBookmarkMenu();
      openBookmarkModal("edit", key);
    });
  }
  if (bookmarkMenuRemoveBtn) {
    bookmarkMenuRemoveBtn.addEventListener("click", () => {
      const key = state.bookmarkUi.menuKey;
      if (!key) return;
      delete state.bookmarks[key];
      saveBookmarks();
      renderFinals(true);
      closeBookmarkMenu();
      showToast("Bookmark removed.", "info");
    });
  }
  if (bookmarkModalCancelBtn) {
    bookmarkModalCancelBtn.addEventListener("click", () => closeBookmarkModal());
  }
  if (bookmarkModalSaveBtn) {
    bookmarkModalSaveBtn.addEventListener("click", () => {
      const key = state.bookmarkUi.modalKey;
      if (!key) return;
      const note = String(bookmarkNoteInput?.value || "").trim();
      if (state.bookmarkUi.modalMode === "edit" && state.bookmarks[key]) {
        state.bookmarks[key] = { ...state.bookmarks[key], note };
        saveBookmarks();
        renderFinals(true);
        showToast("Bookmark updated.", "success");
      } else {
        toggleBookmarkForKey(key, { note });
      }
      closeBookmarkModal();
    });
  }
  document.addEventListener("click", (ev) => {
    const target = ev.target;
    if (!(target instanceof Element)) return;
    if (bookmarkMenu && !bookmarkMenu.classList.contains("hidden")) {
      if (!target.closest("#bookmarkMenu") && !target.closest(".bookmark-btn")) {
        closeBookmarkMenu();
      }
    }
    if (bookmarkModal && !bookmarkModal.classList.contains("hidden")) {
      if (target === bookmarkModal) closeBookmarkModal();
    }
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.defaultPrevented) return;
    const tag = (ev.target && ev.target.tagName ? ev.target.tagName.toLowerCase() : "");
    const typing = tag === "input" || tag === "textarea" || tag === "select";
    if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter" && !typing) {
      ev.preventDefault();
      startBtn.click();
      return;
    }
    if (ev.key === "Escape" && !typing) {
      if (bookmarkModal && !bookmarkModal.classList.contains("hidden")) {
        ev.preventDefault();
        closeBookmarkModal();
        return;
      }
      if (bookmarkMenu && !bookmarkMenu.classList.contains("hidden")) {
        ev.preventDefault();
        closeBookmarkMenu();
        return;
      }
      ev.preventDefault();
      stopBtn.click();
    }
  });

  loadUiPrefs();
  loadBookmarks();
  applyTheme();
  applyTimestampVisibility();
  applyFontSettings();
  applySettingsAccordionPrefs();
  bindSettingsAccordionPrefs();
  applyLivePanelHeight(state.ui.livePanelHeight);
  syncCoachControlsUI();
  renderAutoStopHint();
  renderAutoStopPresetState();
  renderSilenceGuardChip();
  renderTelemetryHud();
  setupTimelineDivider();

  request("/api/state")
    .then((snapshot) => {
      renderSnapshot(snapshot);
      if (snapshot.config) setConfigUI(snapshot.config);
    })
    .catch(() => {});

  loadAudioDevices().catch(() => {});

  connectSocket();
  setInterval(() => {
    renderTimeStrip();
    renderSilenceGuardChip();
  }, 500);
})();
