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

  // ==========================================================================
  // DOM REFERENCES
  // ==========================================================================

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
  const cfgTranslationEnabled = document.getElementById("cfgTranslationEnabled");
  const showTs = document.getElementById("showTs");
  const timelineHead = document.getElementById("timelineHead");
  const liveStrip = document.getElementById("liveStrip");
  const translationOffBadge = document.getElementById("translationOffBadge");
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
  const topicsStatusEl = document.getElementById("topicsStatus");
  const topicsDefinitionsPane = document.getElementById("topicsDefinitionsPane");
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
  const summaryGenerateBtn = document.getElementById("summaryGenerateBtn");
  const summaryClearBtn = document.getElementById("summaryClearBtn");
  const summaryExportMenuBtn = document.getElementById("summaryExportMenuBtn");
  const summaryExportMenu = document.getElementById("summaryExportMenu");
  const exportSummaryJsonBtn = document.getElementById("exportSummaryJsonBtn");
  const exportSummaryTxtBtn = document.getElementById("exportSummaryTxtBtn");
  const summaryKpiStatus = document.getElementById("summaryKpiStatus");
  const summaryPendingIndicator = document.getElementById("summaryPendingIndicator");
  const summaryError = document.getElementById("summaryError");
  const summaryEmpty = document.getElementById("summaryEmpty");
  const summaryBody = document.getElementById("summaryBody");
  const summaryExecutiveText = document.getElementById("summaryExecutiveText");
  const summaryKeyPointsList = document.getElementById("summaryKeyPointsList");
  const summaryActionItemsList = document.getElementById("summaryActionItemsList");
  const summaryInsightsSection = document.getElementById("summaryInsightsSection");
  const summaryInsightsBody = document.getElementById("summaryInsightsBody");
  const summaryHealthChip = document.getElementById("summaryHealthChip");
  const summaryKeywordsSection = document.getElementById("summaryKeywordsSection");
  const summaryKeywordsMeta = document.getElementById("summaryKeywordsMeta");
  const summaryKeywordSearch = document.getElementById("summaryKeywordSearch");
  const summaryKeywordsList = document.getElementById("summaryKeywordsList");
  const summaryMetaRow = document.getElementById("summaryMetaRow");
  const summaryDecisionsSection = document.getElementById("summaryDecisionsSection");
  const summaryDecisionsList = document.getElementById("summaryDecisionsList");
  const summaryRisksSection = document.getElementById("summaryRisksSection");
  const summaryRisksList = document.getElementById("summaryRisksList");
  const summaryTermsSection = document.getElementById("summaryTermsSection");
  const summaryTermsToggle = document.getElementById("summaryTermsToggle");
  const summaryTermsBody = document.getElementById("summaryTermsBody");
  const summaryTermsList = document.getElementById("summaryTermsList");
  const summaryTopicSection = document.getElementById("summaryTopicSection");
  const summaryAdherenceChip = document.getElementById("summaryAdherenceChip");
  const summaryTopicKpis = document.getElementById("summaryTopicKpis");
  const summaryTopicJourneyWrap = document.getElementById("summaryTopicJourneyWrap");
  const summaryTopicJourneyMeta = document.getElementById("summaryTopicJourneyMeta");
  const summaryTopicJourneyAxis = document.getElementById("summaryTopicJourneyAxis");
  const summaryTopicJourney = document.getElementById("summaryTopicJourney");
  const summaryTopicDonutWrap = document.getElementById("summaryTopicDonutWrap");
  const summaryTopicDonut = document.getElementById("summaryTopicDonut");
  const summaryTopicDonutCenter = document.getElementById("summaryTopicDonutCenter");
  const summaryTopicDonutLegend = document.getElementById("summaryTopicDonutLegend");
  const summaryTopicGroupsWrap = document.getElementById("summaryTopicGroupsWrap");
  const summaryTopicGroups = document.getElementById("summaryTopicGroups");
  const summaryAgendaActualHead = document.getElementById("summaryAgendaActualHead");
  const summaryAgendaActualWrap = document.getElementById("summaryAgendaActualWrap");
  const summaryTopicTimeline = document.getElementById("summaryTopicTimeline");
  const summaryTopicPlaceholder = document.getElementById("summaryTopicPlaceholder");
  const summaryFromFileBtn = document.getElementById("summaryFromFileBtn");
  const cfgSummaryEnabled = document.getElementById("cfgSummaryEnabled");
  const cfgSummaryTopicDurationMode = document.getElementById("cfgSummaryTopicDurationMode");
  const cfgSummaryTopicGapThresholdSec = document.getElementById("cfgSummaryTopicGapThresholdSec");

  // File analysis modal
  const fileAnalysisModal = document.getElementById("fileAnalysisModal");
  const fileModalCloseBtn = document.getElementById("fileModalCloseBtn");
  const fileDropZone = document.getElementById("fileDropZone");
  const transcriptFileInput = document.getElementById("transcriptFileInput");
  const fileModalFilename = document.getElementById("fileModalFilename");
  const fileModalAnalyseBtn = document.getElementById("fileModalAnalyseBtn");
  const fileModalPending = document.getElementById("fileModalPending");
  const fileModalError = document.getElementById("fileModalError");

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
  const insightFilterButtons = Array.from(document.querySelectorAll("[data-filter]"));
  const insightSpeakerButtons = Array.from(document.querySelectorAll("[data-speaker]"));

  const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
  const tabPanes = Array.from(document.querySelectorAll(".tab-pane"));
  const settingsAccordions = Array.from(document.querySelectorAll(".settings-accordion"));
  const toastHost = document.getElementById("toastHost");

  // ==========================================================================
  // AUTH + LOCAL STATE BOOTSTRAP
  // ==========================================================================

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
      definitions: [],
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
        topics: "definitions",
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
    summary: {
      pending: false,
      generated_ts: null,
      executive_summary: "",
      key_points: [],
      action_items: [],
      topic_key_points: [],
      entities: [],
      decisions_made: [],
      risks_and_blockers: [],
      key_terms_defined: [],
      metadata: {},
      topic_breakdown: [],
      agenda_adherence_pct: null,
      meeting_insights: {},
      keyword_index: [],
      error: "",
    },
  };

  // ==========================================================================
  // CORE UTILITIES
  // ==========================================================================

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

  function toFiniteNumber(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function toOptionalNumber(value) {
    if (value === null || value === undefined) return null;
    if (typeof value === "string" && value.trim() === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function formatMinutesShort(minutes) {
    const totalSec = Math.max(0, Math.round(toFiniteNumber(minutes, 0) * 60));
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}m ${secs}s`;
  }

  function formatMinutesDelta(minutes) {
    const value = toFiniteNumber(minutes, 0);
    const sign = value < 0 ? "-" : "+";
    const totalSec = Math.max(0, Math.round(Math.abs(value) * 60));
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${sign}${mins}m ${secs}s`;
  }

  function formatClockFromSeconds(totalSec) {
    const sec = Math.max(0, Math.round(toFiniteNumber(totalSec, 0)));
    const hh = Math.floor(sec / 3600);
    const mm = Math.floor((sec % 3600) / 60);
    const ss = sec % 60;
    if (hh > 0) {
      return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
    }
    return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  }

  function formatClockTime(tsSec) {
    const sec = toFiniteNumber(tsSec, 0);
    if (sec <= 0) return "--:--:--";
    if (sec < 1_000_000_000) return formatClockFromSeconds(sec);
    return formatTime(sec);
  }

  function formatTimelinePoint(vm, sec, tsSec = null) {
    const absTs = toFiniteNumber(tsSec, 0);
    if (vm?.hasRealTiming) {
      if (absTs > 0) return formatClockTime(absTs);
      const baseline = toFiniteNumber(vm.timelineStartTs, 0);
      if (baseline > 0) {
        const offset = Math.max(0, toFiniteNumber(sec, 0));
        return formatClockTime(baseline + offset);
      }
    }
    return formatClockFromSeconds(sec);
  }

  function parseUtteranceIdNumber(value) {
    const raw = String(value || "").trim().toUpperCase();
    const match = raw.match(/^U(\d{1,6})$/);
    if (!match) return null;
    return Number(match[1]);
  }

  const TOPIC_COLORS = [
    "#4E9BFF",
    "#53D8A8",
    "#F5B35C",
    "#FF7E7E",
    "#8E9CFF",
    "#34C8D9",
    "#E69DFF",
    "#B8D86D",
    "#FF9E6E",
    "#74D3BE",
  ];

  function topicColorByName(name) {
    const text = String(name || "").trim();
    if (!text) return TOPIC_COLORS[0];
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
      hash = ((hash << 5) - hash) + text.charCodeAt(i);
      hash |= 0;
    }
    return TOPIC_COLORS[Math.abs(hash) % TOPIC_COLORS.length];
  }

  function cleanCoachSuggestionText(value) {
    let text = String(value || "").replace(/\r/g, "\n");
    text = text.replace(/\*\*/g, "");
    text = text.replace(/```/g, "");
    text = text.replace(/^\s*suggested reply\s*:\s*/im, "");
    return text.trim();
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
    if (!localId) missing.push("Local Input Device");
    if (!remoteId) missing.push("Remote Input Device");
    return {
      ok: false,
      message: `Dual Input requires both devices selected. Missing: ${missing.join(", ")}`,
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
      { el: cfgEnd, min: 50, max: 10000, label: "Finalization silence" },
      { el: cfgCoachCooldownSec, min: 0, max: 120, label: "Coach cooldown" },
      { el: cfgCoachMaxTurns, min: 2, max: 30, label: "Context window turns" },
      { el: cfgPartialTranslateMinIntervalSec, min: 0.2, max: 10.0, label: "Translation update interval" },
      { el: cfgAutoStopSilenceSec, min: 0, max: 5, label: "Auto-stop silence minutes" },
      { el: cfgMaxSessionSec, min: 5, max: 180, label: "Hard session limit" },
      { el: cfgSummaryTopicGapThresholdSec, min: 0, max: 300, label: "Gap merge threshold" },
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
      cfgSummaryTopicGapThresholdSec,
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

  // ==========================================================================
  // LOGS + TRANSCRIPT RENDERING
  // ==========================================================================

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
    const ts = Number(item.ts || Date.now() / 1000);
    const startTsRaw = Number(item.start_ts ?? ts);
    const startTs = Number.isFinite(startTsRaw) ? Math.min(startTsRaw, ts) : ts;
    const endTsRaw = Number(item.end_ts ?? ts);
    const endTsClamped = Number.isFinite(endTsRaw) ? Math.max(startTs, Math.min(endTsRaw, ts)) : ts;
    const durationRaw = Number(item.duration_sec);
    const durationSec = Number.isFinite(durationRaw)
      ? Math.max(0, durationRaw)
      : Math.max(0, endTsClamped - startTs);

    const normalized = {
      en: item.en || "",
      ar: item.ar || "",
      speaker: item.speaker || "default",
      speaker_label: item.speaker_label || "Speaker",
      segment_id: item.segment_id || "",
      revision: Number(item.revision || 0),
      ts,
      start_ts: startTs,
      end_ts: endTsClamped,
      duration_sec: durationSec,
      offset_sec: item.offset_sec == null ? null : Number(item.offset_sec),
      timing_source: item.timing_source || "event_only",
      recognizer_session_id: item.recognizer_session_id || "",
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

    if (!insightBookmarkSummary || !insightBookmarksList) return;
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

  // ==========================================================================
  // TOPICS MODEL + TOPICS UI
  // ==========================================================================

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
    normalized.sort((a, b) => {
      if (a.order !== b.order) return a.order - b.order;
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });
    normalized.forEach((row, idx) => { row.order = idx; });
    state.topics.definitions = normalized;
    return normalized;
  }

  function syncTopicsSubtabUI() {
    state.ui.pageSubtabs.topics = "definitions";
    if (topicsDefinitionsPane) {
      topicsDefinitionsPane.classList.add("active");
      topicsDefinitionsPane.hidden = false;
    }
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
    ensureTopicDefinitions();
    syncTopicsSubtabUI();
    const activeEl = document.activeElement;
    const editingInputs = [topicDefNameInput, topicDefDurationInput, topicDefPriorityInput, topicDefCommentsInput];
    const editorBusy = editingInputs.includes(activeEl);
    if (!editorBusy && !state.ui.topicsDefinitionsView.editingId) {
      resetTopicDefinitionEditor();
    }
  }

  function renderTopicDefinitionsList() {
    if (!topicsDefinitionsList) return;
    const defs = ensureTopicDefinitions();
    topicsDefinitionsList.innerHTML = "";
    if (!defs.length) {
      const empty = document.createElement("div");
      empty.className = "topics-empty";
      empty.textContent = "No topic definitions yet. Add one to use in Summary.";
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
    const defs = ensureTopicDefinitions();

    const statusParts = [];
    statusParts.push(defs.length ? "Definitions ready" : "No definitions yet");
    statusParts.push("Used by Summary");
    if (topicsStatusEl) topicsStatusEl.textContent = statusParts.join(" | ");

    if (topicsKpiCount) topicsKpiCount.textContent = String(defs.length);
    syncTopicsSubtabUI();
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

  // ==========================================================================
  // SUMMARY RENDERING + INSIGHTS
  // ==========================================================================

  function renderSummary() {
    const s = state.summary;
    const hasSummary = !!(
      s.executive_summary
      || (s.key_points && s.key_points.length)
      || (s.action_items && s.action_items.length)
      || (s.topic_breakdown && s.topic_breakdown.length)
      || (s.topic_key_points && s.topic_key_points.length)
      || (s.keyword_index && s.keyword_index.length)
      || (s.meeting_insights && Object.keys(s.meeting_insights).length)
    );
    const summaryChip = summaryKpiStatus ? summaryKpiStatus.closest(".ops-kpi-chip") : null;

    if (summaryKpiStatus) {
      summaryKpiStatus.textContent = s.pending ? "Generating…" : (s.error ? "Error" : (hasSummary ? "Ready" : "--"));
    }
    if (summaryChip) {
      summaryChip.classList.remove("is-ready", "is-pending", "is-error");
      if (s.pending) summaryChip.classList.add("is-pending");
      else if (s.error) summaryChip.classList.add("is-error");
      else if (hasSummary) summaryChip.classList.add("is-ready");
    }
    if (summaryPendingIndicator) summaryPendingIndicator.classList.toggle("hidden", !s.pending);
    if (summaryError) {
      summaryError.classList.toggle("hidden", !s.error);
      if (s.error) summaryError.textContent = `Error: ${s.error}`;
    }
    if (summaryEmpty) summaryEmpty.classList.toggle("hidden", hasSummary || s.pending || !!s.error);
    if (summaryBody) summaryBody.classList.toggle("hidden", !hasSummary);
    if (summaryExportMenuBtn) summaryExportMenuBtn.disabled = !hasSummary;

    if (!hasSummary) return;

    if (summaryExecutiveText) summaryExecutiveText.textContent = s.executive_summary || "";

    if (summaryKeyPointsList) {
      summaryKeyPointsList.innerHTML = "";
      (s.key_points || []).forEach((pt) => {
        const li = document.createElement("li");
        li.textContent = String(pt);
        summaryKeyPointsList.appendChild(li);
      });
    }

    if (summaryActionItemsList) {
      summaryActionItemsList.innerHTML = "";
      if ((s.action_items || []).length === 0) {
        const empty = document.createElement("div");
        empty.className = "summary-empty-state summary-empty-state-inline";
        empty.textContent = "No action items identified.";
        summaryActionItemsList.appendChild(empty);
      } else {
        (s.action_items || []).forEach((ai) => {
          const row = document.createElement("div");
          row.className = "action-item-row";
          const item = document.createElement("span");
          item.className = "ai-item";
          item.textContent = String(ai.item || "");
          const owner = document.createElement("span");
          owner.className = "ai-owner";
          owner.textContent = ai.owner ? `Owner: ${ai.owner}` : "";
          const due = document.createElement("span");
          due.className = "ai-due";
          due.textContent = ai.due_date ? `Due: ${ai.due_date}` : "";
          row.appendChild(item);
          row.appendChild(owner);
          row.appendChild(due);
          summaryActionItemsList.appendChild(row);
        });
      }
    }

    // Metadata row (meeting type chip + sentiment arc)
    if (summaryMetaRow) {
      const meta = s.metadata || {};
      const meetingType = String(meta.meeting_type || "").trim();
      const sentiment = String(meta.sentiment_arc || "").trim();
      const hasMeta = !!(meetingType || sentiment);
      summaryMetaRow.classList.toggle("hidden", !hasMeta);
      summaryMetaRow.innerHTML = "";
      if (meetingType) {
        const chip = document.createElement("span");
        chip.className = "summary-meta-chip";
        chip.textContent = meetingType;
        summaryMetaRow.appendChild(chip);
      }
      if (sentiment) {
        const text = document.createElement("span");
        text.className = "summary-meta-sentiment";
        text.textContent = sentiment;
        summaryMetaRow.appendChild(text);
      }
    }

    // Decisions made
    if (summaryDecisionsSection && summaryDecisionsList) {
      const decisions = s.decisions_made || [];
      summaryDecisionsSection.classList.toggle("hidden", decisions.length === 0);
      summaryDecisionsList.innerHTML = "";
      decisions.forEach((d) => {
        const li = document.createElement("li");
        li.textContent = String(d);
        summaryDecisionsList.appendChild(li);
      });
    }

    // Risks & blockers
    if (summaryRisksSection && summaryRisksList) {
      const risks = s.risks_and_blockers || [];
      summaryRisksSection.classList.toggle("hidden", risks.length === 0);
      summaryRisksList.innerHTML = "";
      risks.forEach((r) => {
        const li = document.createElement("li");
        li.className = "summary-risk-item";
        li.textContent = String(r);
        summaryRisksList.appendChild(li);
      });
    }

    // Key terms (collapsible — preserve open/closed state across re-renders)
    if (summaryTermsSection && summaryTermsList) {
      const terms = s.key_terms_defined || [];
      summaryTermsSection.classList.toggle("hidden", terms.length === 0);
      summaryTermsList.innerHTML = "";
      terms.forEach((t) => {
        const dt = document.createElement("dt");
        dt.className = "summary-term-name";
        dt.textContent = String(t.term || "");
        const dd = document.createElement("dd");
        dd.className = "summary-term-def";
        dd.textContent = String(t.definition || "");
        summaryTermsList.appendChild(dt);
        summaryTermsList.appendChild(dd);
      });
    }

    renderMeetingInsights();
    renderKeywordIndex();
    renderTopicCoverage();
  }

  function applyTranscriptFilterAndJump(keyword) {
    const query = String(keyword || "").trim();
    if (!query) return;
    state.filters.transcript = query;
    if (transcriptSearch) transcriptSearch.value = query;
    setActiveTab("transcriptTab");
    renderFinals(true);
    const norm = normalizeText(query);
    const target = filteredFinals().find((item) => {
      const blob = `${item.speaker_label || ""} ${item.en || ""} ${item.ar || ""}`;
      return normalizeText(blob).includes(norm);
    });
    if (target) jumpToTimelineKey(finalKey(target));
  }

  function renderMeetingInsights() {
    if (!summaryInsightsSection || !summaryInsightsBody) return;
    const insights = state.summary.meeting_insights || {};
    const balance = Array.isArray(insights.speaking_balance) ? insights.speaking_balance : [];
    const turn = (insights.turn_taking && typeof insights.turn_taking === "object")
      ? insights.turn_taking
      : {};
    const pace = Array.isArray(insights.pace) ? insights.pace : [];
    const health = (insights.health && typeof insights.health === "object") ? insights.health : {};

    const hasInsights = balance.length > 0 || pace.length > 0 || Object.keys(turn).length > 0;
    summaryInsightsSection.classList.toggle("hidden", !hasInsights);
    summaryInsightsBody.innerHTML = "";

    if (summaryHealthChip) {
      const score = Number(health.score_0_100);
      if (Number.isFinite(score) && score >= 0) {
        summaryHealthChip.textContent = `Health ${Math.round(score)}/100`;
        summaryHealthChip.classList.remove("hidden");
      } else {
        summaryHealthChip.classList.add("hidden");
      }
    }

    if (!hasInsights) return;

    const maxShare = Math.max(1, ...balance.map((row) => Number(row.share_pct || 0)));
    const balanceBlock = document.createElement("div");
    balanceBlock.className = "summary-insight-block";
    const balanceTitle = document.createElement("h4");
    balanceTitle.textContent = "Speaking Balance";
    balanceBlock.appendChild(balanceTitle);
    balance.forEach((row) => {
      const name = String(row.speaker || "Speaker");
      const share = Number(row.share_pct || 0);
      const words = Number(row.words || 0);
      const line = document.createElement("div");
      line.className = "summary-speaker-row";

      const label = document.createElement("span");
      label.className = "summary-speaker-label";
      label.textContent = `${name} (${share.toFixed(1)}%)`;

      const barWrap = document.createElement("div");
      barWrap.className = "summary-speaker-bar";
      const bar = document.createElement("div");
      bar.className = "summary-speaker-fill";
      bar.style.width = `${Math.max(6, Math.min(100, (share / maxShare) * 100)).toFixed(1)}%`;
      barWrap.appendChild(bar);

      const meta = document.createElement("span");
      meta.className = "summary-speaker-meta";
      meta.textContent = `${words} words`;

      line.appendChild(label);
      line.appendChild(barWrap);
      line.appendChild(meta);
      balanceBlock.appendChild(line);
    });
    summaryInsightsBody.appendChild(balanceBlock);

    const turnBlock = document.createElement("div");
    turnBlock.className = "summary-insight-block";
    const turnTitle = document.createElement("h4");
    turnTitle.textContent = "Turn Taking";
    turnBlock.appendChild(turnTitle);
    const turnRows = [
      `Turns: ${Number(turn.total_turns || 0)}`,
      `Avg words/turn: ${Number(turn.avg_words_per_turn || 0).toFixed(1)}`,
      `Speaker switches: ${Number(turn.speaker_switches || 0)} (${Number(turn.switch_rate_pct || 0).toFixed(1)}%)`,
      `Longest turn: ${Number(turn.longest_turn_words || 0)} words`,
    ];
    turnRows.forEach((text) => {
      const row = document.createElement("div");
      row.className = "summary-insight-line";
      row.textContent = text;
      turnBlock.appendChild(row);
    });
    summaryInsightsBody.appendChild(turnBlock);

    const paceBlock = document.createElement("div");
    paceBlock.className = "summary-insight-block";
    const paceTitle = document.createElement("h4");
    paceTitle.textContent = "Speaking Pace";
    paceBlock.appendChild(paceTitle);
    pace.forEach((row) => {
      const line = document.createElement("div");
      line.className = "summary-insight-line";
      line.textContent = `${row.speaker || "Speaker"}: ${Number(row.wpm || 0).toFixed(1)} WPM`;
      paceBlock.appendChild(line);
    });
    summaryInsightsBody.appendChild(paceBlock);

    const healthFlags = Array.isArray(health.flags) ? health.flags : [];
    const healthRecs = Array.isArray(health.recommendations) ? health.recommendations : [];
    if (healthFlags.length || healthRecs.length) {
      const healthBlock = document.createElement("div");
      healthBlock.className = "summary-insight-block";
      const healthTitle = document.createElement("h4");
      healthTitle.textContent = "Health Notes";
      healthBlock.appendChild(healthTitle);
      healthFlags.forEach((flag) => {
        const line = document.createElement("div");
        line.className = "summary-insight-line is-flag";
        line.textContent = `• ${String(flag)}`;
        healthBlock.appendChild(line);
      });
      healthRecs.forEach((tip) => {
        const line = document.createElement("div");
        line.className = "summary-insight-line";
        line.textContent = `→ ${String(tip)}`;
        healthBlock.appendChild(line);
      });
      summaryInsightsBody.appendChild(healthBlock);
    }
  }

  function renderKeywordIndex() {
    if (!summaryKeywordsSection || !summaryKeywordsList) return;
    const keywords = Array.isArray(state.summary.keyword_index) ? state.summary.keyword_index : [];
    const query = normalizeText(summaryKeywordSearch?.value || "").trim();
    const filtered = query
      ? keywords.filter((row) => normalizeText(row.keyword || "").includes(query))
      : keywords;
    summaryKeywordsSection.classList.toggle("hidden", keywords.length === 0);
    summaryKeywordsList.innerHTML = "";

    if (summaryKeywordsMeta) {
      if (keywords.length > 0) {
        summaryKeywordsMeta.textContent = `${keywords.length} keywords`;
        summaryKeywordsMeta.classList.remove("hidden");
      } else {
        summaryKeywordsMeta.classList.add("hidden");
      }
    }
    if (keywords.length === 0) return;

    if (filtered.length === 0) {
      const empty = document.createElement("div");
      empty.className = "summary-empty-state summary-empty-state-inline";
      empty.textContent = "No keywords match your filter.";
      summaryKeywordsList.appendChild(empty);
      return;
    }

    filtered.forEach((row) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn summary-keyword-chip";
      const keyword = String(row.keyword || "").trim();
      const occurrences = Number(row.occurrences || 0);
      const first = Number(row.first_ts || 0);
      const last = Number(row.last_ts || 0);
      const speakers = Array.isArray(row.speakers) ? row.speakers.join(", ") : "";
      btn.textContent = `${keyword} (${occurrences})`;
      const firstText = first > 0 ? formatTime(first) : "--";
      const lastText = last > 0 ? formatTime(last) : "--";
      btn.title = `First: ${firstText} | Last: ${lastText}${speakers ? ` | Speakers: ${speakers}` : ""}`;
      btn.addEventListener("click", () => applyTranscriptFilterAndJump(keyword));
      summaryKeywordsList.appendChild(btn);
    });
  }

  function buildContiguousRanges(sortedNums) {
    const ranges = [];
    if (!sortedNums.length) return ranges;
    let start = sortedNums[0];
    let prev = sortedNums[0];
    for (let i = 1; i < sortedNums.length; i += 1) {
      const cur = sortedNums[i];
      if (cur === prev + 1) {
        prev = cur;
        continue;
      }
      ranges.push({ start, end: prev });
      start = cur;
      prev = cur;
    }
    ranges.push({ start, end: prev });
    return ranges;
  }

  function buildSummaryUtteranceTimingMap() {
    const finals = Array.isArray(state.finals) ? state.finals : [];
    if (finals.length === 0) {
      return { byId: {}, maxId: 0, totalSec: 0, baselineTs: 0 };
    }

    const entries = finals
      .slice(-500)
      .map((f) => {
        const text = String(f.en || "").trim();
        if (!text) return null;
        const itemTs = toFiniteNumber(f.ts, 0);
        let startTs = toFiniteNumber(f.start_ts, itemTs);
        let endTs = toFiniteNumber(f.end_ts, itemTs || startTs);
        if (startTs <= 0 && itemTs > 0) startTs = itemTs;
        if (endTs < startTs) endTs = startTs;
        let durationSec = toFiniteNumber(f.duration_sec, endTs - startTs);
        if (durationSec < 0) durationSec = 0;
        return {
          ts: itemTs,
          start_ts: startTs,
          end_ts: endTs,
          duration_sec: durationSec,
        };
      })
      .filter(Boolean)
      .sort((a, b) => (a.start_ts - b.start_ts) || (a.ts - b.ts));

    if (entries.length === 0) {
      return { byId: {}, maxId: 0, totalSec: 0, baselineTs: 0 };
    }

    const baseline = toFiniteNumber(entries[0].start_ts || entries[0].ts, 0);
    let totalSec = 0;
    const byId = {};
    entries.forEach((row, idx) => {
      const utteranceNum = idx + 1;
      const utteranceId = `U${String(utteranceNum).padStart(4, "0")}`;
      const startSec = Math.max(0, toFiniteNumber(row.start_ts, 0) - baseline);
      const endFromDuration = startSec + Math.max(0, toFiniteNumber(row.duration_sec, 0));
      const endFromTs = Math.max(startSec, toFiniteNumber(row.end_ts, row.start_ts) - baseline);
      const endSec = Math.max(endFromDuration, endFromTs);
      totalSec = Math.max(totalSec, endSec);
      byId[utteranceId] = {
        num: utteranceNum,
        start_sec: startSec,
        end_sec: endSec,
        duration_sec: Math.max(0, endSec - startSec),
        start_ts: toFiniteNumber(row.start_ts, 0),
        end_ts: toFiniteNumber(row.end_ts, toFiniteNumber(row.start_ts, 0)),
      };
    });

    return { byId, maxId: entries.length, totalSec, baselineTs: baseline };
  }

  function buildTopicCoverageViewModel() {
    const breakdown = Array.isArray(state.summary.topic_breakdown) ? state.summary.topic_breakdown : [];
    const groups = Array.isArray(state.summary.topic_key_points) ? state.summary.topic_key_points : [];

    const breakdownMap = new Map();
    breakdown.forEach((row) => {
      const name = String(row?.name || "").trim();
      const key = normalizeTopicKey(name);
      if (!key) return;
      breakdownMap.set(key, row);
    });

    const topicsMap = new Map();

    groups.forEach((group) => {
      const name = String(group?.topic_name || "").trim();
      const key = normalizeTopicKey(name);
      if (!key) return;
      const b = breakdownMap.get(key);
      const idsRaw = Array.isArray(group.utterance_ids) ? group.utterance_ids : [];
      const nums = [];
      const uniqueNums = new Set();
      idsRaw.forEach((id) => {
        const n = parseUtteranceIdNumber(id);
        if (n === null || uniqueNums.has(n)) return;
        uniqueNums.add(n);
        nums.push(n);
      });
      nums.sort((a, b2) => a - b2);
      const actualFromGroup = toFiniteNumber(group.estimated_duration_minutes, NaN);
      const actualFromBreakdown = toFiniteNumber(b?.actual_min, 0);
      const actualMin = Number.isFinite(actualFromGroup) && actualFromGroup >= 0
        ? actualFromGroup
        : actualFromBreakdown;
      const plannedRaw = toOptionalNumber(b?.planned_min);
      const plannedMin = (plannedRaw !== null && plannedRaw > 0) ? plannedRaw : null;
      const status = String(
        b?.status
        || (actualMin > 0 ? "covered" : "not_started")
      ).trim().toLowerCase();
      const keyPoints = Array.isArray(group.key_points) ? group.key_points : [];
      topicsMap.set(key, {
        key,
        name: name || String(b?.name || ""),
        origin: String(group.origin || "").trim() || "Inferred",
        utterance_nums: nums,
        utterance_ids: nums.map((n) => `U${String(n).padStart(4, "0")}`),
        key_points: keyPoints.map((pt) => String(pt || "").trim()).filter(Boolean),
        actual_min: Math.max(0, actualMin),
        planned_min: plannedMin,
        status,
        color: topicColorByName(name || String(b?.name || "")),
      });
    });

    breakdown.forEach((row) => {
      const name = String(row?.name || "").trim();
      const key = normalizeTopicKey(name);
      if (!key || topicsMap.has(key)) return;
      const plannedRaw = toOptionalNumber(row?.planned_min);
      const plannedMin = (plannedRaw !== null && plannedRaw > 0) ? plannedRaw : null;
      topicsMap.set(key, {
        key,
        name,
        origin: "Agenda",
        utterance_nums: [],
        utterance_ids: [],
        key_points: [],
        actual_min: Math.max(0, toFiniteNumber(row?.actual_min, 0)),
        planned_min: plannedMin,
        status: String(row?.status || "not_started").trim().toLowerCase(),
        color: topicColorByName(name),
      });
    });

    const topics = Array.from(topicsMap.values());
    const timingMap = buildSummaryUtteranceTimingMap();
    const maxIdFromTopics = topics.reduce((maxSoFar, t) => {
      if (!t.utterance_nums.length) return maxSoFar;
      return Math.max(maxSoFar, t.utterance_nums[t.utterance_nums.length - 1]);
    }, 0);
    const useRealTiming = (
      toFiniteNumber(timingMap.maxId, 0) > 0
      && maxIdFromTopics > 0
      && Math.abs(toFiniteNumber(timingMap.maxId, 0) - maxIdFromTopics) <= 2
    );
    const totalActualMin = topics.reduce((sum, t) => sum + Math.max(0, toFiniteNumber(t.actual_min, 0)), 0);
    const fallbackTotalSec = Math.max(
      60,
      useRealTiming ? toFiniteNumber(timingMap.totalSec, 0) : 0,
      totalActualMin * 60
    );
    const fallbackDenom = Math.max(
      1,
      useRealTiming ? toFiniteNumber(timingMap.maxId, 0) : 0,
      maxIdFromTopics
    );

    topics.forEach((topic) => {
      const ranges = buildContiguousRanges(topic.utterance_nums);
      const segments = ranges.map((range) => {
        const startId = `U${String(range.start).padStart(4, "0")}`;
        const endId = `U${String(range.end).padStart(4, "0")}`;
        const startTiming = timingMap.byId[startId];
        const endTiming = timingMap.byId[endId];
        let startSec = null;
        let endSec = null;
        let startTs = null;
        let endTs = null;
        if (useRealTiming && startTiming && endTiming) {
          startSec = toFiniteNumber(startTiming.start_sec, 0);
          endSec = Math.max(startSec + 0.6, toFiniteNumber(endTiming.end_sec, startSec));
          const startTsRaw = toFiniteNumber(startTiming.start_ts, 0);
          const endTsRaw = toFiniteNumber(endTiming.end_ts, startTsRaw);
          if (startTsRaw > 0) {
            startTs = startTsRaw;
            endTs = Math.max(startTsRaw + (endSec - startSec), endTsRaw);
          }
        } else {
          startSec = ((range.start - 1) / fallbackDenom) * fallbackTotalSec;
          endSec = Math.max(startSec + 0.6, (range.end / fallbackDenom) * fallbackTotalSec);
        }
        return {
          start_sec: startSec,
          end_sec: endSec,
          start_ts: startTs,
          end_ts: endTs,
        };
      });
      const firstSeg = segments[0] || null;
      const lastSeg = segments[segments.length - 1] || null;
      topic.segments = segments;
      topic.first_sec = firstSeg ? firstSeg.start_sec : null;
      topic.last_sec = lastSeg ? lastSeg.end_sec : null;
      topic.first_ts = firstSeg ? firstSeg.start_ts : null;
      topic.last_ts = lastSeg ? lastSeg.end_ts : null;
    });

    // Improve visual differentiation: assign distinct colors by journey order.
    const colorOrder = topics
      .slice()
      .sort((a, b) => {
        const aStart = a.first_sec === null ? Number.POSITIVE_INFINITY : a.first_sec;
        const bStart = b.first_sec === null ? Number.POSITIVE_INFINITY : b.first_sec;
        if (aStart !== bStart) return aStart - bStart;
        return String(a.name || "").localeCompare(String(b.name || ""));
      });
    colorOrder.forEach((topic, idx) => {
      if (idx < TOPIC_COLORS.length) {
        topic.color = TOPIC_COLORS[idx];
      } else {
        const hue = (idx * 43) % 360;
        topic.color = `hsl(${hue} 72% 64%)`;
      }
    });

    const timelineTotalSec = Math.max(
      fallbackTotalSec,
      ...topics.flatMap((t) => t.segments.map((seg) => seg.end_sec))
    );
    const timelineStartTs = useRealTiming ? toFiniteNumber(timingMap.baselineTs, 0) : 0;
    const coveredTopics = topics.filter((t) => t.actual_min > 0);
    const plannedTopics = topics.filter((t) => t.planned_min !== null);
    const plannedCovered = plannedTopics.filter((t) => t.actual_min > 0);
    const dominantTopic = coveredTopics
      .slice()
      .sort((a, b) => b.actual_min - a.actual_min)[0] || null;
    const journeyTopics = coveredTopics
      .filter((t) => t.segments.length > 0)
      .slice()
      .sort((a, b) => {
        const aStart = a.first_sec === null ? Number.POSITIVE_INFINITY : a.first_sec;
        const bStart = b.first_sec === null ? Number.POSITIVE_INFINITY : b.first_sec;
        if (aStart !== bStart) return aStart - bStart;
        return b.actual_min - a.actual_min;
      });

    return {
      breakdown,
      topics,
      coveredTopics,
      journeyTopics,
      totalActualMin,
      plannedCount: plannedTopics.length,
      plannedCoveredCount: plannedCovered.length,
      inferredCount: topics.filter((t) => t.planned_min === null).length,
      totalCount: topics.length,
      dominantTopic,
      timelineTotalSec,
      timelineStartTs,
      hasRealTiming: useRealTiming,
    };
  }

  function renderTopicCoverageKpis(vm) {
    if (!summaryTopicKpis) return;
    summaryTopicKpis.innerHTML = "";

    const hasPlanned = vm.plannedCount > 0;
    const coverageCard = hasPlanned
      ? { label: "Planned Topics Covered", value: `${vm.plannedCoveredCount}/${vm.plannedCount}` }
      : { label: "Inferred Topics", value: `${vm.coveredTopics.length} active` };
    const planningCard = hasPlanned
      ? { label: "Total Topics Seen", value: String(vm.totalCount) }
      : { label: "Agenda Topics", value: "None" };

    const cards = [
      coverageCard,
      planningCard,
      { label: "Total Topic Time", value: formatMinutesShort(vm.totalActualMin) },
      { label: "Meeting Span", value: formatMinutesShort(vm.timelineTotalSec / 60) },
      {
        label: "Dominant Topic",
        value: vm.dominantTopic ? clipText(vm.dominantTopic.name, 26) : "--",
      },
    ];

    cards.forEach((card) => {
      const wrap = document.createElement("div");
      wrap.className = "summary-topic-kpi";
      const label = document.createElement("div");
      label.className = "summary-topic-kpi-label";
      label.textContent = card.label;
      const value = document.createElement("div");
      value.className = "summary-topic-kpi-value";
      value.textContent = card.value;
      value.title = card.value;
      wrap.appendChild(label);
      wrap.appendChild(value);
      summaryTopicKpis.appendChild(wrap);
    });
  }

  function renderTopicJourney(vm) {
    if (!summaryTopicJourneyWrap || !summaryTopicJourney || !summaryTopicJourneyAxis) return;
    summaryTopicJourney.innerHTML = "";
    summaryTopicJourneyAxis.innerHTML = "";

    if (vm.journeyTopics.length === 0) {
      summaryTopicJourneyWrap.classList.add("hidden");
      if (summaryTopicJourneyMeta) summaryTopicJourneyMeta.classList.add("hidden");
      return;
    }
    summaryTopicJourneyWrap.classList.remove("hidden");

    if (summaryTopicJourneyMeta) {
      summaryTopicJourneyMeta.textContent = vm.hasRealTiming
        ? "Timing from transcript timestamps"
        : "Timing inferred from utterance order";
      summaryTopicJourneyMeta.classList.remove("hidden");
    }

    const axisRow = document.createElement("div");
    axisRow.className = "summary-topic-axis-row";
    const axisLabelSpacer = document.createElement("div");
    axisLabelSpacer.className = "summary-topic-axis-spacer";
    const axisTrack = document.createElement("div");
    axisTrack.className = "summary-topic-axis-track";
    const axisMetaSpacer = document.createElement("div");
    axisMetaSpacer.className = "summary-topic-axis-spacer";

    for (let i = 0; i <= 4; i += 1) {
      const tick = document.createElement("span");
      tick.className = "summary-topic-axis-tick";
      if (i === 0) tick.classList.add("start");
      if (i === 4) tick.classList.add("end");
      const sec = (vm.timelineTotalSec * i) / 4;
      const tickTs = vm.hasRealTiming ? (toFiniteNumber(vm.timelineStartTs, 0) + sec) : null;
      tick.textContent = formatTimelinePoint(vm, sec, tickTs);
      tick.style.left = `${(i / 4) * 100}%`;
      axisTrack.appendChild(tick);
    }

    axisRow.appendChild(axisLabelSpacer);
    axisRow.appendChild(axisTrack);
    axisRow.appendChild(axisMetaSpacer);
    summaryTopicJourneyAxis.appendChild(axisRow);

    vm.journeyTopics.forEach((topic) => {
      const row = document.createElement("div");
      row.className = "summary-topic-journey-row";

      const label = document.createElement("div");
      label.className = "summary-topic-journey-label";
      label.textContent = topic.name;
      label.title = topic.name;

      const track = document.createElement("div");
      track.className = "summary-topic-journey-track";

      topic.segments.forEach((seg) => {
        const segment = document.createElement("div");
        segment.className = "summary-topic-journey-segment";
        const left = Math.max(0, Math.min(100, (seg.start_sec / vm.timelineTotalSec) * 100));
        const width = Math.max(1, Math.min(100 - left, ((seg.end_sec - seg.start_sec) / vm.timelineTotalSec) * 100));
        segment.style.left = `${left.toFixed(2)}%`;
        segment.style.width = `${width.toFixed(2)}%`;
        segment.style.background = topic.color;
        segment.title = `${topic.name} (${formatTimelinePoint(vm, seg.start_sec, seg.start_ts)} - ${formatTimelinePoint(vm, seg.end_sec, seg.end_ts)})`;
        track.appendChild(segment);
      });

      const meta = document.createElement("div");
      meta.className = "summary-topic-journey-meta";
      if (topic.first_sec !== null && topic.last_sec !== null) {
        meta.textContent = `${formatMinutesShort(topic.actual_min)} • ${formatTimelinePoint(vm, topic.first_sec, topic.first_ts)}-${formatTimelinePoint(vm, topic.last_sec, topic.last_ts)}`;
      } else {
        meta.textContent = formatMinutesShort(topic.actual_min);
      }

      row.appendChild(label);
      row.appendChild(track);
      row.appendChild(meta);
      summaryTopicJourney.appendChild(row);
    });
  }

  function renderTopicDonut(vm) {
    if (!summaryTopicDonutWrap || !summaryTopicDonut || !summaryTopicDonutCenter || !summaryTopicDonutLegend) return;
    summaryTopicDonutLegend.innerHTML = "";
    summaryTopicDonutCenter.innerHTML = "";

    const slices = vm.coveredTopics
      .slice()
      .sort((a, b) => b.actual_min - a.actual_min);
    const total = vm.totalActualMin;
    if (!slices.length || total <= 0) {
      summaryTopicDonutWrap.classList.add("hidden");
      summaryTopicDonut.style.background = "none";
      return;
    }
    summaryTopicDonutWrap.classList.remove("hidden");

    const maxSlices = 6;
    const shown = slices.slice(0, maxSlices);
    const rest = slices.slice(maxSlices);
    if (rest.length) {
      const restTotal = rest.reduce((sum, t) => sum + t.actual_min, 0);
      shown.push({
        name: "Other Topics",
        actual_min: restTotal,
        color: "#7B849A",
      });
    }

    let cursor = 0;
    const stops = shown.map((slice) => {
      const pct = (slice.actual_min / total) * 100;
      const start = cursor;
      cursor += pct;
      return `${slice.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
    });
    summaryTopicDonut.style.background = `conic-gradient(${stops.join(", ")})`;

    const totalEl = document.createElement("div");
    totalEl.className = "summary-topic-donut-total";
    totalEl.textContent = formatMinutesShort(total);
    const captionEl = document.createElement("div");
    captionEl.className = "summary-topic-donut-caption";
    captionEl.textContent = `${vm.coveredTopics.length} active topics`;
    summaryTopicDonutCenter.appendChild(totalEl);
    summaryTopicDonutCenter.appendChild(captionEl);

    shown.forEach((slice) => {
      const row = document.createElement("div");
      row.className = "summary-topic-donut-item";
      const dot = document.createElement("span");
      dot.className = "summary-topic-donut-dot";
      dot.style.background = slice.color;
      const label = document.createElement("span");
      label.className = "summary-topic-donut-label";
      label.textContent = slice.name;
      label.title = slice.name;
      const value = document.createElement("span");
      value.className = "summary-topic-donut-value";
      value.textContent = `${((slice.actual_min / total) * 100).toFixed(1)}% • ${formatMinutesShort(slice.actual_min)}`;
      row.appendChild(dot);
      row.appendChild(label);
      row.appendChild(value);
      summaryTopicDonutLegend.appendChild(row);
    });
  }

  function renderTopicBriefs(vm, options = {}) {
    if (!summaryTopicGroupsWrap || !summaryTopicGroups) return;
    summaryTopicGroups.innerHTML = "";
    const hasPlannedAgenda = !!options.hasPlannedAgenda;

    const cards = vm.coveredTopics
      .slice()
      .sort((a, b) => {
        const aStart = a.first_sec === null ? Number.POSITIVE_INFINITY : a.first_sec;
        const bStart = b.first_sec === null ? Number.POSITIVE_INFINITY : b.first_sec;
        if (aStart !== bStart) return aStart - bStart;
        return b.actual_min - a.actual_min;
      });

    if (cards.length === 0) {
      summaryTopicGroupsWrap.classList.add("hidden");
      return;
    }
    summaryTopicGroupsWrap.classList.remove("hidden");

    cards.forEach((topic) => {
      const card = document.createElement("article");
      card.className = "summary-topic-group-card";
      card.style.borderLeft = `3px solid ${topic.color}`;

      const head = document.createElement("div");
      head.className = "summary-topic-group-head";
      const name = document.createElement("div");
      name.className = "summary-topic-group-name";
      name.textContent = topic.name;
      name.title = topic.name;

      const share = vm.totalActualMin > 0 ? (topic.actual_min / vm.totalActualMin) * 100 : 0;
      const meta = document.createElement("div");
      meta.className = "summary-topic-group-meta";
      meta.textContent = `${formatMinutesShort(topic.actual_min)} • ${share.toFixed(1)}%`;
      head.appendChild(name);
      head.appendChild(meta);
      card.appendChild(head);

      const windowLine = document.createElement("div");
      windowLine.className = "summary-topic-group-meta";
      const originLabel = hasPlannedAgenda ? topic.origin : "Inferred";
      if (topic.first_sec !== null && topic.last_sec !== null) {
        windowLine.textContent = `Window ${formatTimelinePoint(vm, topic.first_sec, topic.first_ts)} - ${formatTimelinePoint(vm, topic.last_sec, topic.last_ts)} • ${originLabel}`;
      } else {
        windowLine.textContent = `${originLabel} • No utterance map`;
      }
      card.appendChild(windowLine);

      if (topic.key_points.length === 0) {
        const empty = document.createElement("div");
        empty.className = "summary-topic-group-empty";
        empty.textContent = "No specific key points were grouped under this topic.";
        card.appendChild(empty);
      } else {
        const list = document.createElement("ul");
        list.className = "summary-topic-group-points";
        topic.key_points.slice(0, 4).forEach((point) => {
          const li = document.createElement("li");
          li.textContent = point;
          list.appendChild(li);
        });
        card.appendChild(list);
      }
      summaryTopicGroups.appendChild(card);
    });
  }

  function renderAgendaVsActualBars(breakdown) {
    if (!summaryTopicTimeline) return;
    summaryTopicTimeline.innerHTML = "";
    if (breakdown.length === 0) return;

    const maxVal = Math.max(
      1,
      ...breakdown.map((t) => {
        const planned = toOptionalNumber(t.planned_min);
        return Math.max(
          toFiniteNumber(t.actual_min, 0),
          planned !== null && planned > 0 ? planned : 0
        );
      })
    );

    breakdown.forEach((t) => {
      const actualMin = Math.max(0, toFiniteNumber(t.actual_min, 0));
      const plannedRaw = toOptionalNumber(t.planned_min);
      const plannedMin = (plannedRaw !== null && plannedRaw > 0) ? plannedRaw : null;
      const overUnderRaw = toOptionalNumber(t.over_under_min);
      const overUnder = overUnderRaw !== null ? overUnderRaw : null;
      const status = String(t.status || "not_started");

      let barClass = "status-" + status;
      if (status === "covered" && overUnder !== null && overUnder > 0) {
        barClass = "status-over";
      }

      const row = document.createElement("div");
      row.className = "topic-row";

      const label = document.createElement("div");
      label.className = "topic-row-label";
      label.textContent = String(t.name || "");
      label.title = String(t.name || "");

      const barWrap = document.createElement("div");
      barWrap.className = "topic-row-bar-wrap";

      const bar = document.createElement("div");
      bar.className = `topic-row-bar ${barClass}`;
      bar.style.width = `${Math.max(0, Math.min(100, (actualMin / maxVal) * 100)).toFixed(1)}%`;
      barWrap.appendChild(bar);

      if (plannedMin !== null) {
        const marker = document.createElement("div");
        marker.className = "topic-planned-marker";
        marker.style.left = `${Math.max(0, Math.min(100, (plannedMin / maxVal) * 100)).toFixed(1)}%`;
        marker.title = `Planned: ${formatMinutesShort(plannedMin)}`;
        barWrap.appendChild(marker);
      }

      const stats = document.createElement("div");
      stats.className = "topic-row-stats";
      if (plannedMin !== null) {
        const overEl = document.createElement("span");
        overEl.textContent = `${formatMinutesShort(actualMin)} / ${formatMinutesShort(plannedMin)}`;
        if (overUnder !== null && overUnder !== 0) {
          overEl.className = overUnder > 0 ? "stat-over" : "";
          stats.appendChild(overEl);
          const extra = document.createElement("span");
          extra.className = overUnder > 0 ? "stat-over" : "";
          extra.textContent = ` (${formatMinutesDelta(overUnder)})`;
          stats.appendChild(extra);
        } else {
          stats.appendChild(overEl);
        }
      } else {
        stats.textContent = formatMinutesShort(actualMin);
      }

      row.appendChild(label);
      row.appendChild(barWrap);
      row.appendChild(stats);
      summaryTopicTimeline.appendChild(row);
    });
  }

  function renderTopicCoverage() {
    if (!summaryTopicSection || !summaryTopicTimeline || !summaryTopicPlaceholder) return;
    const hasBreakdown = Array.isArray(state.summary.topic_breakdown) && state.summary.topic_breakdown.length > 0;
    const hasTopicGroups = Array.isArray(state.summary.topic_key_points) && state.summary.topic_key_points.length > 0;
    const adherence = state.summary.agenda_adherence_pct;

    if (!hasBreakdown && !hasTopicGroups) {
      summaryTopicTimeline.innerHTML = "";
      if (summaryTopicKpis) summaryTopicKpis.innerHTML = "";
      if (summaryTopicJourney) summaryTopicJourney.innerHTML = "";
      if (summaryTopicJourneyAxis) summaryTopicJourneyAxis.innerHTML = "";
      if (summaryTopicDonut) summaryTopicDonut.style.background = "none";
      if (summaryTopicDonutCenter) summaryTopicDonutCenter.innerHTML = "";
      if (summaryTopicDonutLegend) summaryTopicDonutLegend.innerHTML = "";
      if (summaryTopicGroups) summaryTopicGroups.innerHTML = "";
      if (summaryTopicJourneyWrap) summaryTopicJourneyWrap.classList.add("hidden");
      if (summaryTopicDonutWrap) summaryTopicDonutWrap.classList.add("hidden");
      if (summaryTopicGroupsWrap) summaryTopicGroupsWrap.classList.add("hidden");
      if (summaryAgendaActualHead) summaryAgendaActualHead.classList.remove("hidden");
      if (summaryAgendaActualWrap) summaryAgendaActualWrap.classList.remove("hidden");
      summaryTopicPlaceholder.textContent = "No topic definitions are defined for this summary.";
      summaryTopicPlaceholder.classList.remove("hidden");
      if (summaryAdherenceChip) summaryAdherenceChip.classList.add("hidden");
      return;
    }

    if (summaryAdherenceChip) {
      if (adherence !== null && adherence !== undefined) {
        summaryAdherenceChip.textContent = `Adherence ${adherence.toFixed(1)}%`;
        summaryAdherenceChip.classList.remove("hidden");
      } else {
        summaryAdherenceChip.classList.add("hidden");
      }
    }

    const vm = buildTopicCoverageViewModel();
    renderTopicCoverageKpis(vm);
    renderTopicJourney(vm);
    renderTopicDonut(vm);
    
    const hasPlannedAgenda = vm.breakdown.some((row) => {
      const planned = toOptionalNumber(row?.planned_min);
      return planned !== null && planned > 0;
    });
    renderTopicBriefs(vm, { hasPlannedAgenda });

    if (!hasPlannedAgenda) {
      if (summaryAgendaActualHead) summaryAgendaActualHead.classList.add("hidden");
      if (summaryAgendaActualWrap) summaryAgendaActualWrap.classList.add("hidden");
      summaryTopicTimeline.innerHTML = "";
      summaryTopicPlaceholder.textContent = "No agenda topics are defined for this summary. Inferred topic coverage is shown above.";
      summaryTopicPlaceholder.classList.add("hidden");
    } else {
      if (summaryAgendaActualHead) summaryAgendaActualHead.classList.remove("hidden");
      if (summaryAgendaActualWrap) summaryAgendaActualWrap.classList.remove("hidden");
      renderAgendaVsActualBars(vm.breakdown);
      summaryTopicPlaceholder.textContent = "No topic definitions are defined for this summary.";
      summaryTopicPlaceholder.classList.add("hidden");
    }
  }

  function buildSummaryTopicCoverageExport() {
    const vm = buildTopicCoverageViewModel();
    const modeRaw = String(state.currentConfig?.summary_topic_duration_mode || "coverage_with_gaps").trim();
    const durationMode = ["coverage_with_gaps", "speech_only"].includes(modeRaw)
      ? modeRaw
      : "coverage_with_gaps";
    const gapThresholdSec = clampNumber(
      state.currentConfig?.summary_topic_gap_threshold_sec,
      0,
      300,
      30
    );
    const journey = vm.journeyTopics.map((topic) => {
      const sharePct = vm.totalActualMin > 0 ? (topic.actual_min / vm.totalActualMin) * 100 : 0;
      return {
        name: topic.name,
        origin: topic.origin,
        status: topic.status,
        color: topic.color,
        actual_min: toFiniteNumber(topic.actual_min, 0),
        actual_text: formatMinutesShort(topic.actual_min),
        share_pct: Number(sharePct.toFixed(1)),
        utterance_ids: Array.isArray(topic.utterance_ids) ? topic.utterance_ids : [],
        key_points: Array.isArray(topic.key_points) ? topic.key_points : [],
        first_sec: topic.first_sec,
        last_sec: topic.last_sec,
        first_clock: topic.first_sec !== null ? formatTimelinePoint(vm, topic.first_sec, topic.first_ts) : null,
        last_clock: topic.last_sec !== null ? formatTimelinePoint(vm, topic.last_sec, topic.last_ts) : null,
        segments: Array.isArray(topic.segments)
          ? topic.segments.map((seg) => ({
            start_sec: seg.start_sec,
            end_sec: seg.end_sec,
            start_clock: formatTimelinePoint(vm, seg.start_sec, seg.start_ts),
            end_clock: formatTimelinePoint(vm, seg.end_sec, seg.end_ts),
          }))
          : [],
      };
    });
    return {
      duration_mode: durationMode,
      gap_threshold_sec: gapThresholdSec,
      has_real_timing: !!vm.hasRealTiming,
      timeline_start_ts: vm.hasRealTiming ? toFiniteNumber(vm.timelineStartTs, 0) : null,
      timeline_start_clock: vm.hasRealTiming ? formatClockTime(vm.timelineStartTs) : null,
      meeting_span_sec: toFiniteNumber(vm.timelineTotalSec, 0),
      meeting_span_text: formatMinutesShort(vm.timelineTotalSec / 60),
      total_topic_time_min: toFiniteNumber(vm.totalActualMin, 0),
      total_topic_time_text: formatMinutesShort(vm.totalActualMin),
      dominant_topic: vm.dominantTopic ? vm.dominantTopic.name : null,
      total_topics_seen: vm.totalCount,
      active_topics: vm.coveredTopics.length,
      planned_topics_count: vm.plannedCount,
      planned_topics_covered: vm.plannedCoveredCount,
      journey,
    };
  }

  function exportSummaryJson() {
    const s = state.summary;
    const topicCoverage = buildSummaryTopicCoverageExport();
    const blob = new Blob([JSON.stringify({
      metadata: s.metadata,
      executive_summary: s.executive_summary,
      key_points: s.key_points,
      action_items: s.action_items,
      topic_key_points: s.topic_key_points,
      entities: s.entities,
      decisions_made: s.decisions_made,
      risks_and_blockers: s.risks_and_blockers,
      key_terms_defined: s.key_terms_defined,
      topic_breakdown: s.topic_breakdown,
      agenda_adherence_pct: s.agenda_adherence_pct,
      meeting_insights: s.meeting_insights,
      keyword_index: s.keyword_index,
      topic_coverage: topicCoverage,
      generated_ts: s.generated_ts,
    }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "summary.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportSummaryTxt() {
    const s = state.summary;
    const topicCoverage = buildSummaryTopicCoverageExport();
    const lines = [];
    if (s.metadata && (s.metadata.meeting_type || s.metadata.sentiment_arc)) {
      lines.push("SESSION METADATA", "=".repeat(40));
      if (s.metadata.meeting_type) lines.push(`Meeting Type: ${s.metadata.meeting_type}`);
      if (s.metadata.sentiment_arc) lines.push(`Sentiment Arc: ${s.metadata.sentiment_arc}`);
      lines.push("");
    }
    if (s.executive_summary) {
      lines.push("EXECUTIVE SUMMARY", "=".repeat(40), s.executive_summary, "");
    }
    if (s.key_points && s.key_points.length) {
      lines.push("KEY POINTS", "=".repeat(40));
      s.key_points.forEach((pt, i) => lines.push(`${i + 1}. ${pt}`));
      lines.push("");
    }
    if (s.action_items && s.action_items.length) {
      lines.push("ACTION ITEMS", "=".repeat(40));
      s.action_items.forEach((ai, i) => {
        let line = `${i + 1}. ${ai.item || ""}`;
        if (ai.owner) line += ` [Owner: ${ai.owner}]`;
        if (ai.due_date) line += ` [Due: ${ai.due_date}]`;
        lines.push(line);
      });
      lines.push("");
    }
    if (s.decisions_made && s.decisions_made.length) {
      lines.push("DECISIONS MADE", "=".repeat(40));
      s.decisions_made.forEach((d, i) => lines.push(`${i + 1}. ${d}`));
      lines.push("");
    }
    if (s.risks_and_blockers && s.risks_and_blockers.length) {
      lines.push("RISKS & BLOCKERS", "=".repeat(40));
      s.risks_and_blockers.forEach((r, i) => lines.push(`${i + 1}. ${r}`));
      lines.push("");
    }
    if (s.key_terms_defined && s.key_terms_defined.length) {
      lines.push("KEY TERMS DEFINED", "=".repeat(40));
      s.key_terms_defined.forEach((t) => lines.push(`${t.term || ""}: ${t.definition || ""}`));
      lines.push("");
    }
    if (s.entities && s.entities.length) {
      lines.push("ENTITIES", "=".repeat(40));
      s.entities.forEach((e) => {
        const type = String(e.type || "").trim();
        const text = String(e.text || "").trim();
        const mentions = e.mentions !== null && e.mentions !== undefined ? ` (${e.mentions})` : "";
        if (text) lines.push(`- ${type ? `[${type}] ` : ""}${text}${mentions}`);
      });
      lines.push("");
    }
    if ((s.topic_breakdown && s.topic_breakdown.length) || topicCoverage.journey.length) {
      lines.push("TOPIC COVERAGE", "=".repeat(40));
      if (s.agenda_adherence_pct !== null && s.agenda_adherence_pct !== undefined) {
        lines.push(`Agenda Adherence: ${s.agenda_adherence_pct.toFixed(1)}%`);
      }
      lines.push(`Duration mode: ${topicCoverage.duration_mode}`);
      lines.push(`Gap threshold: ${topicCoverage.gap_threshold_sec}s`);
      lines.push(`Total topic time: ${topicCoverage.total_topic_time_text}`);
      lines.push(`Meeting span: ${topicCoverage.meeting_span_text}`);
      if (topicCoverage.dominant_topic) {
        lines.push(`Dominant topic: ${topicCoverage.dominant_topic}`);
      }
      (Array.isArray(s.topic_breakdown) ? s.topic_breakdown : []).forEach((t) => {
        const actualText = formatMinutesShort(toFiniteNumber(t.actual_min, 0));
        const planned = t.planned_min !== null ? ` / ${formatMinutesShort(toFiniteNumber(t.planned_min, 0))} planned` : "";
        const delta = (t.over_under_min !== null && t.over_under_min !== 0)
          ? ` (${formatMinutesDelta(toFiniteNumber(t.over_under_min, 0))})`
          : "";
        lines.push(`- ${t.name}: ${t.status}, ${actualText} actual${planned}${delta}`);
      });
      if (topicCoverage.journey.length) {
        lines.push("");
        lines.push("Topic journey:");
        topicCoverage.journey.forEach((row) => {
          const windowText = row.first_clock && row.last_clock
            ? `${row.first_clock} - ${row.last_clock}`
            : "--";
          lines.push(
            `- ${row.name}: ${row.actual_text}, ${row.share_pct.toFixed(1)}%, window ${windowText}, segments ${row.segments.length}`
          );
        });
      }
      lines.push("");
    }
    if (topicCoverage.journey.length) {
      lines.push("TOPIC BRIEFS", "=".repeat(40));
      topicCoverage.journey.forEach((row) => {
        lines.push(`- ${row.name} (${row.actual_text})`);
        const points = Array.isArray(row.key_points) ? row.key_points : [];
        if (!points.length) {
          lines.push("  • No grouped key points");
        } else {
          points.slice(0, 6).forEach((pt) => lines.push(`  • ${pt}`));
        }
      });
      lines.push("");
    }
    if (s.meeting_insights && Object.keys(s.meeting_insights).length) {
      const mi = s.meeting_insights;
      const turn = mi.turn_taking || {};
      const health = mi.health || {};
      lines.push("MEETING INSIGHTS", "=".repeat(40));
      lines.push(
        `Turns: ${Number(turn.total_turns || 0)} | Switches: ${Number(turn.speaker_switches || 0)} (${Number(turn.switch_rate_pct || 0).toFixed(1)}%)`
      );
      lines.push(
        `Avg words/turn: ${Number(turn.avg_words_per_turn || 0).toFixed(1)} | Longest turn: ${Number(turn.longest_turn_words || 0)} words`
      );
      if (Number.isFinite(Number(health.score_0_100))) {
        lines.push(`Health score: ${Math.round(Number(health.score_0_100))}/100`);
      }
      const balance = Array.isArray(mi.speaking_balance) ? mi.speaking_balance : [];
      if (balance.length) {
        lines.push("Speaking balance:");
        balance.forEach((row) => {
          lines.push(
            `- ${row.speaker || "Speaker"}: ${Number(row.share_pct || 0).toFixed(1)}% | ${Number(row.words || 0)} words | ${Number(row.turns || 0)} turns`
          );
        });
      }
      lines.push("");
    }
    if (s.keyword_index && s.keyword_index.length) {
      lines.push("KEYWORD INDEX", "=".repeat(40));
      s.keyword_index.forEach((row) => {
        lines.push(`- ${row.keyword || ""}: ${Number(row.occurrences || 0)} hits`);
      });
      lines.push("");
    }
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "summary.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  // ==========================================================================
  // SETTINGS + CONFIG SYNC
  // ==========================================================================

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
    if (cfgTranslationEnabled) cfgTranslationEnabled.checked = !!(config.translation_enabled ?? true);
    if (cfgSummaryEnabled) cfgSummaryEnabled.checked = !!(config.summary_enabled ?? true);
    if (cfgSummaryTopicDurationMode) {
      const mode = String(config.summary_topic_duration_mode || "coverage_with_gaps").trim();
      cfgSummaryTopicDurationMode.value = ["coverage_with_gaps", "speech_only"].includes(mode)
        ? mode
        : "coverage_with_gaps";
    }
    if (cfgSummaryTopicGapThresholdSec) {
      cfgSummaryTopicGapThresholdSec.value = String(
        clampNumber(config.summary_topic_gap_threshold_sec, 0, 300, 30)
      );
    }
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
    applyTranslationVisibility();
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
        ? "Enable Auto Coach to edit this."
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
        state.ui.pageSubtabs.topics = "definitions";
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
    const menus = [transcriptExportMenu, summaryExportMenu];
    menus.forEach((menu) => {
      if (!menu) return;
      menu.classList.add("hidden");
    });
    if (transcriptExportMenuBtn) transcriptExportMenuBtn.setAttribute("aria-expanded", "false");
    if (summaryExportMenuBtn) summaryExportMenuBtn.setAttribute("aria-expanded", "false");
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
    const captureMode = cfgCaptureMode?.value === "dual" ? "Dual Input" : "Single Input";
    rows.push(`Microphone layout: ${captureMode}`);
    rows.push(`Live coach: ${cfgCoachEnabled?.checked ? "enabled" : "disabled"}`);
    rows.push(`Arabic translation: ${cfgTranslationEnabled?.checked !== false ? "enabled" : "off"}`);
    rows.push(`Auto summary: ${cfgSummaryEnabled?.checked !== false ? "enabled" : "off"}`);
    if (cfgSummaryTopicDurationMode) {
      const mode = String(cfgSummaryTopicDurationMode.value || "coverage_with_gaps");
      const modeLabel = mode === "speech_only" ? "Speech Only" : "Coverage with Gaps";
      rows.push(`Topic timing method: ${modeLabel}`);
    }
    if (cfgSummaryTopicGapThresholdSec) {
      rows.push(`Gap merge threshold: ${clampNumber(cfgSummaryTopicGapThresholdSec.value, 0, 300, 30)} sec`);
    }
    if (cfgAutoStopSilenceSec) {
      const mins = clampDecimal(cfgAutoStopSilenceSec.value, 0, 5, 1.25, 2);
      rows.push(mins > 0 ? `Auto-stop after silence: ${mins} min` : "Auto-stop after silence: off");
    }
    if (cfgPartialTranslateMinIntervalSec) {
      rows.push(`Translation update interval: ${cfgPartialTranslateMinIntervalSec.value} sec`);
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

  function applyTranslationVisibility() {
    const enabled = !!(state.currentConfig.translation_enabled ?? true);
    timeline.classList.toggle("translation-off", !enabled);
    if (timelineHead) timelineHead.classList.toggle("translation-off", !enabled);
    if (liveStrip) liveStrip.classList.toggle("translation-off", !enabled);
    if (translationOffBadge) translationOffBadge.classList.toggle("hidden", enabled);
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

  function applySummarySnapshot(summarySnap) {
    const snap = summarySnap || {};
    const summaryResult = snap.result || {};
    state.summary.pending = !!snap.pending;
    state.summary.generated_ts = snap.generated_ts || null;
    state.summary.executive_summary = String(
      snap.executive_summary || summaryResult.executive_summary || ""
    );
    state.summary.key_points = Array.isArray(snap.key_points)
      ? snap.key_points
      : (Array.isArray(summaryResult.key_points) ? summaryResult.key_points : []);
    state.summary.action_items = Array.isArray(snap.action_items)
      ? snap.action_items
      : (Array.isArray(summaryResult.action_items) ? summaryResult.action_items : []);
    state.summary.topic_key_points = Array.isArray(snap.topic_key_points)
      ? snap.topic_key_points
      : (Array.isArray(summaryResult.topic_key_points) ? summaryResult.topic_key_points : []);
    state.summary.entities = Array.isArray(snap.entities)
      ? snap.entities
      : (Array.isArray(summaryResult.entities) ? summaryResult.entities : []);
    state.summary.decisions_made = Array.isArray(snap.decisions_made)
      ? snap.decisions_made
      : (Array.isArray(summaryResult.decisions_made) ? summaryResult.decisions_made : []);
    state.summary.risks_and_blockers = Array.isArray(snap.risks_and_blockers)
      ? snap.risks_and_blockers
      : (Array.isArray(summaryResult.risks_and_blockers) ? summaryResult.risks_and_blockers : []);
    state.summary.key_terms_defined = Array.isArray(snap.key_terms_defined)
      ? snap.key_terms_defined
      : (Array.isArray(summaryResult.key_terms_defined) ? summaryResult.key_terms_defined : []);
    state.summary.metadata = (snap.metadata && typeof snap.metadata === "object")
      ? snap.metadata
      : ((summaryResult.metadata && typeof summaryResult.metadata === "object") ? summaryResult.metadata : {});
    state.summary.topic_breakdown = Array.isArray(snap.topic_breakdown) ? snap.topic_breakdown : [];
    state.summary.agenda_adherence_pct = (typeof snap.agenda_adherence_pct === "number") ? snap.agenda_adherence_pct : null;
    state.summary.meeting_insights = (snap.meeting_insights && typeof snap.meeting_insights === "object")
      ? snap.meeting_insights
      : ((summaryResult.meeting_insights && typeof summaryResult.meeting_insights === "object") ? summaryResult.meeting_insights : {});
    state.summary.keyword_index = Array.isArray(snap.keyword_index)
      ? snap.keyword_index
      : (Array.isArray(summaryResult.keyword_index) ? summaryResult.keyword_index : []);
    state.summary.error = String(snap.error || "");
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
      start_ts: Number(f.start_ts ?? f.ts ?? Date.now() / 1000),
      end_ts: Number(f.end_ts ?? f.ts ?? Date.now() / 1000),
      duration_sec: Number(
        f.duration_sec ?? Math.max(0, Number(f.end_ts ?? f.ts ?? 0) - Number(f.start_ts ?? f.ts ?? 0))
      ),
      offset_sec: f.offset_sec == null ? null : Number(f.offset_sec),
      timing_source: String(f.timing_source || "event_only"),
      recognizer_session_id: String(f.recognizer_session_id || ""),
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
      definitions: Array.isArray(topics.definitions) ? topics.definitions : (Array.isArray(state.topics.definitions) ? state.topics.definitions : []),
    };

    state.sessionStartedTs = msg.session_started_ts || null;
    state.running = !!msg.running;
    state.lastSpeechActivityTs = Date.now() / 1000;
    const telemetry = msg.telemetry || {};
    state.telemetry.latestMs = telemetry.translation_latest_ms ?? null;
    state.telemetry.p50Ms = telemetry.translation_p50_ms ?? null;
    state.telemetry.estimatedCostUsd = telemetry.estimated_cost_usd ?? null;
    setRecording(msg.recording || null);

    applySummarySnapshot(msg.summary || {});

    renderFinals();
    renderLogs();
    renderLivePartials();
    renderCoachHints();
    setTopicsUIFromState();
    renderTopics();
    renderSummary();
    setStatus(msg.status || "idle", msg.running ? "listening" : "connected");
    applyTimestampVisibility();
    applyTranslationVisibility();
    renderSilenceGuardChip();
    renderTimeStrip();
  }

  // ==========================================================================
  // API HELPERS + CONFIG REQUESTS
  // ==========================================================================

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
      translation_enabled: cfgTranslationEnabled ? cfgTranslationEnabled.checked : !!(existing.translation_enabled ?? true),
      summary_enabled: cfgSummaryEnabled ? cfgSummaryEnabled.checked : !!(existing.summary_enabled ?? true),
      summary_topic_duration_mode: cfgSummaryTopicDurationMode
        ? (["coverage_with_gaps", "speech_only"].includes(String(cfgSummaryTopicDurationMode.value || ""))
          ? cfgSummaryTopicDurationMode.value
          : "coverage_with_gaps")
        : String(existing.summary_topic_duration_mode || "coverage_with_gaps"),
      summary_topic_gap_threshold_sec: cfgSummaryTopicGapThresholdSec
        ? clampNumber(cfgSummaryTopicGapThresholdSec.value, 0, 300, 30)
        : Number(existing.summary_topic_gap_threshold_sec || 30),
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

  // ==========================================================================
  // EXPORT HELPERS
  // ==========================================================================

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
        start_unix_sec: Number(item.start_ts ?? item.ts ?? 0),
        end_unix_sec: Number(item.end_ts ?? item.ts ?? 0),
        duration_sec: Number(
          item.duration_sec ?? Math.max(0, Number(item.end_ts ?? item.ts ?? 0) - Number(item.start_ts ?? item.ts ?? 0))
        ),
        offset_sec: item.offset_sec == null ? null : Number(item.offset_sec),
        timing_source: item.timing_source || "event_only",
        recognizer_session_id: item.recognizer_session_id || "",
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
    const lines = [
      "index,speaker,speaker_label,time_local,time_unix_sec,start_unix_sec,end_unix_sec,duration_sec,offset_sec,timing_source,recognizer_session_id,bookmarked,bookmark_note,english,arabic",
    ];
    state.finals.forEach((item, idx) => {
      const key = finalKey(item);
      const bm = state.bookmarks[key] || null;
      const startTs = Number(item.start_ts ?? item.ts ?? 0);
      const endTs = Number(item.end_ts ?? item.ts ?? 0);
      const durationSec = Number(
        item.duration_sec ?? Math.max(0, Number(endTs) - Number(startTs))
      );
      lines.push(
        [
          idx + 1,
          escapeCsv(item.speaker || "default"),
          escapeCsv(item.speaker_label || "Speaker"),
          formatTime(item.ts),
          item.ts,
          startTs,
          endTs,
          durationSec,
          item.offset_sec == null ? "" : Number(item.offset_sec),
          escapeCsv(item.timing_source || "event_only"),
          escapeCsv(item.recognizer_session_id || ""),
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
    state.ui.logsView.pinned = {};
    renderLogs();
  }

  // ==========================================================================
  // COACH + TOPICS ACTIONS
  // ==========================================================================

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
    const definitions = ensureTopicDefinitions().map((row, idx) => ({
      ...row,
      order: idx,
    }));
    const payload = {
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

  async function clearTopics() {
    const out = await request("/api/topics/clear", "POST");
    if (out?.topics) {
      state.topics = { ...state.topics, ...out.topics };
      saveUiPrefs();
      setTopicsUIFromState();
      renderTopics();
    }
  }

  // ==========================================================================
  // WEBSOCKET INGESTION + LIVE UPDATES
  // ==========================================================================

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
      return;
    }

    if (msg.type === "telemetry") {
      state.telemetry.latestMs = msg.translation_latest_ms ?? null;
      state.telemetry.p50Ms = msg.translation_p50_ms ?? null;
      state.telemetry.estimatedCostUsd = msg.estimated_cost_usd ?? null;
      state.running = !!msg.recognition_running;
      state.recognitionStatus = msg.recognition_status || state.recognitionStatus;
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
        definitions: Array.isArray(topics.definitions) ? topics.definitions : (Array.isArray(state.topics.definitions) ? state.topics.definitions : []),
      };
      setTopicsUIFromState();
      renderTopics();
      return;
    }

    if (msg.type === "summary") {
      state.summary.pending = false;
      state.summary.error = String(msg.error || "");
      state.summary.generated_ts = msg.generated_ts || null;
      state.summary.executive_summary = String(msg.executive_summary || "");
      state.summary.key_points = Array.isArray(msg.key_points) ? msg.key_points : [];
      state.summary.action_items = Array.isArray(msg.action_items) ? msg.action_items : [];
      state.summary.topic_key_points = Array.isArray(msg.topic_key_points) ? msg.topic_key_points : [];
      state.summary.entities = Array.isArray(msg.entities) ? msg.entities : [];
      state.summary.decisions_made = Array.isArray(msg.decisions_made) ? msg.decisions_made : [];
      state.summary.risks_and_blockers = Array.isArray(msg.risks_and_blockers) ? msg.risks_and_blockers : [];
      state.summary.key_terms_defined = Array.isArray(msg.key_terms_defined) ? msg.key_terms_defined : [];
      state.summary.metadata = (msg.metadata && typeof msg.metadata === "object") ? msg.metadata : {};
      state.summary.topic_breakdown = Array.isArray(msg.topic_breakdown) ? msg.topic_breakdown : [];
      state.summary.agenda_adherence_pct = (typeof msg.agenda_adherence_pct === "number") ? msg.agenda_adherence_pct : null;
      state.summary.meeting_insights = (msg.meeting_insights && typeof msg.meeting_insights === "object")
        ? msg.meeting_insights
        : {};
      state.summary.keyword_index = Array.isArray(msg.keyword_index) ? msg.keyword_index : [];
      renderSummary();
      if (!msg.error) {
        setActiveTab("summaryTab");
        showToast("Summary ready.", "success");
      }
      return;
    }

    if (msg.type === "summary_cleared") {
      if (summaryKeywordSearch) summaryKeywordSearch.value = "";
      state.summary = {
        pending: false,
        generated_ts: null,
        executive_summary: "",
        key_points: [],
        action_items: [],
        topic_key_points: [],
        entities: [],
        decisions_made: [],
        risks_and_blockers: [],
        key_terms_defined: [],
        metadata: {},
        topic_breakdown: [],
        agenda_adherence_pct: null,
        meeting_insights: {},
        keyword_index: [],
        error: "",
      };
      renderSummary();
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

  // ==========================================================================
  // SOCKET LIFECYCLE
  // ==========================================================================

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
      scheduleReconnect();
    };
  }

  // ==========================================================================
  // UI EVENT BINDINGS
  // ==========================================================================

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  });
  if (transcriptExportMenuBtn && transcriptExportMenu) {
    transcriptExportMenuBtn.addEventListener("click", () => {
      toggleExportMenu(transcriptExportMenuBtn, transcriptExportMenu);
    });
  }
  if (summaryExportMenuBtn && summaryExportMenu) {
    summaryExportMenuBtn.addEventListener("click", () => {
      toggleExportMenu(summaryExportMenuBtn, summaryExportMenu);
    });
  }
  if (summaryTermsToggle && summaryTermsBody) {
    summaryTermsToggle.addEventListener("click", () => {
      const expanded = summaryTermsToggle.getAttribute("aria-expanded") === "true";
      summaryTermsToggle.setAttribute("aria-expanded", String(!expanded));
      summaryTermsBody.classList.toggle("hidden", expanded);
      const icon = summaryTermsToggle.querySelector(".summary-toggle-icon");
      if (icon) icon.textContent = expanded ? "\u25B6" : "\u25BE";
    });
  }
  if (summaryKeywordSearch) {
    summaryKeywordSearch.addEventListener("input", () => {
      renderKeywordIndex();
    });
  }
  // ── File Analysis Modal ──────────────────────────────────────────────────

  let fileModalSelectedFile = null;

  function openFileModal() {
    if (!fileAnalysisModal) return;
    fileModalSelectedFile = null;
    if (fileModalFilename) { fileModalFilename.textContent = ""; fileModalFilename.classList.add("hidden"); }
    if (fileModalAnalyseBtn) fileModalAnalyseBtn.disabled = true;
    if (fileModalPending) fileModalPending.classList.add("hidden");
    if (fileModalError) { fileModalError.textContent = ""; fileModalError.classList.add("hidden"); }
    if (transcriptFileInput) transcriptFileInput.value = "";
    fileAnalysisModal.showModal();
  }

  function closeFileModal() {
    if (fileAnalysisModal) fileAnalysisModal.close();
  }

  function setFileModalFile(f) {
    fileModalSelectedFile = f || null;
    if (!fileModalSelectedFile) return;
    if (fileModalFilename) {
      fileModalFilename.textContent = fileModalSelectedFile.name;
      fileModalFilename.classList.remove("hidden");
    }
    if (fileModalAnalyseBtn) fileModalAnalyseBtn.disabled = false;
    // Clear previous error when a new file is chosen.
    if (fileModalError) { fileModalError.textContent = ""; fileModalError.classList.add("hidden"); }
  }

  // Wire modal event listeners
  if (summaryFromFileBtn) summaryFromFileBtn.addEventListener("click", openFileModal);
  if (fileModalCloseBtn) fileModalCloseBtn.addEventListener("click", closeFileModal);
  if (fileAnalysisModal) fileAnalysisModal.addEventListener("click", (e) => { if (e.target === fileAnalysisModal) closeFileModal(); });

  if (transcriptFileInput) {
    transcriptFileInput.addEventListener("change", () => {
      setFileModalFile(transcriptFileInput.files && transcriptFileInput.files[0]);
    });
  }

  // Drag-and-drop onto the drop zone
  if (fileDropZone) {
    fileDropZone.addEventListener("dragover", (e) => { e.preventDefault(); fileDropZone.classList.add("dragover"); });
    fileDropZone.addEventListener("dragleave", () => fileDropZone.classList.remove("dragover"));
    fileDropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      fileDropZone.classList.remove("dragover");
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) setFileModalFile(f);
    });
  }

  if (fileModalAnalyseBtn) {
    fileModalAnalyseBtn.addEventListener("click", async () => {
      if (!fileModalSelectedFile) return;
      fileModalAnalyseBtn.disabled = true;
      if (fileModalPending) fileModalPending.classList.remove("hidden");
      if (fileModalError) { fileModalError.textContent = ""; fileModalError.classList.add("hidden"); }

      try {
        const form = new FormData();
        form.append("file", fileModalSelectedFile);
        const defs = Array.isArray(state.topics?.definitions) ? state.topics.definitions : [];
        form.append("topics_definitions_json", JSON.stringify(defs));
        const token = String(state.apiToken || "").trim();
        const headers = {};
        if (token) headers.Authorization = `Bearer ${token}`;
        const resp = await fetch("/api/summary/from-transcript", {
          method: "POST",
          headers: Object.keys(headers).length ? headers : undefined,
          body: form,
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(data.detail || `Server error ${resp.status}`);
        }
        const result = data.result || null;
        if (result && typeof result === "object") {
          const summarySnap = {
            pending: false,
            generated_ts: Date.now() / 1000,
            ...result,
          };
          if (summaryKeywordSearch) summaryKeywordSearch.value = "";
          applySummarySnapshot(summarySnap);
          renderSummary();
          closeFileModal();
          setActiveTab("summaryTab");
          showToast("Summary loaded from file.", "success");
        }
      } catch (err) {
        if (fileModalError) {
          fileModalError.textContent = String(err.message || err);
          fileModalError.classList.remove("hidden");
        }
      } finally {
        if (fileModalPending) fileModalPending.classList.add("hidden");
        fileModalAnalyseBtn.disabled = false;
      }
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

  if (cfgTranslationEnabled) {
    cfgTranslationEnabled.addEventListener("change", () => {
      setConfigDirty(true);
    });
  }
  if (cfgSummaryEnabled) {
    cfgSummaryEnabled.addEventListener("change", () => {
      setConfigDirty(true);
    });
  }

  if (summaryGenerateBtn) {
    summaryGenerateBtn.addEventListener("click", () => withBusy(summaryGenerateBtn, "Generating", async () => {
      const hasTranscript = (state.finals || []).some((f) => {
        const en = String(f?.en || "").trim();
        const ar = String(f?.ar || "").trim();
        return !!(en || ar);
      });
      if (!hasTranscript) {
        state.summary.pending = false;
        renderSummary();
        showToast("No transcript yet. Start speaking before generating a summary.", "info");
        return;
      }

      state.summary.pending = true;
      renderSummary();
      const out = await request("/api/summary/generate", "POST");
      if (out?.summary) {
        applySummarySnapshot(out.summary);
      } else {
        state.summary.pending = false;
      }
      renderSummary();
    }).catch((err) => {
      state.summary.pending = false;
      renderSummary();
      notifyError(err);
    }));
  }
  if (summaryClearBtn) {
    summaryClearBtn.addEventListener("click", () => withBusy(summaryClearBtn, "Clearing", async () => {
      await request("/api/summary/clear", "POST");
      showToast("Summary cleared.", "info");
    }).catch(notifyError));
  }

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
  if (exportSummaryJsonBtn) {
    exportSummaryJsonBtn.addEventListener("click", () => {
      exportSummaryJson();
      closeExportMenus();
      showToast("Summary JSON exported.", "success");
    });
  }
  if (exportSummaryTxtBtn) {
    exportSummaryTxtBtn.addEventListener("click", () => {
      exportSummaryTxt();
      closeExportMenus();
      showToast("Summary TXT exported.", "success");
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
      if ((transcriptExportMenu && !transcriptExportMenu.classList.contains("hidden")) || (summaryExportMenu && !summaryExportMenu.classList.contains("hidden"))) {
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

  // ==========================================================================
  // APP BOOTSTRAP
  // ==========================================================================

  loadUiPrefs();
  state.ui.activeSection = "transcriptTab";
  state.ui.mobileNavOpen = false;
  loadBookmarks();
  applyTheme();
  applyNavCollapsed();
  applyMobileNav();
  applyTimestampVisibility();
  applyTranslationVisibility();
  applyFontSettings();
  if (coachAskPanel) coachAskPanel.open = false;
  applySettingsAccordionPrefs();
  bindSettingsAccordionPrefs();
  applyLivePanelHeight(state.ui.livePanelHeight);
  syncCoachControlsUI();
  renderAutoStopHint();
  renderAutoStopPresetState();
  renderSilenceGuardChip();  setTopicsUIFromState();
  resetTopicDefinitionEditor();
  renderSummary();
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
