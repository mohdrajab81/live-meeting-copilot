(function () {
  const MAX_ROWS = 300;
  const STICKY_THRESHOLD = 80;
  const UI_PREFS_KEY = "translator_ui_prefs_v2";
  const BOOKMARKS_KEY = "translator_bookmarks_v1";
  const API_TOKEN_KEY = "translator_api_token_v1";
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

  const timeline = document.getElementById("timeline");
  const timelineDivider = document.getElementById("timelineDivider");
  const workspaceShell = document.querySelector(".workspace-shell");
  const enInterim = document.getElementById("enInterim");
  const arInterim = document.getElementById("arInterim");
  const enLiveLabel = document.getElementById("enLiveLabel");
  const arLiveLabel = document.getElementById("arLiveLabel");
  const enLiveState = document.getElementById("enLiveState");
  const arLiveState = document.getElementById("arLiveState");
  const transcriptSearch = document.getElementById("transcriptSearch");
  const logsEl = document.getElementById("logs");
  const logsSearch = document.getElementById("logsSearch");
  const leftRail = document.getElementById("leftRail");
  const navToggleBtn = document.getElementById("navToggleBtn");
  const navCollapseBtn = document.getElementById("navCollapseBtn");
  const navBackdrop = document.getElementById("navBackdrop");

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
  const settingsValidationSummary = document.getElementById("settingsValidationSummary");
  const settingsTab = document.getElementById("settingsTab");

  const copyLogsBtn = document.getElementById("copyLogsBtn");
  const clearLogsBtn = document.getElementById("clearLogsBtn");
  const exportLogsBtn = document.getElementById("exportLogsBtn");
  const exportTranscriptJsonBtn = document.getElementById("exportTranscriptJsonBtn");
  const exportTranscriptCsvBtn = document.getElementById("exportTranscriptCsvBtn");
  const exportBookmarksJsonBtn = document.getElementById("exportBookmarksJsonBtn");
  const exportBookmarksCsvBtn = document.getElementById("exportBookmarksCsvBtn");
  const transcriptExportMenuBtn = document.getElementById("transcriptExportMenuBtn");
  const transcriptExportMenu = document.getElementById("transcriptExportMenu");
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
  const coachAskPanel = document.getElementById("coachAskPanel");
  const askCoachBtn = document.getElementById("askCoachBtn");
  const clearCoachBtn = document.getElementById("clearCoachBtn");
  const coachStatusEl = document.getElementById("coachStatus");
  const coachActionDeck = document.getElementById("coachActionDeck");
  const coachRecoPrevBtn = document.getElementById("coachRecoPrevBtn");
  const coachRecoNextBtn = document.getElementById("coachRecoNextBtn");
  const coachRecoPage = document.getElementById("coachRecoPage");
  const coachKpiStatus = document.getElementById("coachKpiStatus");
  const topicsAgendaInput = document.getElementById("topicsAgendaInput");
  const topicsEnableAuto = document.getElementById("topicsEnableAuto");
  const topicsAllowNew = document.getElementById("topicsAllowNew");
  const topicsIntervalSec = document.getElementById("topicsIntervalSec");
  const topicsWindowSec = document.getElementById("topicsWindowSec");
  const topicsSaveBtn = document.getElementById("topicsSaveBtn");
  const topicsAnalyzeBtn = document.getElementById("topicsAnalyzeBtn");
  const topicsClearBtn = document.getElementById("topicsClearBtn");
  const topicsTopActions = document.getElementById("topicsTopActions");
  const topicsExportMenuWrap = document.getElementById("topicsExportMenuWrap");
  const topicsStatusEl = document.getElementById("topicsStatus");
  const topicsListEl = document.getElementById("topicsList");
  const topicsGroupBy = document.getElementById("topicsGroupBy");
  const topicsSortBy = document.getElementById("topicsSortBy");
  const topicsSearch = document.getElementById("topicsSearch");
  const topicsDensityToggle = document.getElementById("topicsDensityToggle");
  const topicsChunkMode = document.getElementById("topicsChunkMode");
  const topicsWindowRow = document.getElementById("topicsWindowRow");
  const topicsBoardControls = document.getElementById("topicsBoardControls");
  const topicsBoardPane = document.getElementById("topicsBoardPane");
  const topicsRunsPane = document.getElementById("topicsRunsPane");
  const topicsDefinitionsPane = document.getElementById("topicsDefinitionsPane");
  const topicsSettingsPane = document.getElementById("topicsSettingsPane");
  const topicsRunsList = document.getElementById("topicsRunsList");
  const topicsSubtabButtons = Array.from(document.querySelectorAll(".topics-subtab-btn"));
  const topicsDefinitionsList = document.getElementById("topicsDefinitionsList");
  const topicsDefinitionEditorTitle = document.getElementById("topicsDefinitionEditorTitle");
  const topicDefIdInput = document.getElementById("topicDefIdInput");
  const topicDefNameInput = document.getElementById("topicDefNameInput");
  const topicDefDurationInput = document.getElementById("topicDefDurationInput");
  const topicDefPriorityInput = document.getElementById("topicDefPriorityInput");
  const topicDefCommentsInput = document.getElementById("topicDefCommentsInput");
  const topicDefSaveBtn = document.getElementById("topicDefSaveBtn");
  const topicDefCancelBtn = document.getElementById("topicDefCancelBtn");
  const topicsDefinitionsValidation = document.getElementById("topicsDefinitionsValidation");
  const topicsKpiCount = document.getElementById("topicsKpiCount");
  const topicsKpiCovered = document.getElementById("topicsKpiCovered");
  const exportTopicsJsonBtn = document.getElementById("exportTopicsJsonBtn");
  const exportTopicsCsvBtn = document.getElementById("exportTopicsCsvBtn");
  const topicsExportMenuBtn = document.getElementById("topicsExportMenuBtn");
  const topicsExportMenu = document.getElementById("topicsExportMenu");
  const logsCompactToggle = document.getElementById("logsCompactToggle");
  const logsPinnedList = document.getElementById("logsPinnedList");
  const clearPinnedLogsBtn = document.getElementById("clearPinnedLogsBtn");
  const logsKpiVisible = document.getElementById("logsKpiVisible");
  const logsKpiErrors = document.getElementById("logsKpiErrors");
  const severityButtons = Array.from(document.querySelectorAll(".severity-chip"));
  const settingsSummary = document.getElementById("settingsSummary");
  const settingsKpiDirty = document.getElementById("settingsKpiDirty");
  const settingsIndexButtons = Array.from(document.querySelectorAll(".settings-index-btn"));
  const transcriptMetaEntries = document.getElementById("transcriptMetaEntries");
  const transcriptMetaBookmarks = document.getElementById("transcriptMetaBookmarks");
  const insightBookmarkSummary = document.getElementById("insightBookmarkSummary");
  const insightBookmarksList = document.getElementById("insightBookmarksList");
  const insightSessionStats = document.getElementById("insightSessionStats");
  const insightFilterButtons = Array.from(document.querySelectorAll("[data-filter]"));
  const insightSpeakerButtons = Array.from(document.querySelectorAll("[data-speaker]"));

  const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
  const tabPanes = Array.from(document.querySelectorAll(".tab-pane"));
  const settingsAccordions = Array.from(document.querySelectorAll(".settings-accordion"));
  const toastHost = document.getElementById("toastHost");

  function loadApiToken() {
    try {
      const params = new URLSearchParams(window.location.search || "");
      const fromQuery = String(params.get("token") || params.get("api_token") || "").trim();
      if (fromQuery) {
        localStorage.setItem(API_TOKEN_KEY, fromQuery);
        return fromQuery;
      }
      return String(localStorage.getItem(API_TOKEN_KEY) || "").trim();
    } catch (_err) {
      return "";
    }
  }

  const state = {
    apiToken: loadApiToken(),
    socket: null,
    reconnectAttempts: 0,
    reconnectTimer: null,
    finals: [],
    livePartials: {},
    liveHeldFinal: null,
    logs: [],
    coachHints: [],
    coachCursor: {
      lastTopKey: "",
      lastCount: 0,
    },
    coachPending: false,
    coachConfigured: false,
    topics: {
      configured: false,
      settings_saved: false,
      enabled: false,
      allow_new_topics: true,
      chunk_mode: "since_last",
      interval_sec: 60,
      window_sec: 90,
      pending: false,
      last_run_ts: 0,
      last_final_index: 0,
      last_error: "",
      agenda: [],
      definitions: [],
      items: [],
      runs: [],
    },
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
      livePanelHeight: 156,
      theme: "dark",
      navCollapsed: false,
      mobileNavOpen: false,
      activeSection: "transcriptTab",
      pageLayouts: {
        topicsSetupCollapsed: false,
      },
      pageSubtabs: {
        topics: "board",
      },
      transcriptView: {
        preset: "all",
        speaker: "any",
        recentMinutes: 10,
      },
      coachView: {
        activeIndex: 0,
      },
      topicsView: {
        groupBy: "status",
        sortBy: "duration_desc",
        search: "",
        density: "comfortable",
        expandedStatements: {},
      },
      topicsDefinitionsView: {
        editingId: "",
      },
      logsView: {
        severity: "all",
        compact: false,
        pinned: {},
      },
      settingsView: {
        summaryExpanded: true,
      },
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
    const base = `${proto}://${location.host}/ws`;
    const token = String(state.apiToken || "").trim();
    if (!token) return base;
    return `${base}?token=${encodeURIComponent(token)}`;
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

  function normalizeTopicKey(text) {
    return normalizeText(String(text || "").replace(/\s+/g, " ").trim());
  }

  function clipText(value, limit) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length <= limit) return text;
    return `${text.slice(0, Math.max(0, limit - 1)).trimEnd()}...`;
  }

  function cleanCoachSuggestionText(value) {
    let text = String(value || "").replace(/\r/g, "\n");
    text = text.replace(/\*\*/g, "");
    text = text.replace(/```/g, "");
    text = text.replace(/^\s*suggested reply\s*:\s*/im, "");
    return text.trim();
  }

  function speakerFamily(value) {
    const key = normalizeText(value);
    if (!key) return "any";
    if (key.includes("remote")) return "remote";
    if (key.includes("local")) return "local";
    if (key.includes("you")) return "local";
    return key;
  }

  function logKey(log) {
    return `${Math.round(Number(log?.ts || 0) * 1000)}:${String(log?.level || "")}:${String(log?.message || "")}`;
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: 1100px)").matches;
  }

  function applyNavCollapsed() {
    const collapsed = !!state.ui.navCollapsed && !isMobileLayout();
    document.body.classList.toggle("nav-collapsed", collapsed);
    if (navCollapseBtn) {
      navCollapseBtn.textContent = collapsed ? ">>" : "Collapse";
      navCollapseBtn.setAttribute("aria-label", collapsed ? "Expand navigation" : "Collapse navigation");
      navCollapseBtn.title = collapsed ? "Expand navigation" : "Collapse navigation";
    }
  }

  function applyMobileNav() {
    const open = !!state.ui.mobileNavOpen && isMobileLayout();
    document.body.classList.toggle("nav-open", open);
    if (navToggleBtn) navToggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
    if (leftRail) leftRail.setAttribute("data-open", open ? "true" : "false");
    if (navBackdrop) navBackdrop.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function closeMobileNav() {
    if (!state.ui.mobileNavOpen) return;
    state.ui.mobileNavOpen = false;
    applyMobileNav();
    saveUiPrefs();
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
    // Telemetry pills were intentionally removed from topbar in UX V3.
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
    if (settingsDirtyIndicator) settingsDirtyIndicator.classList.toggle("hidden", !state.configDirty);
    if (settingsKpiDirty) settingsKpiDirty.textContent = state.configDirty ? "Yes" : "No";
    renderSettingsSummary();
    validateSettingsInputs(true);
  }

  function setFieldValidation(el, message) {
    if (!el || !el.id) return;
    const selector = `.validation-field[data-for="${el.id}"]`;
    let note = document.querySelector(selector);
    if (!message) {
      el.classList.remove("invalid");
      if (note) note.remove();
      return;
    }
    el.classList.add("invalid");
    if (!note) {
      note = document.createElement("div");
      note.className = "validation-field";
      note.dataset.for = el.id;
      if (el.parentElement) el.parentElement.appendChild(note);
    }
    note.textContent = message;
  }

  function validateSettingsInputs(render) {
    const errors = {};
    const isDual = cfgCaptureMode?.value === "dual";
    const localId = String(cfgLocalInputDeviceId?.value || "").trim();
    const remoteId = String(cfgRemoteInputDeviceId?.value || "").trim();
    if (isDual && !localId) errors[cfgLocalInputDeviceId.id] = "Required in dual mode.";
    if (isDual && !remoteId) errors[cfgRemoteInputDeviceId.id] = "Required in dual mode.";

    const rangeChecks = [
      { el: cfgEnd, min: 50, max: 10000, label: "End silence" },
      { el: cfgCoachCooldownSec, min: 0, max: 120, label: "Coach cooldown" },
      { el: cfgCoachMaxTurns, min: 2, max: 30, label: "Coach max turns" },
      { el: cfgPartialTranslateMinIntervalSec, min: 0.2, max: 10.0, label: "Partial interval" },
      { el: cfgAutoStopSilenceSec, min: 0, max: 5, label: "Auto-stop silence" },
      { el: cfgMaxSessionSec, min: 5, max: 180, label: "Max session" },
    ];
    rangeChecks.forEach((row) => {
      if (!row.el) return;
      const value = Number(row.el.value);
      if (!Number.isFinite(value) || value < row.min || value > row.max) {
        errors[row.el.id] = `${row.label} must be ${row.min}-${row.max}.`;
      }
    });

    const targets = [
      cfgLocalInputDeviceId,
      cfgRemoteInputDeviceId,
      cfgEnd,
      cfgCoachCooldownSec,
      cfgCoachMaxTurns,
      cfgPartialTranslateMinIntervalSec,
      cfgAutoStopSilenceSec,
      cfgMaxSessionSec,
    ];
    if (render) {
      targets.forEach((el) => setFieldValidation(el, errors[el?.id] || ""));
      const messages = Object.values(errors);
      if (settingsValidationSummary) {
        if (messages.length) {
          settingsValidationSummary.textContent = messages[0];
          settingsValidationSummary.classList.remove("hidden");
        } else {
          settingsValidationSummary.textContent = "";
          settingsValidationSummary.classList.add("hidden");
        }
      }
      if (applyConfigBtn) applyConfigBtn.disabled = messages.length > 0;
      if (saveConfigBtn) saveConfigBtn.disabled = messages.length > 0;
    }
    return { ok: Object.keys(errors).length === 0, errors };
  }

  function logLineText(log) {
    return `[${formatTimeWithMs(log.ts)}] [${log.level || "info"}] ${log.message || ""}`;
  }

  function filteredLogs() {
    const query = normalizeText(state.filters.logs).trim();
    const severity = String(state.ui.logsView?.severity || "all");
    return state.logs.filter((log) => {
      const level = normalizeText(log.level || "info");
      if (severity !== "all" && severity !== level) return false;
      if (!query) return true;
      const line = `${level} ${log.message || ""} ${formatTime(log.ts)}`;
      return normalizeText(line).includes(query);
    });
  }

  function renderLogs() {
    if (!logsEl) return;
    logsEl.innerHTML = "";
    logsEl.classList.toggle("logs-compact", state.ui.logsView?.compact === true);
    if (logsCompactToggle) {
      const compact = state.ui.logsView?.compact === true;
      logsCompactToggle.textContent = compact ? "Comfortable rows" : "Compact rows";
      logsCompactToggle.setAttribute("aria-pressed", compact ? "true" : "false");
    }
    const newestFirst = filteredLogs().reverse();
    newestFirst.forEach((log) => {
      const line = document.createElement("div");
      const level = normalizeText(log.level || "info");
      line.className = `line log-line level-${level}`;

      const badge = document.createElement("span");
      badge.className = `log-level level-${level}`;
      badge.textContent = level;

      const ts = document.createElement("span");
      ts.className = "log-ts";
      ts.textContent = formatTimeWithMs(log.ts);

      const message = document.createElement("span");
      message.className = "log-msg";
      message.textContent = log.message || "";

      const pinBtn = document.createElement("button");
      pinBtn.type = "button";
      pinBtn.className = "btn log-pin-btn";
      const key = logKey(log);
      const pinned = !!state.ui.logsView?.pinned?.[key];
      pinBtn.textContent = pinned ? "Unpin" : "Pin";
      pinBtn.setAttribute("aria-label", pinned ? "Unpin log line" : "Pin log line");
      pinBtn.addEventListener("click", () => {
        if (!state.ui.logsView.pinned) state.ui.logsView.pinned = {};
        if (state.ui.logsView.pinned[key]) delete state.ui.logsView.pinned[key];
        else state.ui.logsView.pinned[key] = true;
        saveUiPrefs();
        renderLogs();
      });

      line.appendChild(badge);
      line.appendChild(ts);
      line.appendChild(message);
      line.appendChild(pinBtn);
      logsEl.appendChild(line);
    });

    if (logsKpiVisible) logsKpiVisible.textContent = String(newestFirst.length);
    if (logsKpiErrors) {
      const errors = filteredLogs().filter((x) => normalizeText(x.level) === "error").length;
      logsKpiErrors.textContent = String(errors);
    }
    renderPinnedLogs();
    syncSeverityChips();
  }

  function renderPinnedLogs() {
    if (!logsPinnedList) return;
    logsPinnedList.innerHTML = "";
    const pinnedMap = state.ui.logsView?.pinned || {};
    const pinnedRows = state.logs.filter((log) => pinnedMap[logKey(log)]);
    if (!pinnedRows.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "No pinned incidents yet.";
      logsPinnedList.appendChild(empty);
      return;
    }
    pinnedRows
      .slice()
      .reverse()
      .forEach((log) => {
        const row = document.createElement("div");
        row.className = "pinned-row";
        row.textContent = clipText(logLineText(log), 180);
        logsPinnedList.appendChild(row);
      });
  }

  function syncSeverityChips() {
    if (!severityButtons.length) return;
    const current = String(state.ui.logsView?.severity || "all");
    severityButtons.forEach((btn) => {
      const active = btn.getAttribute("data-severity") === current;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
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
    renderTranscriptInsights();
  }

  function jumpToTimelineKey(key) {
    if (!key) return;
    let target = Array.from(timeline.querySelectorAll(".row")).find((row) => row.dataset.key === key);
    if (!target) {
      state.ui.transcriptView.preset = "all";
      state.filters.bookmarksOnly = false;
      if (bookmarksOnlyBtn) {
        bookmarksOnlyBtn.classList.remove("active");
        bookmarksOnlyBtn.setAttribute("aria-pressed", "false");
      }
      renderFinals(true);
      target = Array.from(timeline.querySelectorAll(".row")).find((row) => row.dataset.key === key);
    }
    if (!target) return;
    target.classList.add("row-focus");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => target.classList.remove("row-focus"), 1200);
  }

  function syncTranscriptPresetButtons() {
    const currentPreset = String(state.ui.transcriptView?.preset || "all");
    const currentSpeaker = String(state.ui.transcriptView?.speaker || "any");
    insightFilterButtons.forEach((btn) => {
      const active = btn.getAttribute("data-filter") === currentPreset;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    insightSpeakerButtons.forEach((btn) => {
      const active = btn.getAttribute("data-speaker") === currentSpeaker;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function renderTranscriptInsights() {
    const bookmarkedRows = state.finals
      .map((item) => {
        const key = finalKey(item);
        const mark = state.bookmarks[key];
        if (!mark) return null;
        return { key, item, note: mark.note || "" };
      })
      .filter(Boolean);

    if (transcriptMetaEntries) transcriptMetaEntries.textContent = `Entries: ${state.finals.length}`;
    if (transcriptMetaBookmarks) transcriptMetaBookmarks.textContent = `Bookmarks: ${bookmarkedRows.length}`;
    syncTranscriptPresetButtons();

    if (!insightBookmarkSummary || !insightBookmarksList || !insightSessionStats) return;
    insightBookmarkSummary.textContent = bookmarkedRows.length
      ? `${bookmarkedRows.length} bookmarked moments`
      : "No bookmarks yet.";
    insightBookmarksList.innerHTML = "";
    bookmarkedRows
      .slice(-8)
      .reverse()
      .forEach((row) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn insight-jump-btn";
        const label = row.item?.speaker_label || "Speaker";
        btn.textContent = `${formatTime(row.item?.ts)} ${label} - ${clipText(row.item?.en, 56)}`;
        btn.title = row.note ? `Note: ${row.note}` : "Jump to bookmark";
        btn.addEventListener("click", () => jumpToTimelineKey(row.key));
        insightBookmarksList.appendChild(btn);
      });
    insightSessionStats.innerHTML = "";
  }

  function setLiveTextWithAutoScroll(el, text) {
    if (!el) return;
    const sticky = isNearBottom(el);
    el.textContent = text;
    if (sticky) scrollToBottom(el);
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

    setLiveTextWithAutoScroll(enInterim, enText);
    setLiveTextWithAutoScroll(arInterim, arText);

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

  function renderCoachActionDeck(hints) {
    if (!coachActionDeck) return;
    coachActionDeck.innerHTML = "";
    coachActionDeck.scrollTop = 0;
    const total = Array.isArray(hints) ? hints.length : 0;
    const maxIndex = Math.max(0, total - 1);
    let activeIndex = Number(state.ui.coachView?.activeIndex || 0);
    if (!Number.isFinite(activeIndex)) activeIndex = 0;
    activeIndex = Math.max(0, Math.min(maxIndex, Math.floor(activeIndex)));
    state.ui.coachView.activeIndex = activeIndex;

    if (coachRecoPage) {
      coachRecoPage.textContent = total ? `${activeIndex + 1} / ${total}` : "0 / 0";
    }
    if (coachRecoPrevBtn) coachRecoPrevBtn.disabled = activeIndex <= 0;
    if (coachRecoNextBtn) coachRecoNextBtn.disabled = total === 0 || activeIndex >= maxIndex;

    const selected = hints[activeIndex];
    if (!selected) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "Latest recommendation appears after the next coach response.";
      coachActionDeck.appendChild(empty);
      return;
    }

    const suggestion = cleanCoachSuggestionText(selected.suggestion || "");
    const trigger = cleanCoachSuggestionText(selected.trigger_en || "");
    const bodyText = (suggestion || trigger || "No recommendation yet.").trim();

    const section = document.createElement("section");
    section.className = "coach-structured-section coach-latest-single";

    if (selected?.ts || selected?.speaker_label) {
      const meta = document.createElement("div");
      meta.className = "coach-meta";
      const label = String(selected.speaker_label || "Manual").trim() || "Manual";
      meta.textContent = `${formatTime(selected.ts)} | ${label}`;
      section.appendChild(meta);
    }

    const body = document.createElement("pre");
    body.className = "coach-structured-body";
    body.textContent = bodyText;
    section.appendChild(body);

    if (suggestion && trigger) {
      const basedOn = document.createElement("div");
      basedOn.className = "muted";
      basedOn.textContent = `Based on: ${trigger}`;
      section.appendChild(basedOn);
    }

    coachActionDeck.appendChild(section);
    body.scrollTop = 0;
  }

  function renderCoachHints() {
    const mergedByGroup = new Map();
    const ordered = [...state.coachHints];
    ordered.forEach((hint, idx) => {
      const gid = hint.group_id || `manual-${idx}`;
      const prev = mergedByGroup.get(gid);
      if (!prev || Number(prev.ts || 0) <= Number(hint.ts || 0)) mergedByGroup.set(gid, hint);
    });
    const hints = Array.from(mergedByGroup.values()).sort(
      (a, b) => Number(b?.ts || 0) - Number(a?.ts || 0)
    );
    const topKey = hints.length
      ? `${Number(hints[0]?.ts || 0)}:${String(hints[0]?.group_id || "")}`
      : "";
    if (
      topKey !== state.coachCursor.lastTopKey
      || hints.length !== state.coachCursor.lastCount
    ) {
      state.ui.coachView.activeIndex = 0;
      state.coachCursor.lastTopKey = topKey;
      state.coachCursor.lastCount = hints.length;
      saveUiPrefs();
    }
    renderCoachActionDeck(hints);

    if (coachStatusEl) {
      if (!state.coachConfigured) {
        coachStatusEl.textContent = "Coach unavailable";
        coachStatusEl.classList.remove("hidden");
      } else if (state.coachPending) {
        coachStatusEl.textContent = "Generating recommendation...";
        coachStatusEl.classList.remove("hidden");
      } else {
        coachStatusEl.textContent = "";
        coachStatusEl.classList.add("hidden");
      }
    }
    if (coachKpiStatus) coachKpiStatus.textContent = state.coachPending ? "Pending" : (state.coachConfigured ? "Ready" : "Off");
  }

  function normalizeTopicDefinition(raw, index) {
    const name = String(raw?.name || "").replace(/\s+/g, " ").trim();
    if (!name) return null;
    const idRaw = String(raw?.id || "").trim();
    const normalizedId = idRaw || `topic-${index + 1}`;
    const priorityRaw = String(raw?.priority || "normal").trim().toLowerCase();
    const priorityMapped = priorityRaw === "mandatory"
      ? "high"
      : (priorityRaw === "optional" ? "normal" : priorityRaw);
    const priority = ["low", "normal", "high"].includes(priorityMapped) ? priorityMapped : "normal";
    return {
      id: normalizedId,
      name,
      expected_duration_min: clampNumber(raw?.expected_duration_min, 0, 600, 0),
      priority,
      comments: String(raw?.comments || "").trim(),
      order: clampNumber(raw?.order, 0, 10000, index),
    };
  }

  function ensureTopicDefinitions() {
    const incoming = Array.isArray(state.topics?.definitions) ? state.topics.definitions : [];
    const normalized = [];
    const seenNames = new Set();
    incoming.forEach((row, idx) => {
      const parsed = normalizeTopicDefinition(row, idx);
      if (!parsed) return;
      const key = normalizeTopicKey(parsed.name);
      if (!key || seenNames.has(key)) return;
      seenNames.add(key);
      normalized.push(parsed);
    });
    if (!normalized.length) {
      const agenda = Array.isArray(state.topics?.agenda) ? state.topics.agenda : [];
      agenda.forEach((name, idx) => {
        const parsed = normalizeTopicDefinition({
          name,
          expected_duration_min: 0,
          priority: "normal",
          comments: "",
          order: idx,
        }, idx);
        if (parsed) normalized.push(parsed);
      });
    }
    normalized.sort((a, b) => {
      if (a.order !== b.order) return a.order - b.order;
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });
    normalized.forEach((row, idx) => { row.order = idx; });
    state.topics.definitions = normalized;
    return normalized;
  }

  function agendaLinesFromInput() {
    const defs = ensureTopicDefinitions();
    return defs.map((row) => row.name).slice(0, 20);
  }

  function syncTopicsSubtabUI() {
    const active = String(state.ui.pageSubtabs?.topics || "board");
    const tabs = topicsSubtabButtons || [];
    tabs.forEach((btn) => {
      const key = String(btn.getAttribute("data-topics-tab") || "board");
      const selected = key === active;
      btn.classList.toggle("active", selected);
      btn.setAttribute("aria-selected", selected ? "true" : "false");
    });
    if (topicsBoardPane) {
      const on = active === "board";
      topicsBoardPane.classList.toggle("active", on);
      topicsBoardPane.hidden = !on;
    }
    if (topicsRunsPane) {
      const on = active === "runs";
      topicsRunsPane.classList.toggle("active", on);
      topicsRunsPane.hidden = !on;
    }
    if (topicsDefinitionsPane) {
      const on = active === "definitions";
      topicsDefinitionsPane.classList.toggle("active", on);
      topicsDefinitionsPane.hidden = !on;
    }
    if (topicsSettingsPane) {
      const on = active === "settings";
      topicsSettingsPane.classList.toggle("active", on);
      topicsSettingsPane.hidden = !on;
    }
    if (topicsBoardControls) topicsBoardControls.classList.toggle("hidden", active !== "board");

    const showTopActions = active === "board" || active === "runs";
    if (topicsAnalyzeBtn) topicsAnalyzeBtn.classList.toggle("hidden", !showTopActions);
    if (topicsClearBtn) topicsClearBtn.classList.toggle("hidden", !showTopActions);
    if (topicsExportMenuWrap) topicsExportMenuWrap.classList.toggle("hidden", !showTopActions);
    if (topicsTopActions) topicsTopActions.classList.toggle("definitions-mode", !showTopActions);
  }

  function resetTopicDefinitionEditor() {
    state.ui.topicsDefinitionsView.editingId = "";
    if (topicsDefinitionEditorTitle) topicsDefinitionEditorTitle.textContent = "Add topic";
    if (topicDefIdInput) topicDefIdInput.value = "";
    if (topicDefNameInput) topicDefNameInput.value = "";
    if (topicDefDurationInput) topicDefDurationInput.value = "0";
    if (topicDefPriorityInput) topicDefPriorityInput.value = "normal";
    if (topicDefCommentsInput) topicDefCommentsInput.value = "";
    if (topicDefSaveBtn) topicDefSaveBtn.textContent = "Add topic";
    if (topicsDefinitionsValidation) {
      topicsDefinitionsValidation.classList.add("hidden");
      topicsDefinitionsValidation.textContent = "";
    }
  }

  function setTopicsUIFromState() {
    const t = state.topics || {};
    const defs = ensureTopicDefinitions();
    if (topicsEnableAuto) topicsEnableAuto.checked = !!t.enabled;
    if (topicsAllowNew) topicsAllowNew.checked = !!t.allow_new_topics;
    if (topicsChunkMode) topicsChunkMode.value = String(t.chunk_mode || "since_last");
    if (topicsIntervalSec) topicsIntervalSec.value = clampNumber(t.interval_sec, 30, 300, 60);
    if (topicsWindowSec) topicsWindowSec.value = clampNumber(t.window_sec, 60, 300, 90);
    if (topicsWindowRow) topicsWindowRow.classList.toggle("hidden", String(t.chunk_mode || "since_last") !== "window");
    if (topicsAgendaInput && document.activeElement !== topicsAgendaInput) {
      topicsAgendaInput.value = defs.map((row) => row.name).join("\n");
    }
    if (topicsGroupBy) topicsGroupBy.value = state.ui.topicsView.groupBy;
    if (topicsSortBy) topicsSortBy.value = state.ui.topicsView.sortBy;
    if (topicsSearch && document.activeElement !== topicsSearch) {
      topicsSearch.value = state.ui.topicsView.search || "";
    }
    if (topicsDensityToggle) {
      const compact = state.ui.topicsView.density === "compact";
      topicsDensityToggle.textContent = compact ? "Comfortable" : "Compact";
      topicsDensityToggle.setAttribute("aria-pressed", compact ? "true" : "false");
    }
    if (topicsListEl) topicsListEl.classList.toggle("compact", state.ui.topicsView.density === "compact");
    syncTopicsSettingsControls();
    syncTopicsSubtabUI();
    const activeEl = document.activeElement;
    const editingInputs = [topicDefNameInput, topicDefDurationInput, topicDefPriorityInput, topicDefCommentsInput];
    const editorBusy = editingInputs.includes(activeEl);
    if (!editorBusy && !state.ui.topicsDefinitionsView.editingId) {
      resetTopicDefinitionEditor();
    }
  }

  function syncTopicsSettingsControls() {
    const autoEnabled = !!topicsEnableAuto?.checked;
    if (topicsIntervalSec) topicsIntervalSec.disabled = !autoEnabled;
    if (topicsChunkMode) topicsChunkMode.disabled = !autoEnabled;
    const chunkMode = String(topicsChunkMode?.value || state.topics?.chunk_mode || "since_last");
    const showWindow = autoEnabled && chunkMode === "window";
    if (topicsWindowRow) topicsWindowRow.classList.toggle("hidden", !showWindow);
    if (topicsWindowSec) topicsWindowSec.disabled = !showWindow;
  }

  function formatTopicSeconds(sec) {
    const total = Math.max(0, Number(sec || 0));
    if (total < 60) return `${Math.round(total)}s`;
    const mins = Math.floor(total / 60);
    const rem = Math.round(total % 60);
    return rem ? `${mins}m ${rem}s` : `${mins}m`;
  }

  function formatTopicGroupLabel(groupBy, key) {
    if (groupBy === "status") {
      if (key === "active") return "Active";
      if (key === "covered") return "Covered";
      if (key === "not_started") return "Not started";
      return "Other";
    }
    if (groupBy === "origin") {
      return key === "agenda" ? "Agenda topics" : "Custom topics";
    }
    return "All topics";
  }

  function getDefinitionByTopicName() {
    const defs = ensureTopicDefinitions();
    const map = new Map();
    defs.forEach((row) => {
      map.set(normalizeTopicKey(row.name), row);
    });
    return map;
  }

  function buildTopicRows() {
    const t = state.topics || {};
    const definitionMap = getDefinitionByTopicName();
    const agendaSet = new Set(
      (Array.isArray(t.agenda) ? t.agenda : []).map((name) => normalizeTopicKey(name))
    );
    const items = Array.isArray(t.items) ? t.items : [];
    return items.map((item) => {
      const keyStatements = Array.isArray(item.key_statements) ? item.key_statements : [];
      const latestStatementTs = keyStatements.reduce((acc, row) => {
        const ts = Number(row?.ts || 0);
        if (!Number.isFinite(ts) || ts <= 0) return acc;
        return Math.max(acc, ts);
      }, 0);
      const updatedTs = Number(item.updated_ts || 0);
      const latestActivityTs = latestStatementTs > 0 ? latestStatementTs : (updatedTs > 0 ? updatedTs : 0);
      const name = String(item.name || "Untitled");
      const key = normalizeTopicKey(name);
      const definition = definitionMap.get(key) || null;
      const originRaw = String(item.origin || "").trim().toLowerCase();
      const origin = ["agenda", "custom"].includes(originRaw)
        ? originRaw
        : (agendaSet.has(key) ? "agenda" : "custom");
      const expandKey = definition?.id
        ? `def:${String(definition.id)}`
        : `${origin}:${key}`;
      return {
        ...item,
        name,
        status: String(item.status || "not_started"),
        time_seconds: Number(item.time_seconds || 0),
        key_statements: keyStatements,
        origin,
        latest_activity_ts: Number(item.latest_activity_ts || latestActivityTs),
        statement_count: Number(item.statement_count || keyStatements.length || 0),
        expected_duration_min: Number(
          definition?.expected_duration_min ?? item.expected_duration_min ?? 0
        ),
        priority: String(definition?.priority || item.priority || "normal"),
        comments: String(definition?.comments || item.comments || ""),
        definition_id: String(definition?.id || item.definition_id || ""),
        definition_order: Number(definition?.order ?? item.definition_order ?? 0),
        ui_expand_key: expandKey,
      };
    });
  }

  function getTopicsViewModel() {
    const view = state.ui.topicsView || {};
    const groupBy = ["status", "origin", "none"].includes(view.groupBy) ? view.groupBy : "status";
    const sortBy = ["duration_desc", "name_asc", "latest_activity"].includes(view.sortBy)
      ? view.sortBy
      : "duration_desc";
    const query = normalizeText(view.search || "").trim();
    const rows = buildTopicRows();

    const filtered = rows.filter((item) => {
      if (!query) return true;
      const statementBlob = item.key_statements
        .map((row) => `${row?.speaker || ""} ${row?.text || ""}`)
        .join(" ");
      const blob = `${item.name} ${item.status} ${item.origin} ${statementBlob}`;
      return normalizeText(blob).includes(query);
    });

    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === "name_asc") {
        return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
      }
      if (sortBy === "latest_activity") {
        if (b.latest_activity_ts !== a.latest_activity_ts) return b.latest_activity_ts - a.latest_activity_ts;
        if (b.time_seconds !== a.time_seconds) return b.time_seconds - a.time_seconds;
        return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
      }
      if (b.time_seconds !== a.time_seconds) return b.time_seconds - a.time_seconds;
      if (b.latest_activity_ts !== a.latest_activity_ts) return b.latest_activity_ts - a.latest_activity_ts;
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });

    if (groupBy === "none") {
      return {
        totalCount: rows.length,
        filteredCount: sorted.length,
        groups: [
          {
            key: "all",
            title: "All topics",
            items: sorted,
          },
        ],
      };
    }

    const groupOrder = groupBy === "status"
      ? ["active", "covered", "not_started", "other"]
      : ["agenda", "custom"];
    const grouped = new Map();
    sorted.forEach((item) => {
      let key = groupBy === "status" ? item.status : item.origin;
      if (groupBy === "status" && !["active", "covered", "not_started"].includes(key)) key = "other";
      if (groupBy === "origin" && !["agenda", "custom"].includes(key)) key = "custom";
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(item);
    });

    const groups = [];
    groupOrder.forEach((key) => {
      const items = grouped.get(key) || [];
      if (!items.length) return;
      groups.push({ key, title: formatTopicGroupLabel(groupBy, key), items });
    });
    grouped.forEach((items, key) => {
      if (groupOrder.includes(key)) return;
      groups.push({ key, title: formatTopicGroupLabel(groupBy, key), items });
    });

    return {
      totalCount: rows.length,
      filteredCount: sorted.length,
      groups,
    };
  }

  function renderTopicsBoard(vm) {
    if (!topicsListEl) return;
    topicsListEl.innerHTML = "";
    topicsListEl.classList.toggle("compact", state.ui.topicsView.density === "compact");
    if (!vm.groups.length || vm.filteredCount === 0) {
      const empty = document.createElement("div");
      empty.className = "topics-empty topics-empty-rich";

      const title = document.createElement("div");
      title.className = "topics-empty-title";

      const sub = document.createElement("div");
      sub.className = "topics-empty-sub";

      const actions = document.createElement("div");
      actions.className = "topics-empty-actions";

      const defs = ensureTopicDefinitions();
      if (!defs.length && !state.topics.allow_new_topics) {
        title.textContent = "No topic definitions yet.";
        sub.textContent = "Open Definitions, add your topics, then save setup.";
        const openDefsBtn = document.createElement("button");
        openDefsBtn.type = "button";
        openDefsBtn.className = "btn";
        openDefsBtn.textContent = "Open Definitions";
        openDefsBtn.addEventListener("click", () => {
          state.ui.pageSubtabs.topics = "definitions";
          syncTopicsSubtabUI();
          saveUiPrefs();
        });
        actions.appendChild(openDefsBtn);
      } else if (!defs.length && state.topics.allow_new_topics) {
        title.textContent = "No tracked topics yet.";
        sub.textContent = "Custom topics are allowed. Speak, then run manual analysis.";
        const analyzeBtn = document.createElement("button");
        analyzeBtn.type = "button";
        analyzeBtn.className = "btn";
        analyzeBtn.textContent = "Analyze now";
        analyzeBtn.disabled = !!state.topics.pending || !state.topics.configured || !state.topics.settings_saved;
        analyzeBtn.addEventListener("click", () => {
          if (topicsAnalyzeBtn) topicsAnalyzeBtn.click();
        });
        actions.appendChild(analyzeBtn);
      } else if (!state.topics.enabled) {
        title.textContent = "Automatic analysis is disabled.";
        sub.textContent = "You can run manual analysis now, or enable automatic runs.";
        const analyzeBtn = document.createElement("button");
        analyzeBtn.type = "button";
        analyzeBtn.className = "btn";
        analyzeBtn.textContent = "Analyze now";
        analyzeBtn.disabled = !!state.topics.pending || !state.topics.configured || !state.topics.settings_saved;
        analyzeBtn.addEventListener("click", () => {
          if (topicsAnalyzeBtn) topicsAnalyzeBtn.click();
        });
        const enableBtn = document.createElement("button");
        enableBtn.type = "button";
        enableBtn.className = "btn";
        enableBtn.textContent = "Enable Automatic";
        enableBtn.addEventListener("click", () => {
          withBusy(enableBtn, "Enabling", async () => {
            if (topicsEnableAuto) topicsEnableAuto.checked = true;
            await saveTopicsSetup();
            showToast("Automatic analysis enabled and saved.", "success");
          }).catch(notifyError);
        });
        actions.appendChild(analyzeBtn);
        actions.appendChild(enableBtn);
      } else {
        title.textContent = "No topics match the current view.";
        sub.textContent = "Clear filters or run analysis after speaking to populate coverage.";
        const analyzeBtn = document.createElement("button");
        analyzeBtn.type = "button";
        analyzeBtn.className = "btn";
        analyzeBtn.textContent = "Analyze now";
        analyzeBtn.disabled = !!state.topics.pending;
        analyzeBtn.addEventListener("click", () => {
          if (topicsAnalyzeBtn) topicsAnalyzeBtn.click();
        });
        const resetBtn = document.createElement("button");
        resetBtn.type = "button";
        resetBtn.className = "btn";
        resetBtn.textContent = "Reset View";
        resetBtn.addEventListener("click", () => {
          state.ui.topicsView.groupBy = "status";
          state.ui.topicsView.sortBy = "duration_desc";
          state.ui.topicsView.search = "";
          saveUiPrefs();
          setTopicsUIFromState();
          renderTopics();
        });
        actions.appendChild(analyzeBtn);
        actions.appendChild(resetBtn);
      }

      empty.appendChild(title);
      empty.appendChild(sub);
      empty.appendChild(actions);
      topicsListEl.appendChild(empty);
      return;
    }

    vm.groups.forEach((group) => {
      const groupWrap = document.createElement("section");
      groupWrap.className = "topics-group";

      const groupHead = document.createElement("div");
      groupHead.className = "topics-group-head";
      const groupTitle = document.createElement("div");
      groupTitle.className = "topics-group-title";
      groupTitle.textContent = group.title;
      const groupMeta = document.createElement("div");
      groupMeta.className = "topics-group-meta";
      const totalSeconds = group.items.reduce((acc, item) => acc + Math.max(0, Number(item.time_seconds || 0)), 0);
      groupMeta.textContent = `${group.items.length} topics | ${formatTopicSeconds(totalSeconds)}`;
      groupHead.appendChild(groupTitle);
      groupHead.appendChild(groupMeta);
      groupWrap.appendChild(groupHead);

      group.items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "topic-item";
        const head = document.createElement("div");
        head.className = "topic-item-head";

        const status = document.createElement("span");
        const rawStatus = String(item.status || "not_started");
        status.className = `topic-status status-${rawStatus}`;
        status.textContent = rawStatus.replace("_", " ");

        const origin = document.createElement("span");
        origin.className = `topic-origin origin-${item.origin}`;
        origin.textContent = item.origin;

        const name = document.createElement("div");
        name.className = "topic-item-name";
        const priority = String(item.priority || "normal");
        const priorityLabel = priority.charAt(0).toUpperCase() + priority.slice(1);
        name.textContent = `${item.name || "Untitled"} (${priorityLabel})`;

        const timeBlock = document.createElement("div");
        timeBlock.className = "topic-item-time-block";
        const time = document.createElement("div");
        time.className = "topic-item-time";
        time.textContent = formatTopicSeconds(item.time_seconds || 0);
        const activity = document.createElement("div");
        activity.className = "topic-item-activity";
        activity.textContent = item.latest_activity_ts
          ? `Last ${formatTime(item.latest_activity_ts)}`
          : "Last --";

        timeBlock.appendChild(time);
        timeBlock.appendChild(activity);
        head.appendChild(status);
        head.appendChild(origin);
        head.appendChild(name);
        head.appendChild(timeBlock);
        card.appendChild(head);

        const rows = Array.isArray(item.key_statements) ? item.key_statements : [];
        if (rows.length) {
          const ul = document.createElement("ul");
          ul.className = "topic-statements";
          const visibleLimit = state.ui.topicsView.density === "compact" ? 4 : 6;
          const expandedMap = state.ui.topicsView.expandedStatements || {};
          const isExpanded = !!expandedMap[item.ui_expand_key];
          const visibleCount = isExpanded ? rows.length : visibleLimit;
          rows.slice(0, visibleCount).forEach((row) => {
            const li = document.createElement("li");
            const ts = row.ts ? formatTime(row.ts) : "";
            const speaker = (row.speaker || "Speaker").trim();
            const text = clipText(row.text || "", state.ui.topicsView.density === "compact" ? 74 : 130);
            li.textContent = ts ? `[${ts}] ${speaker}: ${text}` : `${speaker}: ${text}`;
            ul.appendChild(li);
          });
          if (rows.length > visibleLimit) {
            const more = document.createElement("li");
            more.className = "topic-statements-more";
            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "topic-statements-more-toggle";
            toggle.textContent = isExpanded
              ? "Show less"
              : `+${rows.length - visibleLimit} more`;
            toggle.addEventListener("click", () => {
              const next = { ...(state.ui.topicsView.expandedStatements || {}) };
              if (isExpanded) delete next[item.ui_expand_key];
              else next[item.ui_expand_key] = true;
              state.ui.topicsView.expandedStatements = next;
              saveUiPrefs();
              renderTopics();
            });
            more.appendChild(toggle);
            ul.appendChild(more);
          }
          card.appendChild(ul);
        }
        groupWrap.appendChild(card);
      });
      topicsListEl.appendChild(groupWrap);
    });
  }

  function renderTopicsRuns() {
    if (!topicsRunsList) return;
    topicsRunsList.innerHTML = "";
    const runs = Array.isArray(state.topics?.runs) ? state.topics.runs : [];
    if (!runs.length) {
      const empty = document.createElement("div");
      empty.className = "topics-empty";
      empty.textContent = "No runs yet.";
      topicsRunsList.appendChild(empty);
      return;
    }
    runs.slice().reverse().forEach((run) => {
      const card = document.createElement("div");
      card.className = "topics-activity-item";

      const ts = Number(run?.ts || 0);
      const trigger = String(run?.trigger || "manual");
      const status = String(run?.status || "success");
      const fromIdx = Number(run?.from_final_index || 0);
      const toIdx = Number(run?.to_final_index || 0);
      const chunkTurns = Number(run?.chunk_turns || 0);
      const chunkSec = Number(run?.chunk_seconds || 0);
      const chunkActiveSec = Number(run?.chunk_active_seconds || 0);
      const totalMs = Number(run?.total_ms || 0);
      const summary = (
        status === "error"
          ? `Error: ${String(run?.error || "unknown error")}`
          : `Topics: +${Number(run?.new_topics || 0)} new, ${Number(run?.updated_topics || 0)} updated, ${Number(run?.unchanged_topics || 0)} unchanged`
      );

      const line1 = document.createElement("div");
      line1.className = "topic-run-head";
      line1.textContent = `[${ts ? formatTime(ts) : "--"}] ${trigger.toUpperCase()} | ${status.toUpperCase()} | turns [${fromIdx}..${toIdx}) (${chunkTurns})`;

      const line2 = document.createElement("div");
      line2.className = "topic-run-meta";
      line2.textContent = `chunk=${chunkSec}s | active=${chunkActiveSec}s | mode=${String(run?.chunk_mode || "since_last")} | allow_custom=${Boolean(run?.allow_new_topics)} | total=${totalMs}ms`;

      const line3 = document.createElement("div");
      line3.className = "topic-run-summary";
      line3.textContent = summary;

      card.appendChild(line1);
      card.appendChild(line2);
      card.appendChild(line3);
      topicsRunsList.appendChild(card);
    });
  }

  function renderTopicDefinitionsList() {
    if (!topicsDefinitionsList) return;
    const defs = ensureTopicDefinitions();
    topicsDefinitionsList.innerHTML = "";
    if (!defs.length) {
      const empty = document.createElement("div");
      empty.className = "topics-empty";
      empty.textContent = "No topic definitions yet. Add one to start tracking.";
      topicsDefinitionsList.appendChild(empty);
      return;
    }
    defs.forEach((row, idx) => {
      const card = document.createElement("article");
      card.className = "topic-def-item";

      const top = document.createElement("div");
      top.className = "topic-def-top";
      const name = document.createElement("div");
      name.className = "topic-def-name";
      name.textContent = row.name;
      top.appendChild(name);

      const meta = document.createElement("div");
      meta.className = "topic-def-meta";
      const dur = row.expected_duration_min > 0 ? `${row.expected_duration_min}m` : "duration --";
      meta.textContent = `${dur} | ${row.priority} | order ${idx + 1}`;

      const comments = document.createElement("div");
      comments.className = "muted";
      comments.textContent = row.comments || "No comments";

      const actions = document.createElement("div");
      actions.className = "topic-def-actions";
      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn";
      editBtn.textContent = "Edit";
      editBtn.addEventListener("click", () => {
        state.ui.topicsDefinitionsView.editingId = row.id;
        if (topicsDefinitionEditorTitle) topicsDefinitionEditorTitle.textContent = "Edit topic";
        if (topicDefIdInput) topicDefIdInput.value = row.id;
        if (topicDefNameInput) topicDefNameInput.value = row.name;
        if (topicDefDurationInput) topicDefDurationInput.value = String(row.expected_duration_min || 0);
        if (topicDefPriorityInput) topicDefPriorityInput.value = row.priority || "normal";
        if (topicDefCommentsInput) topicDefCommentsInput.value = row.comments || "";
        if (topicDefSaveBtn) topicDefSaveBtn.textContent = "Update topic";
      });

      const upBtn = document.createElement("button");
      upBtn.type = "button";
      upBtn.className = "btn";
      upBtn.textContent = "Up";
      upBtn.disabled = idx === 0;
      upBtn.addEventListener("click", () => {
        if (idx <= 0) return;
        const copy = [...defs];
        const [moved] = copy.splice(idx, 1);
        copy.splice(idx - 1, 0, moved);
        copy.forEach((it, order) => { it.order = order; });
        commitTopicDefinitions(copy, "Topic order saved.").catch(notifyError);
      });

      const downBtn = document.createElement("button");
      downBtn.type = "button";
      downBtn.className = "btn";
      downBtn.textContent = "Down";
      downBtn.disabled = idx >= defs.length - 1;
      downBtn.addEventListener("click", () => {
        if (idx >= defs.length - 1) return;
        const copy = [...defs];
        const [moved] = copy.splice(idx, 1);
        copy.splice(idx + 1, 0, moved);
        copy.forEach((it, order) => { it.order = order; });
        commitTopicDefinitions(copy, "Topic order saved.").catch(notifyError);
      });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "btn btn-soft-danger";
      deleteBtn.textContent = "Delete";
      deleteBtn.addEventListener("click", () => {
        const next = defs.filter((it) => it.id !== row.id).map((it, order) => ({ ...it, order }));
        if (!topicsAllowNew?.checked && next.length === 0) {
          showTopicsDefinitionsError("Add at least one topic definition when custom topics are disabled.");
          return;
        }
        showTopicsDefinitionsError("");
        commitTopicDefinitions(next, "Topic deleted and saved.").catch(notifyError);
      });

      actions.appendChild(editBtn);
      actions.appendChild(upBtn);
      actions.appendChild(downBtn);
      actions.appendChild(deleteBtn);
      card.appendChild(top);
      card.appendChild(meta);
      card.appendChild(comments);
      card.appendChild(actions);
      topicsDefinitionsList.appendChild(card);
    });
  }

  function renderTopics() {
    const t = state.topics || {};
    const rows = buildTopicRows();
    const vm = getTopicsViewModel();
    const defs = ensureTopicDefinitions();

    const statusParts = [];
    if (!defs.length && !t.allow_new_topics) statusParts.push("No definitions yet");
    else if (!defs.length && t.allow_new_topics) statusParts.push("Custom-only mode");
    else statusParts.push("Definitions ready");
    statusParts.push(t.configured ? "Model ready" : "Model unavailable");
    statusParts.push(t.settings_saved ? "Setup saved" : "Setup not saved");
    statusParts.push(t.enabled ? "Auto on" : "Manual only");
    statusParts.push(`Mode ${String(t.chunk_mode || "since_last")}`);
    if (t.pending) statusParts.push("Updating...");
    if (t.last_error) statusParts.push(`Error: ${t.last_error}`);
    if (!t.pending && !t.last_error && t.last_run_ts) statusParts.push(`Last run ${formatTime(t.last_run_ts)}`);
    if (topicsStatusEl) topicsStatusEl.textContent = statusParts.join(" | ");

    if (topicsKpiCount) topicsKpiCount.textContent = String(defs.length);
    if (topicsKpiCovered) topicsKpiCovered.textContent = String(rows.filter((item) => item.status === "covered").length);

    const canAnalyze = !t.pending && !!t.settings_saved && !!t.configured && (defs.length > 0 || !!t.allow_new_topics);
    if (topicsAnalyzeBtn) topicsAnalyzeBtn.disabled = !canAnalyze;
    if (topicsClearBtn) topicsClearBtn.disabled = !rows.length;
    if (topicsExportMenuBtn) topicsExportMenuBtn.disabled = !rows.length;
    if (topicsSaveBtn) topicsSaveBtn.disabled = !!t.pending || (!t.allow_new_topics && defs.length === 0);

    syncTopicsSubtabUI();
    renderTopicsBoard(vm);
    renderTopicsRuns();
    renderTopicDefinitionsList();
  }

  async function clearTranscript() {
    await request("/api/transcript/clear", "POST");
    state.finals = [];
    state.livePartials = {};
    state.liveHeldFinal = null;
    state.bookmarks = {};
    saveBookmarks();
    renderFinals();
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
      const interval = clampDecimal(config.partial_translate_min_interval_sec, 0.2, 10.0, 0.6, 1);
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
    renderSettingsSummary();
    validateSettingsInputs(true);
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
    const bounded = clampDecimal(raw, 0.2, 10.0, 0.6, 1);
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
      if (typeof parsed.navCollapsed === "boolean") state.ui.navCollapsed = parsed.navCollapsed;
      if (typeof parsed.mobileNavOpen === "boolean") state.ui.mobileNavOpen = parsed.mobileNavOpen;
      if (typeof parsed.activeSection === "string") state.ui.activeSection = parsed.activeSection;
      if (parsed.pageLayouts && typeof parsed.pageLayouts === "object") {
        if (typeof parsed.pageLayouts.topicsSetupCollapsed === "boolean") {
          state.ui.pageLayouts.topicsSetupCollapsed = parsed.pageLayouts.topicsSetupCollapsed;
        }
      }
      if (parsed.pageSubtabs && typeof parsed.pageSubtabs === "object") {
        const topicsSubtab = String(parsed.pageSubtabs.topics || "").trim().toLowerCase();
        if (["board", "definitions", "runs", "settings"].includes(topicsSubtab)) {
          state.ui.pageSubtabs.topics = topicsSubtab;
        } else if (topicsSubtab === "activity") {
          state.ui.pageSubtabs.topics = "runs";
        }
      }
      if (parsed.transcriptView && typeof parsed.transcriptView === "object") {
        const preset = String(parsed.transcriptView.preset || "").trim();
        const recentMinutes = Number(parsed.transcriptView.recentMinutes || 10);
        if (["all", "bookmarked"].includes(preset)) state.ui.transcriptView.preset = preset;
        state.ui.transcriptView.speaker = "any";
        if (Number.isFinite(recentMinutes) && recentMinutes > 0) state.ui.transcriptView.recentMinutes = recentMinutes;
      }
      if (parsed.coachView && typeof parsed.coachView === "object") {
        const activeIndex = Number(parsed.coachView.activeIndex);
        if (Number.isFinite(activeIndex) && activeIndex >= 0) {
          state.ui.coachView.activeIndex = Math.floor(activeIndex);
        }
      }
      if (parsed.topicsView && typeof parsed.topicsView === "object") {
        const groupBy = String(parsed.topicsView.groupBy || "").trim();
        const sortBy = String(parsed.topicsView.sortBy || "").trim();
        const search = String(parsed.topicsView.search || "");
        const density = String(parsed.topicsView.density || "");
        if (["status", "origin", "none"].includes(groupBy)) state.ui.topicsView.groupBy = groupBy;
        if (["duration_desc", "name_asc", "latest_activity"].includes(sortBy)) state.ui.topicsView.sortBy = sortBy;
        state.ui.topicsView.search = search;
        if (["comfortable", "compact"].includes(density)) state.ui.topicsView.density = density;
        if (parsed.topicsView.expandedStatements && typeof parsed.topicsView.expandedStatements === "object") {
          const rawExpanded = parsed.topicsView.expandedStatements;
          const safeExpanded = {};
          Object.entries(rawExpanded).forEach(([k, v]) => {
            const key = String(k || "").trim();
            if (!key) return;
            safeExpanded[key] = !!v;
          });
          state.ui.topicsView.expandedStatements = safeExpanded;
        }
      }
      if (parsed.topicsDefinitionsView && typeof parsed.topicsDefinitionsView === "object") {
        const editingId = String(parsed.topicsDefinitionsView.editingId || "");
        state.ui.topicsDefinitionsView.editingId = editingId;
      }
      if (parsed.logsView && typeof parsed.logsView === "object") {
        const severity = String(parsed.logsView.severity || "").trim();
        if (["all", "debug", "info", "warning", "error"].includes(severity)) {
          state.ui.logsView.severity = severity;
        }
        state.ui.logsView.compact = !!parsed.logsView.compact;
        if (parsed.logsView.pinned && typeof parsed.logsView.pinned === "object") {
          state.ui.logsView.pinned = parsed.logsView.pinned;
        }
      }
      if (parsed.settingsView && typeof parsed.settingsView === "object") {
        if (typeof parsed.settingsView.summaryExpanded === "boolean") {
          state.ui.settingsView.summaryExpanded = parsed.settingsView.summaryExpanded;
        }
      }
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

  function closeExportMenus() {
    const menus = [transcriptExportMenu, topicsExportMenu];
    menus.forEach((menu) => {
      if (!menu) return;
      menu.classList.add("hidden");
    });
    if (transcriptExportMenuBtn) transcriptExportMenuBtn.setAttribute("aria-expanded", "false");
    if (topicsExportMenuBtn) topicsExportMenuBtn.setAttribute("aria-expanded", "false");
  }

  function toggleExportMenu(buttonEl, menuEl) {
    if (!buttonEl || !menuEl) return;
    const opening = menuEl.classList.contains("hidden");
    closeExportMenus();
    if (!opening) return;
    menuEl.classList.remove("hidden");
    buttonEl.setAttribute("aria-expanded", "true");
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
    setActiveSettingsIndex(getActiveSettingsSection());
  }

  function bindSettingsAccordionPrefs() {
    if (!settingsAccordions.length) return;
    settingsAccordions.forEach((el) => {
      el.addEventListener("toggle", () => {
        const key = String(el.dataset.accordion || "").trim();
        if (!key) return;
        state.ui.settingsAccordions[key] = !!el.open;
        if (el.open) setActiveSettingsIndex(key);
        saveUiPrefs();
      });
    });
  }

  function getActiveSettingsSection() {
    const open = settingsAccordions.find((el) => !!el.open);
    if (open) return String(open.dataset.accordion || "system");
    const first = settingsIndexButtons[0];
    if (first) return String(first.getAttribute("data-settings-target") || "system");
    return "system";
  }

  function setActiveSettingsIndex(sectionKey) {
    const activeKey = String(sectionKey || "").trim().toLowerCase();
    if (!settingsIndexButtons.length) return;
    settingsIndexButtons.forEach((btn) => {
      const key = String(btn.getAttribute("data-settings-target") || "").trim().toLowerCase();
      const isActive = key && key === activeKey;
      btn.classList.toggle("active", isActive);
      if (isActive) btn.setAttribute("aria-current", "true");
      else btn.removeAttribute("aria-current");
    });
  }

  function renderSettingsSummary() {
    if (!settingsSummary) return;
    const rows = [];
    rows.push(state.configDirty ? "Pending changes are not yet applied." : "All settings are synced.");
    rows.push(`Capture mode: ${cfgCaptureMode?.value || "single"}`);
    rows.push(`Coach: ${cfgCoachEnabled?.checked ? "enabled" : "disabled"}`);
    if (cfgAutoStopSilenceSec) {
      const mins = clampDecimal(cfgAutoStopSilenceSec.value, 0, 5, 1.25, 2);
      rows.push(mins > 0 ? `Auto-stop: ${mins} minute silence` : "Auto-stop: off");
    }
    if (cfgPartialTranslateMinIntervalSec) {
      rows.push(`Partial translate interval: ${cfgPartialTranslateMinIntervalSec.value}s`);
    }
    settingsSummary.innerHTML = "";
    rows.forEach((line) => {
      const el = document.createElement("div");
      el.className = "settings-summary-row";
      el.textContent = line;
      settingsSummary.appendChild(el);
    });
  }

  function scrollToSettingsSection(sectionKey) {
    if (!sectionKey) return;
    const target = settingsAccordions.find((row) => String(row.dataset.accordion || "") === sectionKey);
    if (!target) return;
    target.open = true;
    setActiveSettingsIndex(sectionKey);
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function applyFontSettings() {
    const selectedFamilyEn = FONT_STACKS[state.ui.fontFamilyEn] || FONT_STACKS.Manrope;
    const selectedFamilyAr = FONT_STACKS[state.ui.fontFamilyAr] || FONT_STACKS["Noto Sans Arabic"];
    const scaleEn = Number(state.ui.fontScaleEn) || 1;
    const scaleAr = Number(state.ui.fontScaleAr) || 1;

    document.documentElement.style.setProperty("--ui-font-en", selectedFamilyEn);
    document.documentElement.style.setProperty("--ui-font-ar", selectedFamilyAr);
    document.documentElement.style.setProperty("--line-en-size", `${(1.08 * scaleEn).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--line-ar-size", `${(1.20 * scaleAr).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--live-en-size", `${(1.02 * scaleEn).toFixed(2)}rem`);
    document.documentElement.style.setProperty("--live-ar-size", `${(1.10 * scaleAr).toFixed(2)}rem`);

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
    if (!workspaceShell) return 180;
    const wrapH = Math.max(240, Math.floor(workspaceShell.clientHeight || 0));
    const minH = 90;
    const maxH = Math.floor(wrapH * 0.6);
    return Math.max(minH, Math.min(maxH, Math.floor(px)));
  }

  function applyLivePanelHeight(px) {
    const height = clampLiveHeight(px);
    state.ui.livePanelHeight = height;
    if (workspaceShell) {
      workspaceShell.style.setProperty("--live-panel-height", `${height}px`);
    }
  }

  function setupTimelineDivider() {
    if (!timelineDivider || !workspaceShell) return;
    const onDrag = (clientY) => {
      const rect = workspaceShell.getBoundingClientRect();
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

  function enforceSingleVisiblePane(activeId) {
    tabPanes.forEach((pane) => {
      const active = pane.id === activeId;
      pane.hidden = !active;
      pane.style.display = active ? "flex" : "none";
      pane.classList.toggle("active", active);
      pane.setAttribute("aria-hidden", active ? "false" : "true");
    });
  }

  function setActiveTab(tabId) {
    const next = tabPanes.some((pane) => pane.id === tabId) ? tabId : "transcriptTab";
    state.ui.activeSection = next;
    closeExportMenus();
    tabButtons.forEach((btn) => {
      const active = btn.dataset.tab === next;
      btn.classList.toggle("active", active);
      if (active) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    enforceSingleVisiblePane(next);
    if (state.ui.mobileNavOpen) {
      state.ui.mobileNavOpen = false;
      applyMobileNav();
    }
    if (next === "transcriptTab") renderTranscriptInsights();
    if (next === "logsTab") renderLogs();
    if (next === "topicsTab") renderTopics();
    if (next === "coachTab") {
      state.ui.coachView.activeIndex = 0;
      renderCoachHints();
    }
    if (next === "settingsTab") {
      renderSettingsSummary();
      setActiveSettingsIndex(getActiveSettingsSection());
    }
    saveUiPrefs();
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
    const topics = msg.topics || {};
    state.topics = {
      ...state.topics,
      configured: !!topics.configured,
      settings_saved: !!topics.settings_saved,
      enabled: !!topics.enabled,
      allow_new_topics: !!topics.allow_new_topics,
      chunk_mode: String(topics.chunk_mode || "since_last"),
      interval_sec: clampNumber(topics.interval_sec, 30, 300, 60),
      window_sec: clampNumber(topics.window_sec, 60, 300, 90),
      pending: !!topics.pending,
      last_run_ts: Number(topics.last_run_ts || 0),
      last_final_index: Number(topics.last_final_index || 0),
      last_error: String(topics.last_error || ""),
      agenda: Array.isArray(topics.agenda) ? topics.agenda : [],
      definitions: Array.isArray(topics.definitions) ? topics.definitions : (Array.isArray(state.topics.definitions) ? state.topics.definitions : []),
      items: Array.isArray(topics.items) ? topics.items : [],
      runs: Array.isArray(topics.runs) ? topics.runs : [],
    };

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
    setTopicsUIFromState();
    renderTopics();
    setStatus(msg.status || "idle", msg.running ? "listening" : "connected");
    applyTimestampVisibility();
    renderSilenceGuardChip();
    renderTimeStrip();
    renderTelemetryHud();
  }

  async function request(path, method, body) {
    const headers = {};
    if (body) headers["Content-Type"] = "application/json";
    const token = String(state.apiToken || "").trim();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(path, {
      method: method || "GET",
      headers: Object.keys(headers).length ? headers : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err?.detail;
      let message = `${path} failed`;
      if (typeof detail === "string" && detail.trim()) {
        message = detail.trim();
      } else if (Array.isArray(detail) && detail.length) {
        const first = detail[0];
        const msg = typeof first?.msg === "string" ? first.msg : "";
        const loc = Array.isArray(first?.loc) ? first.loc.join(".") : "";
        message = loc ? `${loc}: ${msg}` : (msg || message);
      }
      const ex = new Error(message);
      ex.status = res.status;
      ex.detail = detail;
      throw ex;
    }
    return res.json().catch(() => ({}));
  }

  async function applyConfig() {
    const settingsValidation = validateSettingsInputs(true);
    if (!settingsValidation.ok) {
      throw new Error("Fix validation errors before applying settings.");
    }
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
        ? clampDecimal(cfgPartialTranslateMinIntervalSec.value, 0.2, 10.0, 0.6, 1)
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
    const settingsValidation = validateSettingsInputs(true);
    if (!settingsValidation.ok) {
      throw new Error("Fix validation errors before saving settings.");
    }
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

  function exportTopicsJson() {
    const t = state.topics || {};
    const data = {
      exported_at: new Date().toISOString(),
      configured: !!t.configured,
      settings_saved: !!t.settings_saved,
      enabled: !!t.enabled,
      allow_new_topics: !!t.allow_new_topics,
      chunk_mode: String(t.chunk_mode || "since_last"),
      interval_sec: Number(t.interval_sec || 60),
      window_sec: Number(t.window_sec || 90),
      last_final_index: Number(t.last_final_index || 0),
      agenda: Array.isArray(t.agenda) ? t.agenda : [],
      definitions: Array.isArray(t.definitions) ? t.definitions : [],
      items: Array.isArray(t.items) ? t.items : [],
      runs: Array.isArray(t.runs) ? t.runs : [],
    };
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `topics-${stamp}.json`,
      `${JSON.stringify(data, null, 2)}\n`,
      "application/json;charset=utf-8"
    );
  }

  function exportTopicsCsv() {
    const t = state.topics || {};
    const lines = ["topic,status,time_seconds,time_human,statement_time,statement_speaker,statement_text"];
    const items = Array.isArray(t.items) ? t.items : [];
    items.forEach((item) => {
      const statements = Array.isArray(item.key_statements) ? item.key_statements : [];
      if (!statements.length) {
        lines.push(
          [
            escapeCsv(item.name || ""),
            escapeCsv(item.status || ""),
            Number(item.time_seconds || 0),
            escapeCsv(formatTopicSeconds(item.time_seconds || 0)),
            "",
            "",
            "",
          ].join(",")
        );
        return;
      }
      statements.forEach((row) => {
        lines.push(
          [
            escapeCsv(item.name || ""),
            escapeCsv(item.status || ""),
            Number(item.time_seconds || 0),
            escapeCsv(formatTopicSeconds(item.time_seconds || 0)),
            escapeCsv(row.ts ? formatTime(row.ts) : ""),
            escapeCsv(row.speaker || ""),
            escapeCsv(row.text || ""),
          ].join(",")
        );
      });
    });
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    downloadFile(
      `topics-${stamp}.csv`,
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
    state.ui.logsView.pinned = {};
    renderLogs();
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
    state.coachCursor.lastTopKey = "";
    state.coachCursor.lastCount = 0;
    state.ui.coachView.activeIndex = 0;
    saveUiPrefs();
    renderCoachHints();
    showToast("Coach history cleared.", "info");
  }

  function showTopicsDefinitionsError(message) {
    if (!topicsDefinitionsValidation) return;
    if (!message) {
      topicsDefinitionsValidation.textContent = "";
      topicsDefinitionsValidation.classList.add("hidden");
      return;
    }
    topicsDefinitionsValidation.textContent = message;
    topicsDefinitionsValidation.classList.remove("hidden");
  }

  function collectDefinitionEditorValue() {
    return normalizeTopicDefinition({
      id: String(topicDefIdInput?.value || "").trim(),
      name: String(topicDefNameInput?.value || "").trim(),
      expected_duration_min: Number(topicDefDurationInput?.value || 0),
      priority: String(topicDefPriorityInput?.value || "normal"),
      comments: String(topicDefCommentsInput?.value || "").trim(),
      order: Number(state.topics.definitions?.length || 0),
    }, Number(state.topics.definitions?.length || 0));
  }

  function cloneDefinitions(defs) {
    return (Array.isArray(defs) ? defs : []).map((row, idx) => ({
      ...row,
      id: String(row?.id || `topic-${idx + 1}`),
      name: String(row?.name || "").trim(),
      expected_duration_min: clampNumber(row?.expected_duration_min, 0, 600, 0),
      priority: String(row?.priority || "normal"),
      comments: String(row?.comments || "").trim(),
      order: idx,
    }));
  }

  async function commitTopicDefinitions(nextDefs, successMessage) {
    const previousDefs = cloneDefinitions(ensureTopicDefinitions());
    const normalizedNext = cloneDefinitions(nextDefs);
    state.topics.definitions = normalizedNext;
    renderTopicDefinitionsList();
    renderTopics();
    try {
      await saveTopicsSetup();
      if (successMessage) showToast(successMessage, "success");
    } catch (err) {
      state.topics.definitions = previousDefs;
      renderTopicDefinitionsList();
      renderTopics();
      throw err;
    }
  }

  function upsertDefinitionFromEditor() {
    const draft = collectDefinitionEditorValue();
    if (!draft) {
      showTopicsDefinitionsError("Topic name is required.");
      return null;
    }
    const defs = ensureTopicDefinitions();
    const editingId = String(topicDefIdInput?.value || "").trim();
    const duplicate = defs.find((row) => normalizeTopicKey(row.name) === normalizeTopicKey(draft.name) && row.id !== editingId);
    if (duplicate) {
      showTopicsDefinitionsError("Topic name must be unique.");
      return null;
    }

    showTopicsDefinitionsError("");
    let next = [];
    if (editingId) {
      next = defs.map((row) => (row.id === editingId ? { ...row, ...draft, id: editingId } : row));
    } else {
      next = defs.concat([{ ...draft, id: draft.id || `topic-${defs.length + 1}` }]);
    }
    next = next.map((row, idx) => ({ ...row, order: idx }));
    return {
      mode: editingId ? "updated" : "added",
      definitions: next,
    };
  }

  async function saveTopicsSetup() {
    const agenda = agendaLinesFromInput();
    const definitions = ensureTopicDefinitions().map((row, idx) => ({
      ...row,
      order: idx,
    }));
    const allowNew = !!topicsAllowNew?.checked;
    if (!allowNew && definitions.length === 0) {
      throw new Error("Add at least one topic definition when custom topics are disabled.");
    }
    const chunkMode = String(topicsChunkMode?.value || "since_last").trim().toLowerCase() === "window"
      ? "window"
      : "since_last";
    const payload = {
      agenda,
      enabled: !!topicsEnableAuto?.checked,
      allow_new_topics: allowNew,
      chunk_mode: chunkMode,
      interval_sec: clampNumber(topicsIntervalSec?.value, 30, 300, 60),
      window_sec: clampNumber(topicsWindowSec?.value, 60, 300, 90),
      definitions,
    };
    const out = await request("/api/topics/configure", "POST", payload);
    if (out?.topics) {
      state.topics = { ...state.topics, ...out.topics };
      saveUiPrefs();
      setTopicsUIFromState();
      renderTopics();
    }
  }

  async function analyzeTopicsNow() {
    const out = await request("/api/topics/analyze-now", "POST");
    if (out?.topics) {
      state.topics = { ...state.topics, ...out.topics };
      renderTopics();
    }
  }

  async function clearTopics() {
    const out = await request("/api/topics/clear", "POST");
    if (out?.topics) {
      state.topics = { ...state.topics, ...out.topics };
      saveUiPrefs();
      setTopicsUIFromState();
      renderTopics();
    }
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
      const speakerKey = msg.speaker || "default";
      state.liveHeldFinal = {
        en: msg.en || "",
        ar: msg.ar || "",
        speaker: speakerKey,
        speaker_label: msg.speaker_label || "Speaker",
        segment_id: msg.segment_id || "",
        revision: Number(msg.revision || 0),
        ts: msg.ts || Date.now() / 1000,
      };
      delete state.livePartials[speakerKey];
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
      state.ui.coachView.activeIndex = 0;
      state.coachPending = false;
      renderCoachHints();
      return;
    }

    if (msg.type === "topics_update") {
      const topics = msg.topics || {};
      state.topics = {
        ...state.topics,
        configured: !!topics.configured,
        settings_saved: !!topics.settings_saved,
        enabled: !!topics.enabled,
        allow_new_topics: !!topics.allow_new_topics,
        chunk_mode: String(topics.chunk_mode || "since_last"),
        interval_sec: clampNumber(topics.interval_sec, 30, 300, 60),
        window_sec: clampNumber(topics.window_sec, 60, 300, 90),
        pending: !!topics.pending,
        last_run_ts: Number(topics.last_run_ts || 0),
        last_final_index: Number(topics.last_final_index || 0),
        last_error: String(topics.last_error || ""),
        agenda: Array.isArray(topics.agenda) ? topics.agenda : [],
        definitions: Array.isArray(topics.definitions) ? topics.definitions : (Array.isArray(state.topics.definitions) ? state.topics.definitions : []),
        items: Array.isArray(topics.items) ? topics.items : [],
        runs: Array.isArray(topics.runs) ? topics.runs : [],
      };
      setTopicsUIFromState();
      renderTopics();
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
  if (transcriptExportMenuBtn && transcriptExportMenu) {
    transcriptExportMenuBtn.addEventListener("click", () => {
      toggleExportMenu(transcriptExportMenuBtn, transcriptExportMenu);
    });
  }
  if (topicsExportMenuBtn && topicsExportMenu) {
    topicsExportMenuBtn.addEventListener("click", () => {
      toggleExportMenu(topicsExportMenuBtn, topicsExportMenu);
    });
  }
  if (coachRecoPrevBtn) {
    coachRecoPrevBtn.addEventListener("click", () => {
      state.ui.coachView.activeIndex = Math.max(0, Number(state.ui.coachView.activeIndex || 0) - 1);
      saveUiPrefs();
      renderCoachHints();
    });
  }
  if (coachRecoNextBtn) {
    coachRecoNextBtn.addEventListener("click", () => {
      state.ui.coachView.activeIndex = Math.max(0, Number(state.ui.coachView.activeIndex || 0) + 1);
      saveUiPrefs();
      renderCoachHints();
    });
  }
  if (navToggleBtn) {
    navToggleBtn.addEventListener("click", () => {
      state.ui.mobileNavOpen = !state.ui.mobileNavOpen;
      applyMobileNav();
      saveUiPrefs();
    });
  }
  if (navCollapseBtn) {
    navCollapseBtn.addEventListener("click", () => {
      state.ui.navCollapsed = !state.ui.navCollapsed;
      applyNavCollapsed();
      saveUiPrefs();
    });
  }
  if (navBackdrop) {
    navBackdrop.addEventListener("click", () => closeMobileNav());
  }
  window.addEventListener("resize", () => {
    if (!isMobileLayout() && state.ui.mobileNavOpen) {
      state.ui.mobileNavOpen = false;
      applyMobileNav();
      saveUiPrefs();
    }
    applyNavCollapsed();
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
    renderSettingsSummary();
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
      renderSettingsSummary();
      saveUiPrefs();
    });
  }

  cfgCaptureMode.addEventListener("change", () => {
    syncCaptureModeUI();
    syncAudioSourceUI();
    renderSettingsSummary();
  });
  if (cfgCoachEnabled) {
    cfgCoachEnabled.addEventListener("change", () => {
      syncCoachControlsUI();
      renderSettingsSummary();
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
      if (ignore) {
        renderSettingsSummary();
        validateSettingsInputs(true);
        return;
      }
      if (target.closest(".settings-actions")) return;
      setConfigDirty(true);
      validateSettingsInputs(true);
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
      if (ignore) {
        renderSettingsSummary();
        validateSettingsInputs(true);
        return;
      }
      if (target.closest(".settings-actions")) return;
      setConfigDirty(true);
      validateSettingsInputs(true);
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
  if (severityButtons.length) {
    severityButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        state.ui.logsView.severity = String(btn.getAttribute("data-severity") || "all");
        saveUiPrefs();
        renderLogs();
      });
    });
  }
  if (logsCompactToggle) {
    logsCompactToggle.addEventListener("click", () => {
      state.ui.logsView.compact = !state.ui.logsView.compact;
      logsCompactToggle.setAttribute("aria-pressed", state.ui.logsView.compact ? "true" : "false");
      saveUiPrefs();
      renderLogs();
    });
  }
  if (clearPinnedLogsBtn) {
    clearPinnedLogsBtn.addEventListener("click", () => {
      state.ui.logsView.pinned = {};
      saveUiPrefs();
      renderLogs();
    });
  }
  if (topicsGroupBy) {
    topicsGroupBy.addEventListener("change", () => {
      state.ui.topicsView.groupBy = topicsGroupBy.value;
      saveUiPrefs();
      renderTopics();
    });
  }
  if (topicsSortBy) {
    topicsSortBy.addEventListener("change", () => {
      state.ui.topicsView.sortBy = topicsSortBy.value;
      saveUiPrefs();
      renderTopics();
    });
  }
  if (topicsSearch) {
    topicsSearch.addEventListener("input", () => {
      state.ui.topicsView.search = topicsSearch.value;
      saveUiPrefs();
      renderTopics();
    });
  }
  if (topicsDensityToggle) {
    topicsDensityToggle.addEventListener("click", () => {
      state.ui.topicsView.density = state.ui.topicsView.density === "compact" ? "comfortable" : "compact";
      saveUiPrefs();
      setTopicsUIFromState();
      renderTopics();
    });
  }
  if (topicsEnableAuto) {
    topicsEnableAuto.addEventListener("change", () => {
      state.topics.enabled = !!topicsEnableAuto.checked;
      syncTopicsSettingsControls();
      renderTopics();
    });
  }
  if (topicsAllowNew) {
    topicsAllowNew.addEventListener("change", () => {
      state.topics.allow_new_topics = !!topicsAllowNew.checked;
      renderTopics();
    });
  }
  if (topicsChunkMode) {
    topicsChunkMode.addEventListener("change", () => {
      state.topics.chunk_mode = String(topicsChunkMode.value || "since_last");
      syncTopicsSettingsControls();
      renderTopics();
    });
  }
  if (topicsSubtabButtons.length) {
    topicsSubtabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = String(btn.getAttribute("data-topics-tab") || "board");
        state.ui.pageSubtabs.topics = ["board", "definitions", "runs", "settings"].includes(tab) ? tab : "board";
        closeExportMenus();
        saveUiPrefs();
        syncTopicsSubtabUI();
        renderTopics();
      });
    });
  }
  if (topicDefCancelBtn) {
    topicDefCancelBtn.addEventListener("click", () => {
      resetTopicDefinitionEditor();
    });
  }
  if (topicDefSaveBtn) {
    topicDefSaveBtn.addEventListener("click", () => withBusy(topicDefSaveBtn, "Saving", async () => {
      const result = upsertDefinitionFromEditor();
      if (!result) return;
      await commitTopicDefinitions(
        result.definitions,
        result.mode === "added" ? "Topic added and saved." : "Topic updated and saved."
      );
      resetTopicDefinitionEditor();
    }).catch((err) => {
      showTopicsDefinitionsError("Could not save topic definition. Check the input and try again.");
      notifyError(err);
    }));
  }
  if (settingsIndexButtons.length) {
    settingsIndexButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = String(btn.getAttribute("data-settings-target") || "");
        scrollToSettingsSection(target);
      });
    });
  }

  askCoachBtn.addEventListener("click", () => askCoach().catch(notifyError));
  clearCoachBtn.addEventListener("click", () => clearCoach().catch(notifyError));
  if (topicsSaveBtn) {
    topicsSaveBtn.addEventListener("click", () => withBusy(topicsSaveBtn, "Saving", async () => {
      await saveTopicsSetup();
      showToast("Topics setup saved.", "success");
    }).catch(notifyError));
  }
  if (topicsAnalyzeBtn) {
    topicsAnalyzeBtn.addEventListener("click", () => withBusy(topicsAnalyzeBtn, "Analyzing", async () => {
      await analyzeTopicsNow();
      showToast("Topics analyzed.", "success");
    }).catch(notifyError));
  }
  if (topicsClearBtn) {
    topicsClearBtn.addEventListener("click", () => withBusy(topicsClearBtn, "Clearing", async () => {
      await clearTopics();
      showToast("Topics cleared.", "info");
    }).catch(notifyError));
  }

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
      closeExportMenus();
      showToast("Transcript JSON exported.", "success");
    });
  }
  if (exportTranscriptCsvBtn) {
    exportTranscriptCsvBtn.addEventListener("click", () => {
      exportTranscriptCsv();
      closeExportMenus();
      showToast("Transcript CSV exported.", "success");
    });
  }
  if (exportBookmarksJsonBtn) {
    exportBookmarksJsonBtn.addEventListener("click", () => {
      exportBookmarksJson();
      closeExportMenus();
      showToast("Bookmarks JSON exported.", "success");
    });
  }
  if (exportBookmarksCsvBtn) {
    exportBookmarksCsvBtn.addEventListener("click", () => {
      exportBookmarksCsv();
      closeExportMenus();
      showToast("Bookmarks CSV exported.", "success");
    });
  }
  if (exportTopicsJsonBtn) {
    exportTopicsJsonBtn.addEventListener("click", () => {
      exportTopicsJson();
      closeExportMenus();
      showToast("Topics JSON exported.", "success");
    });
  }
  if (exportTopicsCsvBtn) {
    exportTopicsCsvBtn.addEventListener("click", () => {
      exportTopicsCsv();
      closeExportMenus();
      showToast("Topics CSV exported.", "success");
    });
  }
  if (bookmarksOnlyBtn) {
    bookmarksOnlyBtn.addEventListener("click", () => {
      state.filters.bookmarksOnly = !state.filters.bookmarksOnly;
      state.ui.transcriptView.preset = state.filters.bookmarksOnly ? "bookmarked" : "all";
      bookmarksOnlyBtn.classList.toggle("active", state.filters.bookmarksOnly);
      bookmarksOnlyBtn.setAttribute("aria-pressed", state.filters.bookmarksOnly ? "true" : "false");
      saveUiPrefs();
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
    if (!target.closest("[data-export-menu-wrapper]")) {
      closeExportMenus();
    }
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
      if ((transcriptExportMenu && !transcriptExportMenu.classList.contains("hidden")) || (topicsExportMenu && !topicsExportMenu.classList.contains("hidden"))) {
        ev.preventDefault();
        closeExportMenus();
        return;
      }
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
      if (state.ui.mobileNavOpen) {
        ev.preventDefault();
        closeMobileNav();
        return;
      }
      ev.preventDefault();
      stopBtn.click();
    }
  });

  loadUiPrefs();
  state.ui.activeSection = "transcriptTab";
  state.ui.mobileNavOpen = false;
  loadBookmarks();
  applyTheme();
  applyNavCollapsed();
  applyMobileNav();
  applyTimestampVisibility();
  applyFontSettings();
  if (coachAskPanel) coachAskPanel.open = false;
  applySettingsAccordionPrefs();
  bindSettingsAccordionPrefs();
  applyLivePanelHeight(state.ui.livePanelHeight);
  syncCoachControlsUI();
  renderAutoStopHint();
  renderAutoStopPresetState();
  renderSilenceGuardChip();
  renderTelemetryHud();
  setTopicsUIFromState();
  resetTopicDefinitionEditor();
  renderSettingsSummary();
  validateSettingsInputs(true);
  syncSeverityChips();
  enforceSingleVisiblePane("transcriptTab");
  setActiveTab(state.ui.activeSection);
  renderTopics();
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
