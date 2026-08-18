(() => {
  const STORAGE_KEY = "helpme.green.notebook.v2";
  const THEME_KEY = "helpme.green.theme";
  const PHOTO_DB_NAME = "helpme.green.photos.v1";
  const PHOTO_STORE_NAME = "photos";
  const MAX_PHOTOS_PER_PAGE = 3;
  const MAX_LIBRARY_REFERENCE_IMAGES = 3;
  const SUPPORTED_VISION_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);
  const ASSISTANT_VERIFICATION_NOTICE = "AI note: Models can make mistakes. Please check important details against reliable sources and, where relevant, measurements or qualified professional advice before acting.";
  const phases = [
    {id: "observe", label: "Observe", detail: "What is in front of you?", heading: "Start with the first look", lede: "Describe what is in front of you, what is happening with it, or what you need to understand. Your words stay attached to this phase.", question: "What do you see, and what would you like to understand?", change: ["A clearer view of surface, form, or condition.", "A note about what is known, suspected, or still open."]},
    {id: "identify", label: "Identify", detail: "Name with care", heading: "Name the material with care", lede: "Use the library to keep a helpful example nearby. A visual match is a starting point, not a confirmed answer.", question: "Which material type is worth checking next?", change: ["A label, document, or test result that supports the name.", "A mixed, coated, or layered piece that changes the first read."]},
    {id: "understand", label: "Understand", detail: "Keep the details", heading: "Keep the details together", lede: "Keep what you saw, the examples you chose, and the question you are trying to answer on the same page.", question: "What would change how you see this material?", change: ["A missing detail about its condition or past use.", "Something that does not fit the first read."]},
    {id: "options", label: "Options", detail: "Compare routes", heading: "Compare possible routes", lede: "Look at possible directions before you choose one. Keep the limits and the next check in view.", question: "Which direction is worth looking into first, and why?", change: ["A limit that makes one route less useful.", "A missing source, measurement, or expert check."]},
    {id: "next", label: "Next steps", detail: "Choose the next check", heading: "Choose the next useful check", lede: "End with a clear, reversible next action linked to your question—not a conclusion that goes beyond what you know.", question: "What is the simplest useful next check?", change: ["A new detail that answers the open question.", "A result that makes the next choice clearer."]}
  ];
  const categories = [
    {id: "plastics", label: "Plastics", image: "/assets/material-plastics.webp", subtypes: [
      {id: "pp", code: "PP", label: "Polypropylene", image: "/assets/material-pp.webp"},
      {id: "hdpe", code: "HDPE", label: "High-density polyethylene", image: "/assets/material-hdpe.webp"},
      {id: "ldpe", code: "LDPE", label: "Low-density polyethylene", image: "/assets/material-ldpe.webp"},
      {id: "abs", code: "ABS", label: "Acrylonitrile butadiene styrene", image: "/assets/material-abs.webp"},
      {id: "pet", code: "PET", label: "Polyethylene terephthalate", image: "/assets/material-pet.webp"},
      {id: "pvc", code: "PVC", label: "Polyvinyl chloride", image: "/assets/material-pvc.webp"},
      {id: "ps", code: "PS", label: "Polystyrene", image: "/assets/material-ps.webp"}
    ]},
    {id: "metals", label: "Metals", image: "/assets/material-metals.webp", subtypes: [
      {id: "steel", code: "Steel", label: "Carbon steel", image: "/assets/material-steel.webp"},
      {id: "aluminium", code: "Al", label: "Aluminium", image: "/assets/material-aluminium.webp"},
      {id: "copper", code: "Cu", label: "Copper", image: "/assets/material-copper.webp"},
      {id: "brass", code: "Brass", label: "Brass", image: "/assets/material-brass.webp"},
      {id: "stainless", code: "SS", label: "Stainless steel", image: "/assets/material-stainless.webp"},
      {id: "mixed-metal", code: "Mixed", label: "Mixed metal", image: "/assets/material-mixed-metal.webp"}
    ]},
    {id: "cable", label: "Cable & Harness", image: "/assets/material-cable-harness.webp", subtypes: [
      {id: "copper-cable", code: "Cable", label: "Copper conductor cable", image: "/assets/material-cable-harness.webp"},
      {id: "aluminium-cable", code: "Cable", label: "Aluminium conductor cable", image: "/assets/material-cable-harness.webp"},
      {id: "control-harness", code: "Harness", label: "Control harness", image: "/assets/material-cable-harness.webp"},
      {id: "data-cable", code: "Data", label: "Data cable", image: "/assets/material-cable-harness.webp"},
      {id: "coaxial", code: "Coax", label: "Coaxial cable", image: "/assets/material-cable-harness.webp"}
    ]},
    {id: "paper", label: "Paper & Board", image: "/assets/material-paper.webp", subtypes: [
      {id: "corrugated", code: "Board", label: "Corrugated board", image: "/assets/material-paper.webp"},
      {id: "kraft", code: "Paper", label: "Kraft paper", image: "/assets/material-paper.webp"},
      {id: "office", code: "Paper", label: "Office paper", image: "/assets/material-paper.webp"},
      {id: "coated", code: "Paper", label: "Coated paper", image: "/assets/material-paper.webp"},
      {id: "fiberboard", code: "Board", label: "Fiberboard", image: "/assets/material-paper.webp"}
    ]},
    {id: "glass", label: "Glass", image: "/assets/material-glass.webp", subtypes: [
      {id: "clear-glass", code: "Glass", label: "Clear glass", image: "/assets/material-glass.webp"},
      {id: "green-glass", code: "Glass", label: "Green glass", image: "/assets/material-glass.webp"},
      {id: "amber-glass", code: "Glass", label: "Amber glass", image: "/assets/material-glass.webp"},
      {id: "glass-fiber", code: "Fiber", label: "Glass fiber", image: "/assets/material-glass.webp"}
    ]},
    {id: "textiles", label: "Textiles", image: "/assets/material-textiles.webp", subtypes: [
      {id: "cotton", code: "Fiber", label: "Cotton", image: "/assets/material-textiles.webp"},
      {id: "polyester", code: "Fiber", label: "Polyester", image: "/assets/material-textiles.webp"},
      {id: "nylon", code: "Fiber", label: "Nylon", image: "/assets/material-textiles.webp"},
      {id: "wool", code: "Fiber", label: "Wool", image: "/assets/material-textiles.webp"},
      {id: "blend", code: "Blend", label: "Blended textile", image: "/assets/material-textiles.webp"},
      {id: "elastane", code: "Fiber", label: "Elastane", image: "/assets/material-textiles.webp"}
    ]}
  ];

  const elements = {
    body: document.body,
    phaseList: document.getElementById("phaseList"),
    pageState: document.getElementById("pageState"),
    railPageCount: document.getElementById("railPageCount"),
    railProgress: document.getElementById("railProgress"),
    leftPageTag: document.getElementById("leftPageTag"),
    pageLede: document.getElementById("pageLede"),
    noteTitle: document.getElementById("noteTitle"),
    boardImagePrimary: document.getElementById("boardImagePrimary"),
    boardImageSecondary: document.getElementById("boardImageSecondary"),
    boardImageTertiary: document.getElementById("boardImageTertiary"),
    observationList: document.getElementById("observationList"),
    observationCount: document.getElementById("observationCount"),
    evidencePhotos: document.getElementById("evidencePhotos"),
    evidencePhotoInput: document.getElementById("evidencePhotoInput"),
    evidenceCount: document.getElementById("evidenceCount"),
    evidenceForm: document.getElementById("evidenceForm"),
    evidenceCondition: document.getElementById("evidenceCondition"),
    evidenceOrigin: document.getElementById("evidenceOrigin"),
    evidenceDetails: document.getElementById("evidenceDetails"),
    evidenceNote: document.getElementById("evidenceNote"),
    modelDisclosure: document.getElementById("modelDisclosure"),
    clearDetachedPhotos: document.getElementById("clearDetachedPhotos"),
    evidenceGuidance: document.getElementById("evidenceGuidance"),
    evidenceGuidanceTitle: document.getElementById("evidenceGuidanceTitle"),
    evidenceGuidanceText: document.getElementById("evidenceGuidanceText"),
    referenceChips: document.getElementById("referenceChips"),
    compareEvidence: document.getElementById("compareEvidence"),
    comparisonHint: document.getElementById("comparisonHint"),
    composer: document.getElementById("composer"),
    message: document.getElementById("message"),
    send: document.getElementById("send"),
    statusNote: document.getElementById("statusNote"),
    retryRequest: document.getElementById("retryRequest"),
    noteDate: document.getElementById("noteDate"),
    workingTitle: document.getElementById("workingTitle"),
    workingRead: document.getElementById("workingRead"),
    readEvidence: document.getElementById("readEvidence"),
    changeList: document.getElementById("changeList"),
    nextQuestion: document.getElementById("nextQuestion"),
    usePrompt: document.getElementById("usePrompt"),
    assistantRead: document.getElementById("assistantRead"),
    assistantText: document.getElementById("assistantText"),
    sourceNote: document.getElementById("sourceNote"),
    comparisonRead: document.getElementById("comparisonRead"),
    comparisonText: document.getElementById("comparisonText"),
    comparisonSourceNote: document.getElementById("comparisonSourceNote"),
    previousPage: document.getElementById("previousPage"),
    nextPage: document.getElementById("nextPage"),
    pageProgress: document.getElementById("pageProgress"),
    noteHistory: document.getElementById("noteHistory"),
    historyList: document.getElementById("historyList"),
    library: document.getElementById("library"),
    libraryToggle: document.getElementById("libraryToggle"),
    libraryClose: document.getElementById("libraryClose"),
    libraryBackdrop: document.getElementById("libraryBackdrop"),
    materialSearch: document.getElementById("materialSearch"),
    categoryList: document.getElementById("categoryList"),
    globalSearch: document.getElementById("globalSearch"),
    newNote: document.getElementById("newNote"),
    themeToggle: document.getElementById("themeToggle"),
    authGate: document.getElementById("authGate"),
    authForm: document.getElementById("authForm"),
    authInput: document.getElementById("token"),
    authError: document.getElementById("authError"),
    settingsForm: document.getElementById("settingsForm"),
    settingsProvider: document.getElementById("settingsProvider"),
    settingsModel: document.getElementById("settingsModel"),
    settingsIdentity: document.getElementById("settingsIdentity"),
    settingsLocalaiBaseUrl: document.getElementById("settingsLocalaiBaseUrl"),
    settingsApiKey: document.getElementById("settingsApiKey"),
    settingsClearApiKey: document.getElementById("settingsClearApiKey"),
    settingsKeyStatus: document.getElementById("settingsKeyStatus"),
    settingsAiEnabled: document.getElementById("settingsAiEnabled"),
    settingsLocalaiTls: document.getElementById("settingsLocalaiTls"),
    settingsVision: document.getElementById("settingsVision"),
    settingsIncludeReasoning: document.getElementById("settingsIncludeReasoning"),
    settingsTemperature: document.getElementById("settingsTemperature"),
    settingsTopP: document.getElementById("settingsTopP"),
    settingsTopK: document.getElementById("settingsTopK"),
    settingsMinP: document.getElementById("settingsMinP"),
    settingsMaxTokens: document.getElementById("settingsMaxTokens"),
    settingsContextWindow: document.getElementById("settingsContextWindow"),
    settingsTimeout: document.getElementById("settingsTimeout"),
    settingsReasoningStrength: document.getElementById("settingsReasoningStrength"),
    settingsAdvancedOptions: document.getElementById("settingsAdvancedOptions"),
    settingsQualityJudges: document.getElementById("settingsQualityJudges"),
    settingsRetries: document.getElementById("settingsRetries"),
    settingsDiscoveryTimeout: document.getElementById("settingsDiscoveryTimeout"),
    settingsMaxTimeout: document.getElementById("settingsMaxTimeout"),
    settingsTheme: document.getElementById("settingsTheme"),
    saveSettings: document.getElementById("saveSettings"),
    settingsStatus: document.getElementById("settingsStatus")
  };
  const libraryBackground = [
    document.querySelector(".topbar"),
    document.querySelector(".phase-rail"),
    document.querySelector(".notebook-column")
  ].filter(Boolean);

  let sessionId = null;
  let configuredModelIdentity = "";
  let detachedPhotoCount = 0;
  let conversationGeneration = 0;
  let token = "";
  let starting = false;
  let requestPending = false;
  let requestPhaseIndex = null;
  let comparisonPending = false;
  let comparisonPhaseIndex = null;
  let lastFailedRequest = null;
  let persistenceError = "";
  let photoStorageError = "";
  let photoDbPromise = null;
  let photoRenderVersion = 0;
  let libraryTrigger = null;
  let turnTimer = null;
  let loadedSettings = null;

  function blankEvidence() {
    return {photos: [], form: "", condition: "", origin: "", details: ""};
  }
  function blankPage() {
    return {draft: "", observations: [], references: [], reply: "", sources: [], comparison: "", comparisonSources: [], evidence: blankEvidence()};
  }
  function freshState() {
    return {
      title: "New material note",
      createdAt: new Date().toISOString(),
      sessionId: null,
      currentPhase: 0,
      selectedCategory: "plastics",
      pages: phases.map(() => blankPage()),
      history: []
    };
  }
  function migrateMaterialAsset(value) {
    if (typeof value !== "string") return value;
    return value.replace(/^(\/assets\/material-[^?]+)\.png$/, "$1.webp");
  }
  function isAssistantFailureText(value) {
    return typeof value === "string" && /^(I couldn.?t get a response from the local model just now|I couldn.?t answer that right now)/i.test(value.trim());
  }
  function withAssistantVerificationNotice(value) {
    const text = typeof value === "string" ? value.trim() : "";
    if (!text || text.toLowerCase().includes(ASSISTANT_VERIFICATION_NOTICE.toLowerCase())) return text;
    return text + "\n\n" + ASSISTANT_VERIFICATION_NOTICE;
  }
  function modelTargetLabel() {
    return configuredModelIdentity || "the configured vision model";
  }
  function validTimestamp(value) {
    return typeof value === "string" && Number.isFinite(Date.parse(value)) ? value : "";
  }
  function validPhoto(value, index, keepLegacyData) {
    if (!value || typeof value !== "object") return null;
    const legacyDataUrl = typeof value.dataUrl === "string" && value.dataUrl.startsWith("data:image/") && value.dataUrl.length <= 1600000
      ? value.dataUrl
      : typeof value.legacyDataUrl === "string" && value.legacyDataUrl.startsWith("data:image/") && value.legacyDataUrl.length <= 1600000
        ? value.legacyDataUrl
        : "";
    if (!legacyDataUrl && typeof value.id !== "string") return null;
    const generatedId = "photo-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
    const photo = {
      id: typeof value.id === "string" && value.id ? value.id.slice(0, 120) : generatedId + "-" + index,
      name: typeof value.name === "string" ? value.name.slice(0, 80) : "Sample photo",
      type: typeof value.type === "string" ? value.type.slice(0, 80) : "image/jpeg",
      size: Number.isFinite(value.size) ? Math.max(0, Math.min(value.size, 8_000_000)) : 0
    };
    if (keepLegacyData && legacyDataUrl) photo.legacyDataUrl = legacyDataUrl;
    return photo;
  }
  function validEvidence(value, keepLegacyData = true) {
    const evidence = blankEvidence();
    if (!value || typeof value !== "object") return evidence;
    const allowedForms = ["", "whole", "flakes", "granules", "powder", "mixed", "closed"];
    const allowedConditions = ["", "clean", "worn", "dirty", "mixed", "damaged", "unknown"];
    evidence.form = allowedForms.includes(value.form) ? value.form : "";
    evidence.condition = allowedConditions.includes(value.condition) ? value.condition : "";
    evidence.origin = typeof value.origin === "string" ? value.origin.slice(0, 140) : "";
    evidence.details = typeof value.details === "string" ? value.details.slice(0, 220) : "";
    evidence.photos = Array.isArray(value.photos)
      ? value.photos.map((photo, index) => validPhoto(photo, index, keepLegacyData)).filter(Boolean).slice(0, MAX_PHOTOS_PER_PAGE)
      : [];
    return evidence;
  }
  function validPage(value, keepLegacyData = true) {
    const source = value && typeof value === "object" ? value : {};
    return {
      draft: typeof source.draft === "string" ? source.draft.slice(0, 4000) : "",
      observations: Array.isArray(source.observations) ? source.observations.filter((item) => typeof item === "string").slice(0, 80) : [],
      references: Array.isArray(source.references) ? source.references.filter((item) => item && typeof item.id === "string").slice(0, 40).map((item) => Object.assign({}, item, {image: migrateMaterialAsset(item.image)})) : [],
      reply: typeof source.reply === "string" && !isAssistantFailureText(source.reply) ? source.reply : "",
      sources: Array.isArray(source.sources) ? source.sources.slice(0, 20) : [],
      comparison: typeof source.comparison === "string" && !isAssistantFailureText(source.comparison) ? source.comparison : "",
      comparisonSources: Array.isArray(source.comparisonSources) ? source.comparisonSources.slice(0, 20) : [],
      evidence: validEvidence(source.evidence, keepLegacyData)
    };
  }
  function validHistory(value) {
    if (!Array.isArray(value)) return [];
    return value.map((snapshot) => {
      if (!snapshot || typeof snapshot !== "object" || !Array.isArray(snapshot.pages)) return null;
      return {
        title: typeof snapshot.title === "string" ? snapshot.title.slice(0, 90) : "Untitled material note",
        createdAt: validTimestamp(snapshot.createdAt),
        savedAt: validTimestamp(snapshot.savedAt),
        pages: phases.map((_, index) => validPage(snapshot.pages[index], true))
      };
    }).filter(Boolean);
  }
  function validState(value) {
    if (!value || !Array.isArray(value.pages)) return freshState();
    const next = freshState();
    next.title = typeof value.title === "string" ? value.title.slice(0, 90) : next.title;
    next.createdAt = validTimestamp(value.createdAt) || next.createdAt;
    next.sessionId = typeof value.sessionId === "string" && value.sessionId ? value.sessionId.slice(0, 160) : null;
    next.currentPhase = Number.isInteger(value.currentPhase) ? Math.min(Math.max(value.currentPhase, 0), phases.length - 1) : 0;
    next.selectedCategory = categories.some((category) => category.id === value.selectedCategory) ? value.selectedCategory : "plastics";
    next.history = validHistory(value.history);
    next.pages = phases.map((_, index) => validPage(value.pages[index], true));
    return next;
  }
  function loadState() {
    try { return validState(JSON.parse(localStorage.getItem(STORAGE_KEY) || "null")); }
    catch (_) { return freshState(); }
  }
  let state = loadState();
  sessionId = state.sessionId;

  function persistablePage(page) {
    const safe = validPage(page, false);
    safe.evidence.photos = (page.evidence && Array.isArray(page.evidence.photos) ? page.evidence.photos : [])
      .map((photo, index) => {
        const persisted = validPhoto(photo, index, false);
        if (!persisted) return null;
        if (photo && typeof photo.legacyDataUrl === "string" && photo.legacyDataUrl.startsWith("data:image/")) {
          persisted.dataUrl = photo.legacyDataUrl;
        }
        return persisted;
      }).filter(Boolean).slice(0, MAX_PHOTOS_PER_PAGE);
    return safe;
  }
  function persistableState() {
    return {
      title: state.title,
      createdAt: state.createdAt,
      sessionId: state.sessionId || null,
      currentPhase: state.currentPhase,
      selectedCategory: state.selectedCategory,
      pages: state.pages.map((page) => persistablePage(page)),
      history: (state.history || []).map((snapshot) => Object.assign({}, snapshot, {
        pages: Array.isArray(snapshot.pages) ? snapshot.pages.map((page) => persistablePage(page)) : []
      }))
    };
  }
  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(persistableState()));
      persistenceError = "";
      return true;
    } catch (_) {
      persistenceError = "Browser storage is full. Your changes remain on screen but may not survive a reload.";
      return false;
    }
  }
  function openPhotoDb() {
    if (photoDbPromise) return photoDbPromise;
    if (!window.indexedDB) return Promise.reject(new Error("This browser does not support local photo storage."));
    photoDbPromise = new Promise((resolve, reject) => {
      const request = window.indexedDB.open(PHOTO_DB_NAME, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(PHOTO_STORE_NAME)) {
          request.result.createObjectStore(PHOTO_STORE_NAME, {keyPath: "id"});
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Local photo storage could not be opened."));
    }).catch((error) => {
      photoDbPromise = null;
      throw error;
    });
    return photoDbPromise;
  }
  function photoRequest(mode, operation) {
    return openPhotoDb().then((database) => new Promise((resolve, reject) => {
      const transaction = database.transaction(PHOTO_STORE_NAME, mode);
      const request = operation(transaction.objectStore(PHOTO_STORE_NAME));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Local photo storage failed."));
      transaction.onerror = () => reject(transaction.error || new Error("Local photo storage failed."));
    }));
  }
  function putPhoto(photo, blob, detachedAt = null) {
    return photoRequest("readwrite", (store) => store.put({
      id: photo.id,
      name: photo.name,
      type: photo.type,
      size: blob.size,
      detachedAt,
      blob
    }));
  }
  function getPhoto(id) {
    return photoRequest("readonly", (store) => store.get(id));
  }
  function getAllPhotos() {
    return photoRequest("readonly", (store) => store.getAll());
  }
  async function detachPhoto(id) {
    const record = await getPhoto(id);
    if (!record || !record.blob) return;
    await putPhoto(record, record.blob, new Date().toISOString());
  }
  function referencedPhotoIds() {
    const pages = state.pages.concat((state.history || []).flatMap((snapshot) => snapshot.pages || []));
    return new Set(pages.flatMap((page) => ((page.evidence && page.evidence.photos) || []).map((photo) => photo.id)));
  }
  async function refreshDetachedPhotoStatus() {
    try {
      const referenced = referencedPhotoIds();
      const records = await getAllPhotos();
      detachedPhotoCount = records.filter((record) => record && record.detachedAt && !referenced.has(record.id)).length;
      updateDetachedPhotoControl();
    } catch (_) {
      detachedPhotoCount = 0;
      updateDetachedPhotoControl();
    }
  }
  function updateDetachedPhotoControl() {
    if (!elements.clearDetachedPhotos) return;
    elements.clearDetachedPhotos.hidden = detachedPhotoCount === 0;
    elements.clearDetachedPhotos.textContent = detachedPhotoCount === 1
      ? "Clear 1 removed original"
      : "Clear " + detachedPhotoCount + " removed originals";
  }
  async function clearDetachedPhotos() {
    const referenced = referencedPhotoIds();
    const records = await getAllPhotos();
    const removable = records.filter((record) => record && record.detachedAt && !referenced.has(record.id));
    if (!removable.length) {
      detachedPhotoCount = 0;
      updateDetachedPhotoControl();
      return;
    }
    const label = removable.length === 1 ? "1 removed original" : removable.length + " removed originals";
    if (!window.confirm("Permanently clear " + label + " from this browser?")) return;
    for (const record of removable) {
      await photoRequest("readwrite", (store) => store.delete(record.id));
    }
    await refreshDetachedPhotoStatus();
  }
  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("The sample photo could not be prepared for the assistant."));
      reader.onload = () => resolve(String(reader.result || ""));
      reader.readAsDataURL(blob);
    });
  }
  async function modelImagesForPage(page) {
    const images = [];
    for (const photo of (page.evidence && page.evidence.photos) || []) {
      let dataUrl = photo.legacyDataUrl || "";
      let mimeType = photo.type || "";
      if (!dataUrl) {
        const record = await getPhoto(photo.id);
        if (!record || !record.blob) {
          throw new Error("The sample photo could not be loaded for the assistant.");
        }
        mimeType = record.blob.type || mimeType;
        dataUrl = await blobToDataUrl(record.blob);
      }
      const type = mimeType.toLowerCase();
      if (!SUPPORTED_VISION_IMAGE_TYPES.has(type) || !dataUrl.startsWith("data:image/")) {
        throw new Error("Use PNG, JPEG, WebP, or GIF photos for visual analysis.");
      }
      images.push({name: photo.name || "Sample photo", mime_type: type, data_url: dataUrl});
    }
    for (const reference of (page.references || []).slice(0, MAX_LIBRARY_REFERENCE_IMAGES)) {
      try {
        const response = await fetch(reference.image);
        if (!response.ok) continue;
        const blob = await response.blob();
        const type = (blob.type || "").toLowerCase();
        if (!SUPPORTED_VISION_IMAGE_TYPES.has(type)) continue;
        images.push({
          name: "Library example — " + (reference.label || reference.code || "reference"),
          mime_type: type,
          data_url: await blobToDataUrl(blob)
        });
      } catch (_) {
        // The labels remain in the text prompt when an illustrative asset cannot be loaded.
      }
    }
    return images;
  }
  function dataUrlToBlob(dataUrl) {
    const parts = dataUrl.split(",", 2);
    if (parts.length !== 2) throw new Error("The sample photo data is incomplete.");
    const header = parts[0].match(/^data:([^;]+);base64$/i);
    if (!header) throw new Error("The sample photo data is invalid.");
    const bytes = window.atob(parts[1]);
    const buffer = new Uint8Array(bytes.length);
    for (let index = 0; index < bytes.length; index += 1) buffer[index] = bytes.charCodeAt(index);
    return new Blob([buffer], {type: header[1]});
  }
  async function migrateLegacyPhotos() {
    let migrated = false;
    const pages = state.pages.concat((state.history || []).flatMap((snapshot) => snapshot.pages || []));
    for (const page of pages) {
      for (const photo of page.evidence.photos) {
        if (!photo.legacyDataUrl) continue;
        try {
          await putPhoto(photo, dataUrlToBlob(photo.legacyDataUrl));
          delete photo.legacyDataUrl;
          migrated = true;
        } catch (_) {
          photoStorageError = "A previous photo is still kept in browser storage because photo storage could not be opened.";
        }
      }
    }
    if (migrated) {
      saveState();
      renderAll();
    }
  }
  function activePage() { return state.pages[state.currentPhase]; }
  function phaseHasWork(index) {
    const page = state.pages[index];
    return Boolean(page && (
      page.observations.length || page.references.length || page.reply || page.comparison || page.draft.trim() ||
      page.evidence.photos.length || page.evidence.condition || page.evidence.origin.trim() || page.evidence.details.trim()
    ));
  }
  function phaseState(index) {
    if (index === state.currentPhase) return "active";
    if (phaseHasWork(index) || index < state.currentPhase) return "complete";
    return "pending";
  }
  function setTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    elements.body.dataset.theme = next;
    elements.themeToggle.textContent = next === "dark" ? "Light mode" : "Dark mode";
    document.querySelector('meta[name="theme-color"]').setAttribute("content", next === "dark" ? "#101a14" : "#f4f0e7");
    try { localStorage.setItem(THEME_KEY, next); } catch (_) {}
  }
  function loadTheme() {
    try { return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light"; }
    catch (_) { return "light"; }
  }
  function renderPhaseRail() {
    elements.phaseList.replaceChildren();
    phases.forEach((phase, index) => {
      const item = document.createElement("li");
      item.className = "phase-step";
      item.dataset.state = phaseState(index);
      const button = document.createElement("button");
      button.className = "phase-button";
      button.type = "button";
      button.setAttribute("aria-label", "Open phase " + (index + 1) + ": " + phase.label);
      const number = document.createElement("span");
      number.className = "phase-number";
      number.textContent = String(index + 1);
      const copy = document.createElement("span");
      copy.className = "phase-copy";
      const label = document.createElement("span");
      label.className = "phase-label";
      label.textContent = phase.label;
      const detail = document.createElement("span");
      detail.className = "phase-detail";
      detail.textContent = phase.detail;
      const status = document.createElement("span");
      status.className = "phase-status";
      status.textContent = phaseState(index) === "complete" ? "Saved" : phaseState(index) === "active" ? "In progress" : "Not started";
      copy.append(label, detail, status);
      button.append(number, copy);
      button.addEventListener("click", () => goToPhase(index));
      item.appendChild(button);
      elements.phaseList.appendChild(item);
    });
    const progress = ((state.currentPhase + 1) / phases.length) * 100;
    elements.railPageCount.textContent = "Phase " + (state.currentPhase + 1) + " of " + phases.length;
    elements.railProgress.style.width = progress + "%";
  }
  function renderPageProgress() {
    elements.pageProgress.replaceChildren();
    phases.forEach((phase, index) => {
      const dot = document.createElement("button");
      dot.className = "page-dot";
      dot.type = "button";
      dot.setAttribute("aria-label", "Go to phase " + (index + 1) + ": " + phase.label);
      if (index === state.currentPhase) dot.classList.add("active");
      if (phaseState(index) === "complete" && index !== state.currentPhase) dot.classList.add("complete");
      dot.addEventListener("click", () => goToPhase(index));
      elements.pageProgress.appendChild(dot);
    });
  }
  function renderObservations(page) {
    elements.observationList.replaceChildren();
    elements.observationCount.textContent = page.observations.length + " saved";
    if (!page.observations.length) {
      const empty = document.createElement("li");
      empty.className = "empty-row";
      empty.textContent = "Your observations will stay on this page.";
      elements.observationList.appendChild(empty);
      return;
    }
    page.observations.forEach((observation, index) => {
      const row = document.createElement("li");
      row.className = "observation-row";
      const number = document.createElement("span");
      number.className = "observation-index";
      number.textContent = String(index + 1).padStart(2, "0");
      const text = document.createElement("span");
      text.className = "observation-text";
      text.textContent = observation;
      const remove = document.createElement("button");
      remove.className = "observation-remove";
      remove.type = "button";
      remove.textContent = "Remove";
      remove.disabled = requestPending || comparisonPending;
      remove.setAttribute("aria-label", "Remove observation " + (index + 1));
      remove.addEventListener("click", () => {
        page.observations.splice(index, 1);
        page.reply = "";
        page.sources = [];
        page.comparison = "";
        page.comparisonSources = [];
        lastFailedRequest = null;
        saveState();
        renderAll();
      });
      row.append(number, text, remove);
      elements.observationList.appendChild(row);
    });
  }
  function renderEvidence(page) {
    const evidence = page.evidence || blankEvidence();
    const formGuidance = {
      whole: {
        title: "Whole piece",
        text: "A photo can show shape and surface. It still cannot confirm the exact material, grade, or blend."
      },
      flakes: {
        title: "Flakes / chips",
        text: "A photo can show colour, shape, and visible mix. If safe, add an overall view and a close-up. It cannot confirm the exact material from appearance alone."
      },
      granules: {
        title: "Granules / pellets",
        text: "A photo can show colour, size, shape, and whether the sample looks mixed. If safe, add a close-up with a size reference. It cannot confirm the polymer, alloy, or blend."
      },
      powder: {
        title: "Powder / dust",
        text: "Photos can show colour and texture, but not reliably name the material. If safe, photograph the container or settled sample. If the dust may be unsafe, keep it closed and do not spread it just for a photo."
      },
      mixed: {
        title: "Mixed pieces",
        text: "Treat this as a mixture first. If safe, add an overview and a close-up of the different pieces. The assistant will inspect the attached image and keep the result as a mixture instead of forcing one material name."
      },
      closed: {
        title: "Closed container",
        text: "Keep an unknown sample closed. A photo of the container, label, and source can help, but a photo alone cannot name what is inside."
      }
    };
    const renderVersion = ++photoRenderVersion;
    elements.evidencePhotos.replaceChildren();
    elements.evidenceCount.textContent = evidence.photos.length + " photo" + (evidence.photos.length === 1 ? "" : "s");
    if (!evidence.photos.length) {
      const empty = document.createElement("span");
      empty.className = "evidence-empty";
      empty.textContent = "Add a photo of the real piece when you have one.";
      elements.evidencePhotos.appendChild(empty);
    } else {
      evidence.photos.forEach((photo, index) => {
        const frame = document.createElement("div");
        frame.className = "evidence-photo";
        const image = document.createElement("img");
        image.alt = "User sample photo " + (index + 1);
        if (photo.legacyDataUrl) {
          image.src = photo.legacyDataUrl;
        } else {
          void getPhoto(photo.id).then((record) => {
            if (renderVersion !== photoRenderVersion || !record || !record.blob) return;
            const objectUrl = URL.createObjectURL(record.blob);
            image.src = objectUrl;
            image.addEventListener("load", () => URL.revokeObjectURL(objectUrl), {once: true});
          }).catch(() => {
            if (renderVersion === photoRenderVersion) image.alt += " (preview unavailable)";
          });
        }
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove from page";
        remove.setAttribute("aria-label", "Remove user sample photo " + (index + 1) + " from this page");
        remove.addEventListener("click", () => {
          activePage().evidence.photos = activePage().evidence.photos.filter((item) => item.id !== photo.id);
          activePage().comparison = "";
          activePage().comparisonSources = [];
          saveState();
          renderAll();
          void detachPhoto(photo.id).then(refreshDetachedPhotoStatus).catch(() => {
            photoStorageError = "The photo was removed from this page, but local photo storage could not update its archive status.";
            renderNotebook();
          });
        });
        frame.append(image, remove);
        elements.evidencePhotos.appendChild(frame);
      });
    }
    elements.evidenceForm.value = evidence.form;
    elements.evidenceCondition.value = evidence.condition;
    elements.evidenceOrigin.value = evidence.origin;
    elements.evidenceDetails.value = evidence.details;
    const guidance = formGuidance[evidence.form];
    elements.evidenceGuidance.hidden = !guidance;
    if (guidance) {
      elements.evidenceGuidanceTitle.textContent = guidance.title;
      elements.evidenceGuidanceText.textContent = guidance.text;
    } else {
      elements.evidenceGuidanceTitle.textContent = "";
      elements.evidenceGuidanceText.textContent = "";
    }
    const detail = evidence.form || evidence.condition || evidence.origin || evidence.details;
    elements.evidenceNote.textContent = evidence.photos.length
      ? "Your original photo" + (evidence.photos.length === 1 ? " is" : "s are") + " ready for the next comparison."
      : detail
        ? "These details stay with this page. Add a photo when you have one."
        : "No photo yet. Your notes are enough to start.";
    if (elements.modelDisclosure) elements.modelDisclosure.textContent = modelTargetLabel();
    updateDetachedPhotoControl();
  }
  function renderReferences(page) {
    elements.referenceChips.replaceChildren();
    if (!page.references.length) {
      const empty = document.createElement("span");
      empty.className = "reference-empty";
      empty.textContent = "Choose a family or subtype from the library when it helps.";
      elements.referenceChips.appendChild(empty);
      return;
    }
    page.references.forEach((reference) => {
      const chip = document.createElement("span");
      chip.className = "reference-chip";
      const image = document.createElement("img");
      image.src = reference.image;
      image.alt = "";
      const label = document.createElement("span");
      label.textContent = reference.code + " — " + reference.label;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", "Remove " + reference.label);
      remove.addEventListener("click", () => {
        activePage().references = activePage().references.filter((item) => item.id !== reference.id);
        activePage().comparison = "";
        activePage().comparisonSources = [];
        saveState();
        renderAll();
      });
      chip.append(image, label, remove);
      elements.referenceChips.appendChild(chip);
    });
  }
  function renderRead(page, phase) {
    elements.workingTitle.textContent = phase.heading;
    const firstAssistantLine = page.reply.trim().split(/\n+/)[0].trim();
    elements.workingRead.textContent = firstAssistantLine ? firstAssistantLine.slice(0, 240) : phase.lede;
    elements.pageLede.textContent = phase.lede;
    elements.nextQuestion.textContent = phase.question;
    elements.changeList.replaceChildren();
    phase.change.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      elements.changeList.appendChild(item);
    });
    elements.readEvidence.replaceChildren();
    const evidence = [];
    if (page.observations.length) evidence.push(page.observations.length + " note" + (page.observations.length === 1 ? "" : "s") + " saved on this phase.");
    if (page.references.length) evidence.push(page.references.length + " library example" + (page.references.length === 1 ? "" : "s") + " kept with this phase.");
    if (!evidence.length) evidence.push("Nothing has been added to this phase yet.");
    evidence.push("The library images are examples; a material name still needs context or a test.");
    evidence.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      elements.readEvidence.appendChild(item);
    });
    if (page.reply) {
      elements.assistantRead.hidden = false;
      elements.assistantText.textContent = withAssistantVerificationNotice(page.reply);
      const sources = page.sources || [];
      elements.sourceNote.textContent = sources.length ? sources.map((source) => source.label || "Reference").join(" · ") : "No source linked to this read yet.";
    } else {
      elements.assistantRead.hidden = true;
      elements.assistantText.textContent = "";
      elements.sourceNote.textContent = "";
    }
    if (page.comparison) {
      elements.comparisonRead.hidden = false;
      elements.comparisonText.textContent = withAssistantVerificationNotice(page.comparison);
      const comparisonSources = page.comparisonSources || [];
      elements.comparisonSourceNote.textContent = comparisonSources.length
        ? comparisonSources.map((source) => source.label || "Reference").join(" · ")
        : "No source linked to this comparison yet.";
    } else {
      elements.comparisonRead.hidden = true;
      elements.comparisonText.textContent = "";
      elements.comparisonSourceNote.textContent = "";
    }
  }
  function renderNotebook() {
    const page = activePage();
    const phase = phases[state.currentPhase];
    const difficultForm = ["granules", "powder", "mixed", "closed"].includes(page.evidence.form);
    elements.noteTitle.value = state.title;
    fitNoteTitle();
    elements.noteDate.textContent = "NOTE — " + new Intl.DateTimeFormat("en-GB", {day: "2-digit", month: "short", year: "numeric"}).format(new Date(state.createdAt || Date.now())).toUpperCase();
    elements.leftPageTag.textContent = phase.label.toUpperCase();
    elements.pageState.textContent = "Phase " + (state.currentPhase + 1) + " of " + phases.length;
    elements.message.value = page.draft;
    elements.message.placeholder = "Add an observation for " + phase.label.toLowerCase() + "...";
    renderObservations(page);
    renderEvidence(page);
    renderReferences(page);
    renderRead(page, phase);
    renderPageProgress();
    elements.previousPage.disabled = state.currentPhase === 0;
    elements.nextPage.textContent = state.currentPhase === phases.length - 1 ? "Finish this note" : "Continue to " + phases[state.currentPhase + 1].label.toLowerCase();
    const pageRequestPending = requestPending && requestPhaseIndex === state.currentPhase;
    const pageComparisonPending = comparisonPending && comparisonPhaseIndex === state.currentPhase;
    const pageFailure = lastFailedRequest && lastFailedRequest.phaseIndex === state.currentPhase ? lastFailedRequest : null;
    const offline = typeof navigator !== "undefined" && navigator.onLine === false;
    elements.statusNote.classList.toggle("is-pending", pageComparisonPending || pageRequestPending);
    elements.statusNote.textContent = persistenceError || photoStorageError
      ? persistenceError || photoStorageError
      : pageComparisonPending
      ? "Sending the original photo and all saved page details to " + modelTargetLabel() + "..."
      : pageRequestPending
        ? "Sending the observation and attached photo to " + modelTargetLabel() + "..."
        : pageFailure
          ? offline
            ? "You appear to be offline. Your note is saved here; try again when connected."
            : pageFailure.kind === "comparison"
              ? "Your notes are saved on this page. The comparison is not available right now."
              : "The observation is saved on this page. The assistant read is not available right now."
        : "Autosaved in this browser. Nothing is lost when you move between phases.";
    elements.retryRequest.hidden = !pageFailure || pageRequestPending || pageComparisonPending;
    const hasComparisonInput = Boolean(
      page.observations.length || page.references.length || page.evidence.photos.length || page.evidence.condition || page.evidence.origin || page.evidence.details
    );
    elements.compareEvidence.disabled = comparisonPending || requestPending || !hasComparisonInput;
    elements.composer.setAttribute("aria-busy", pageRequestPending ? "true" : "false");
    elements.send.disabled = pageRequestPending || pageComparisonPending;
    elements.compareEvidence.textContent = pageComparisonPending ? "Comparing..." : difficultForm ? "Compare carefully" : "Compare with assistant";
    elements.comparisonHint.textContent = hasComparisonInput
      ? difficultForm
        ? "Next: click Compare carefully · attached photo + all page details will be analyzed"
        : "Next: click Compare with assistant · attached photo + all page details will be analyzed"
      : difficultForm
        ? "Add a note or example first · the attached photo will be analyzed with it"
        : "Add an observation or library example first";
  }
  function renderHistory() {
    elements.historyList.replaceChildren();
    const history = Array.isArray(state.history) ? state.history : [];
    elements.noteHistory.hidden = history.length === 0;
    history.forEach((snapshot, index) => {
      const button = document.createElement("button");
      button.className = "history-item";
      button.type = "button";
      const label = document.createElement("span");
      label.textContent = snapshot.title || "Untitled note";
      const restore = document.createElement("span");
      restore.textContent = "Restore";
      button.append(label, restore);
      button.addEventListener("click", () => restoreHistory(index));
      elements.historyList.appendChild(button);
    });
  }
  function renderLibrary() {
    const query = elements.materialSearch.value.trim().toLowerCase();
    elements.categoryList.replaceChildren();
    categories.forEach((category) => {
      const matchingSubtypes = category.subtypes.filter((subtype) => !query || (category.label + " " + subtype.code + " " + subtype.label).toLowerCase().includes(query));
      if (query && !matchingSubtypes.length && !category.label.toLowerCase().includes(query)) return;
      const block = document.createElement("section");
      block.className = "category-block";
      const categoryButton = document.createElement("button");
      categoryButton.className = "category-button" + (state.selectedCategory === category.id ? " active" : "");
      categoryButton.type = "button";
      categoryButton.setAttribute("aria-expanded", state.selectedCategory === category.id ? "true" : "false");
      const image = document.createElement("img");
      image.className = "category-thumb";
      image.src = category.image;
      image.alt = "";
      const copy = document.createElement("span");
      copy.className = "category-copy";
      const name = document.createElement("span");
      name.className = "category-name";
      name.textContent = category.label;
      const count = document.createElement("span");
      count.className = "category-count";
      count.textContent = category.subtypes.length + " types";
      copy.append(name, count);
      const stateMark = document.createElement("span");
      stateMark.className = "category-state";
      stateMark.textContent = state.selectedCategory === category.id ? "Close" : "Open";
      categoryButton.append(image, copy, stateMark);
      categoryButton.addEventListener("click", () => {
        state.selectedCategory = state.selectedCategory === category.id ? "" : category.id;
        saveState();
        renderLibrary();
      });
      block.appendChild(categoryButton);
      if (state.selectedCategory === category.id || query) {
        const subtypeList = document.createElement("div");
        subtypeList.className = "subtype-list";
        const subtypes = query ? matchingSubtypes : category.subtypes;
        subtypes.forEach((subtype) => {
          const selected = activePage().references.some((reference) => reference.id === subtype.id);
          const subtypeButton = document.createElement("button");
          subtypeButton.className = "subtype-button" + (selected ? " selected" : "");
          subtypeButton.type = "button";
          subtypeButton.setAttribute("aria-pressed", selected ? "true" : "false");
          const subtypeImage = document.createElement("img");
          subtypeImage.className = "subtype-thumb";
          subtypeImage.src = subtype.image || category.image;
          subtypeImage.alt = "";
          const subtypeCopy = document.createElement("span");
          subtypeCopy.className = "subtype-copy";
          const code = document.createElement("span");
          code.className = "subtype-code";
          code.textContent = subtype.code;
          const subtypeLabel = document.createElement("span");
          subtypeLabel.className = "subtype-label";
          subtypeLabel.textContent = subtype.label;
          subtypeCopy.append(code, subtypeLabel);
          const selectedMark = document.createElement("span");
          selectedMark.className = "subtype-state";
          selectedMark.textContent = selected ? "Saved" : "Add";
          subtypeButton.append(subtypeImage, subtypeCopy, selectedMark);
          subtypeButton.addEventListener("click", () => toggleReference(category, subtype));
          subtypeList.appendChild(subtypeButton);
        });
        block.appendChild(subtypeList);
      }
      elements.categoryList.appendChild(block);
    });
  }
  function renderBoard(page) {
    const images = page.references.length ? page.references.map((item) => item.image) : ["/assets/material-plastics.webp", "/assets/material-paper.webp", "/assets/material-metals.webp"];
    elements.boardImagePrimary.src = images[0] || "/assets/material-plastics.webp";
    elements.boardImageSecondary.src = images[1] || images[0] || "/assets/material-paper.webp";
    elements.boardImageTertiary.src = images[2] || images[1] || images[0] || "/assets/material-metals.webp";
  }
  function renderAll() {
    renderPhaseRail();
    renderNotebook();
    renderBoard(activePage());
    renderHistory();
    renderLibrary();
  }
  function turnToPhase(index) {
    if (index < 0 || index >= phases.length || index === state.currentPhase) return;
    if (turnTimer) window.clearTimeout(turnTimer);
    const direction = index > state.currentPhase ? "is-turning-forward" : "is-turning-back";
    elements.notebookSpread = elements.notebookSpread || document.getElementById("notebookSpread");
    elements.notebookSpread.classList.remove("is-turning-forward", "is-turning-back");
    void elements.notebookSpread.offsetWidth;
    elements.notebookSpread.classList.add(direction);
    const oldIndex = state.currentPhase;
    turnTimer = window.setTimeout(() => {
      state.currentPhase = index;
      saveState();
      renderAll();
      elements.notebookSpread.classList.remove("is-turning-forward", "is-turning-back");
      if (oldIndex !== index) elements.message.focus({preventScroll: true});
    }, 230);
  }
  function goToPhase(index) {
    if (index === state.currentPhase) return;
    turnToPhase(index);
  }
  function markPhaseAndAdvance() {
    if (state.currentPhase < phases.length - 1) {
      if (!phaseHasWork(state.currentPhase)) {
        elements.message.focus({preventScroll: true});
        elements.statusNote.textContent = "Add an observation or a reference before moving on. Your page is still ready.";
        return;
      }
      turnToPhase(state.currentPhase + 1);
      return;
    }
    elements.statusNote.textContent = "This note is complete as a working record. You can still return to any phase.";
  }
  function toggleReference(category, subtype) {
    const page = activePage();
    const existing = page.references.findIndex((reference) => reference.id === subtype.id);
    if (existing >= 0) page.references.splice(existing, 1);
    else page.references.push({id: subtype.id, code: subtype.code, label: subtype.label, image: subtype.image || category.image});
    page.comparison = "";
    page.comparisonSources = [];
    saveState();
    renderAll();
  }
  function setLibraryOpen(open, trigger) {
    if (open && (trigger || (window.innerWidth <= 1080 && !libraryTrigger))) {
      libraryTrigger = trigger || document.activeElement;
    }
    const modal = open && window.innerWidth <= 1080;
    elements.library.dataset.open = open ? "true" : "false";
    elements.library.setAttribute("aria-hidden", open ? "false" : "true");
    elements.library.setAttribute("aria-modal", modal ? "true" : "false");
    elements.libraryBackdrop.dataset.open = open ? "true" : "false";
    elements.libraryToggle.setAttribute("aria-expanded", open ? "true" : "false");
    libraryBackground.forEach((element) => {
      element.inert = modal;
      if (modal) element.setAttribute("aria-hidden", "true");
      else element.removeAttribute("aria-hidden");
    });
    if (modal) {
      elements.library.focus({preventScroll: true});
    } else if (!open && libraryTrigger) {
      libraryTrigger.focus({preventScroll: true});
      libraryTrigger = null;
    }
  }
  function archiveCurrentNote() {
    if (!state.pages.some((_, index) => phaseHasWork(index))) return;
    state.history = [{
      title: state.title,
      createdAt: state.createdAt,
      pages: state.pages.map((page) => validPage(page, false)),
      savedAt: new Date().toISOString()
    }, ...(state.history || [])];
  }
  function startNewNote() {
    archiveCurrentNote();
    const history = state.history || [];
    state = freshState();
    state.history = history;
    sessionId = null;
    state.sessionId = null;
    elements.globalSearch.value = "";
    elements.materialSearch.value = "";
    saveState();
    conversationGeneration += 1;
    requestPending = false;
    requestPhaseIndex = null;
    comparisonPending = false;
    comparisonPhaseIndex = null;
    lastFailedRequest = null;
    renderAll();
    elements.noteTitle.focus({preventScroll: true});
  }
  function restoreHistory(index) {
    const snapshot = state.history[index];
    if (!snapshot || !Array.isArray(snapshot.pages)) return;
    const current = {title: state.title, createdAt: state.createdAt, pages: state.pages.map((page) => validPage(page, false)), savedAt: new Date().toISOString()};
    state.title = snapshot.title || "Restored material investigation";
    state.pages = validState({pages: snapshot.pages}).pages;
    state.createdAt = validTimestamp(snapshot.createdAt) || new Date().toISOString();
    sessionId = null;
    state.sessionId = null;
    state.currentPhase = 0;
    state.history = [current, ...state.history.filter((_, itemIndex) => itemIndex !== index)];
    conversationGeneration += 1;
    lastFailedRequest = null;
    saveState();
    renderAll();
  }
  function headers() {
    const result = {"Content-Type": "application/json"};
    if (token) result.Authorization = "Bearer " + token;
    return result;
  }
  async function request(url, options) {
    const response = await fetch(url, Object.assign({}, options, {headers: headers()}));
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      elements.authGate.hidden = false;
      elements.authInput.focus();
      const error = new Error("auth_required");
      error.code = "auth_required";
      error.status = response.status;
      throw error;
    }
    if (!response.ok) {
      const error = new Error(body.error || ("Request failed (" + response.status + ")"));
      error.code = body.error || "request_failed";
      error.status = response.status;
      throw error;
    }
    return body;
  }
  async function loadModelIdentity() {
    try {
      const body = await request("/api/runtime/model");
      if (typeof body.identity === "string") configuredModelIdentity = body.identity;
      renderNotebook();
    } catch (_) {
      // The notebook remains usable with the generic provider label when the metadata route is unavailable.
    }
  }
  const SETTINGS_PROFILE_FIELDS = new Set([
    "temperature", "top_p", "top_k", "min_p", "max_tokens", "context_window",
    "timeout_seconds", "vision", "include_reasoning", "chat_template_kwargs"
  ]);
  function setSettingsNumber(id, value) {
    elements[id].value = value === undefined || value === null || value === "" ? "" : String(value);
  }
  function renderSettings(settings) {
    loadedSettings = settings;
    elements.settingsProvider.value = settings.provider || "localai";
    elements.settingsModel.value = settings.model || "auto";
    elements.settingsIdentity.textContent = settings.identity || "Not configured";
    elements.settingsLocalaiBaseUrl.value = settings.localai_base_url || "";
    elements.settingsAiEnabled.checked = Boolean(settings.ai_enabled);
    elements.settingsLocalaiTls.checked = Boolean(settings.localai_tls_verify);
    elements.settingsQualityJudges.checked = Boolean(settings.quality_judges);
    setSettingsNumber("settingsRetries", settings.model_retries);
    setSettingsNumber("settingsDiscoveryTimeout", settings.model_discovery_timeout);
    setSettingsNumber("settingsMaxTimeout", settings.max_model_timeout_seconds);
    elements.settingsTheme.value = loadTheme();
    elements.settingsApiKey.value = "";
    elements.settingsClearApiKey.checked = false;
    const keyStatus = settings.api_keys && settings.api_keys[settings.provider];
    if (keyStatus && keyStatus.configured) {
      elements.settingsKeyStatus.textContent = keyStatus.source === "encrypted"
        ? "An encrypted key is saved for this provider."
        : "A key is supplied by the server environment.";
    } else if (!settings.api_key_storage_available) {
      elements.settingsKeyStatus.textContent = "Encrypted key storage is unavailable; set HELPME_MASTER_KEY before saving a key.";
    } else {
      elements.settingsKeyStatus.textContent = "No key is saved for this provider.";
    }
    const profile = settings.profile && typeof settings.profile === "object" ? settings.profile : {};
    elements.settingsVision.checked = profile.vision === true;
    elements.settingsIncludeReasoning.checked = profile.include_reasoning === true;
    setSettingsNumber("settingsTemperature", profile.temperature);
    setSettingsNumber("settingsTopP", profile.top_p);
    setSettingsNumber("settingsTopK", profile.top_k);
    setSettingsNumber("settingsMinP", profile.min_p);
    setSettingsNumber("settingsMaxTokens", profile.max_tokens);
    setSettingsNumber("settingsContextWindow", profile.context_window);
    setSettingsNumber("settingsTimeout", profile.timeout_seconds);
    const template = profile.chat_template_kwargs && typeof profile.chat_template_kwargs === "object" && !Array.isArray(profile.chat_template_kwargs)
      ? Object.assign({}, profile.chat_template_kwargs)
      : {};
    elements.settingsReasoningStrength.value = typeof template.reasoning_strength === "string" ? template.reasoning_strength : "";
    delete template.reasoning_strength;
    const advanced = Object.fromEntries(Object.entries(profile).filter(([key]) => !SETTINGS_PROFILE_FIELDS.has(key)));
    if (Object.keys(template).length) advanced.chat_template_kwargs = template;
    elements.settingsAdvancedOptions.value = Object.keys(advanced).length ? JSON.stringify(advanced, null, 2) : "";
  }
  function settingsStatus(text, kind) {
    elements.settingsStatus.textContent = text || "";
    elements.settingsStatus.dataset.kind = kind || "";
  }
  async function loadSettings() {
    if (!elements.settingsForm) return;
    settingsStatus("Loading saved settings...", "busy");
    try {
      const body = await request("/api/settings");
      renderSettings(body);
      settingsStatus("Settings loaded.", "");
    } catch (error) {
      settingsStatus(error && error.code === "auth_required" ? "Enter the connection key in the notebook before opening settings." : (error.message || "Settings could not be loaded."), "error");
    }
  }
  function numericSetting(id) {
    const raw = elements[id].value.trim();
    if (!raw) return undefined;
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new Error("Model option must be a number.");
    return value;
  }
  function buildSettingsProfile() {
    let advanced = {};
    const rawAdvanced = elements.settingsAdvancedOptions.value.trim();
    if (rawAdvanced) {
      try { advanced = JSON.parse(rawAdvanced); } catch (_) { throw new Error("Advanced request options must be valid JSON."); }
      if (!advanced || typeof advanced !== "object" || Array.isArray(advanced)) throw new Error("Advanced request options must be a JSON object.");
    }
    const profile = Object.assign({}, advanced);
    const numericFields = {
      temperature: "settingsTemperature",
      top_p: "settingsTopP",
      top_k: "settingsTopK",
      min_p: "settingsMinP",
      max_tokens: "settingsMaxTokens",
      context_window: "settingsContextWindow",
      timeout_seconds: "settingsTimeout"
    };
    Object.entries(numericFields).forEach(([key, id]) => {
      const value = numericSetting(id);
      if (value === undefined) delete profile[key];
      else profile[key] = value;
    });
    profile.vision = elements.settingsVision.checked;
    profile.include_reasoning = elements.settingsIncludeReasoning.checked;
    const template = profile.chat_template_kwargs && typeof profile.chat_template_kwargs === "object" && !Array.isArray(profile.chat_template_kwargs)
      ? Object.assign({}, profile.chat_template_kwargs)
      : {};
    const reasoningStrength = elements.settingsReasoningStrength.value.trim();
    if (reasoningStrength) template.reasoning_strength = reasoningStrength;
    else delete template.reasoning_strength;
    if (Object.keys(template).length) profile.chat_template_kwargs = template;
    else delete profile.chat_template_kwargs;
    return profile;
  }
  async function saveSettings(event) {
    event.preventDefault();
    let profile;
    try { profile = buildSettingsProfile(); } catch (error) {
      settingsStatus(error.message || "Check the model options.", "error");
      return;
    }
    const payload = {
      provider: elements.settingsProvider.value,
      model: elements.settingsModel.value.trim(),
      localai_base_url: elements.settingsLocalaiBaseUrl.value.trim(),
      ai_enabled: elements.settingsAiEnabled.checked,
      localai_tls_verify: elements.settingsLocalaiTls.checked,
      quality_judges: elements.settingsQualityJudges.checked,
      model_retries: Number(elements.settingsRetries.value),
      model_discovery_timeout: Number(elements.settingsDiscoveryTimeout.value),
      max_model_timeout_seconds: Number(elements.settingsMaxTimeout.value),
      profile
    };
    const apiKey = elements.settingsApiKey.value;
    if (apiKey) payload.api_key = apiKey;
    if (elements.settingsClearApiKey.checked) payload.clear_api_key = true;
    elements.saveSettings.disabled = true;
    settingsStatus("Saving settings...", "busy");
    try {
      const body = await request("/api/settings", {method: "POST", body: JSON.stringify(payload)});
      const saved = body.settings || body;
      renderSettings(saved);
      configuredModelIdentity = saved.identity || configuredModelIdentity;
      setTheme(elements.settingsTheme.value);
      settingsStatus("Saved. Start a new conversation to use provider or model changes.", "success");
      renderNotebook();
    } catch (error) {
      settingsStatus(error.message || "Settings could not be saved.", "error");
    } finally {
      elements.saveSettings.disabled = false;
    }
  }
  async function streamRequest(url, options, onDelta) {
    const response = await fetch(url, Object.assign({}, options, {headers: headers()}));
    if (response.status === 401) {
      elements.authGate.hidden = false;
      elements.authInput.focus();
      const error = new Error("auth_required");
      error.code = "auth_required";
      error.status = response.status;
      throw error;
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const error = new Error(body.error || ("Request failed (" + response.status + ")"));
      error.code = body.error || "request_failed";
      error.status = response.status;
      throw error;
    }
    if (!response.body) throw Object.assign(new Error("stream_unavailable"), {code: "stream_unavailable"});
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let complete = null;
    const dispatch = (rawEvent) => {
      let eventName = "message";
      const dataLines = [];
      rawEvent.split("\n").forEach((line) => {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      });
      if (!dataLines.length) return;
      const payload = JSON.parse(dataLines.join("\n"));
      if (eventName === "delta" && payload.text) onDelta(payload.text);
      if (eventName === "complete") complete = payload;
      if (eventName === "error") {
        const error = new Error(payload.error || "stream_failed");
        error.code = payload.error || "stream_failed";
        throw error;
      }
    };
    while (true) {
      const result = await reader.read();
      buffer += decoder.decode(result.value || new Uint8Array(), {stream: !result.done});
      buffer = buffer.replace(/\r\n/g, "\n");
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      events.forEach(dispatch);
      if (result.done) break;
    }
    if (buffer.trim()) dispatch(buffer);
    if (!complete) throw Object.assign(new Error("stream_incomplete"), {code: "stream_incomplete"});
    return complete;
  }
  function showConnectionError(error, kind, phaseIndex, text) {
    requestPending = false;
    requestPhaseIndex = null;
    comparisonPending = false;
    comparisonPhaseIndex = null;
    if (error && error.code === "auth_required") {
      lastFailedRequest = null;
      renderNotebook();
      return;
    }
    lastFailedRequest = {kind, phaseIndex, text: text || ""};
    renderNotebook();
  }
  async function createSession(force = false) {
    if (force) {
      sessionId = null;
      state.sessionId = null;
    }
    if (starting || sessionId) return sessionId;
    starting = true;
    elements.send.disabled = true;
    try {
      const body = await request("/api/sessions", {method: "POST", body: "{}"});
      sessionId = body.session_id;
      configuredModelIdentity = typeof body.model === "string" ? body.model : configuredModelIdentity;
      state.sessionId = sessionId;
      saveState();
      elements.authGate.hidden = true;
      return sessionId;
    } catch (error) {
      if (error && error.code === "auth_required") {
        elements.authError.hidden = false;
        elements.authError.textContent = "That key was not accepted. Check it and try again.";
      }
      return null;
    } finally {
      starting = false;
      elements.send.disabled = false;
    }
  }
  async function sendAssistantMessage(message, onDelta, images = []) {
    let activeSessionId = await createSession();
    if (!activeSessionId) throw Object.assign(new Error("assistant_unavailable"), {code: "assistant_unavailable"});
    const payload = {message};
    if (images.length) payload.images = images;
    const send = (id, onDelta) => streamRequest("/api/sessions/" + encodeURIComponent(id) + "/message/stream", {
      method: "POST",
      body: JSON.stringify(payload)
    }, onDelta);
    try {
      return await send(activeSessionId, onDelta);
    } catch (error) {
      if (error && error.code === "session_not_found") {
        activeSessionId = await createSession(true);
        if (!activeSessionId) throw error;
        return send(activeSessionId, onDelta);
      }
      if (error && (error.status === 404 || error.status === 405 || error.code === "stream_unavailable")) {
        return request("/api/sessions/" + encodeURIComponent(activeSessionId) + "/message", {
          method: "POST",
          body: JSON.stringify(payload)
        });
      }
      throw error;
    }
  }
  async function sendObservationRequest(phaseIndex, text) {
    const requestGeneration = conversationGeneration;
    requestPending = true;
    requestPhaseIndex = phaseIndex;
    lastFailedRequest = null;
    renderNotebook();
    const targetPage = state.pages[phaseIndex];
    try {
      const images = await modelImagesForPage(targetPage);
      const prompt = [
        "Respond to the latest user observation naturally while using the attached image(s) and every saved detail on this page.",
        "Latest observation:\n" + text,
        comparisonPrompt(targetPage, phases[phaseIndex], state.title)
      ].join("\n\n");
      const body = await sendAssistantMessage(prompt, (delta) => {
        if (requestGeneration !== conversationGeneration) return;
        targetPage.reply += delta;
        renderRead(targetPage, phases[phaseIndex]);
      }, images);
      if (requestGeneration !== conversationGeneration) return;
      const assistantAvailable = !(body.data && body.data.ai_used === false) && !body.error && !isAssistantFailureText(body.text);
      targetPage.reply = assistantAvailable ? withAssistantVerificationNotice(body.text || "The observation is saved. Add another detail when you are ready.") : "";
      targetPage.sources = assistantAvailable && body.data && Array.isArray(body.data.sources) ? body.data.sources : [];
      saveState();
      lastFailedRequest = assistantAvailable ? null : {kind: "observation", phaseIndex, text};
    } catch (error) {
      if (requestGeneration !== conversationGeneration) return;
      showConnectionError(error, "observation", phaseIndex, text);
    } finally {
      if (requestGeneration === conversationGeneration) {
        requestPending = false;
        requestPhaseIndex = null;
        renderAll();
        elements.message.focus({preventScroll: true});
      }
    }
  }
  async function saveObservation(event) {
    event.preventDefault();
    const text = elements.message.value.trim();
    if (!text || requestPending || comparisonPending) return;
    const phaseIndex = state.currentPhase;
    const page = state.pages[phaseIndex];
    page.observations.push(text);
    page.draft = "";
    page.reply = "";
    page.sources = [];
    page.comparison = "";
    page.comparisonSources = [];
    saveState();
    requestPending = true;
    requestPhaseIndex = phaseIndex;
    renderAll();
    await sendObservationRequest(phaseIndex, text);
  }
  function comparisonPrompt(page, phase, title) {
    const observations = page.observations.map((item, index) => (index + 1) + ". " + item).join("\n") || "None recorded.";
    const references = page.references.map((item) => item.code + " — " + item.label).join(", ") || "None selected.";
    const evidence = page.evidence || blankEvidence();
    const sampleFormLabels = {
      whole: "whole piece",
      flakes: "flakes or chips",
      granules: "granules or pellets",
      powder: "powder or dust",
      mixed: "mixed pieces",
      closed: "a closed container"
    };
    const sampleForm = sampleFormLabels[evidence.form] || "not provided";
    const difficultForm = ["granules", "powder", "mixed", "closed"].includes(evidence.form);
    const photoNote = evidence.photos.length
      ? evidence.photos.length + " original user-provided photo(s) are attached to this request. Inspect every available visual detail at the supplied resolution, including surfaces, texture, geometry, labels, attachments, damage, contamination cues, and differences between pieces."
      : "No user-provided sample photo is attached.";
    return [
      "Please compare this material investigation in ordinary language.",
      "The phase is " + phase.label + ".",
      "Investigation title: " + (title || "New material note") + ".",
      "Current unsaved note: " + (page.draft || "None") + ".",
      "User notes (treat as supplied details, not verified fact):\n" + observations,
      "Selected library examples (used or worked-on material examples only): " + references,
      "Sample form: " + sampleForm + ".",
      "Sample condition: " + (evidence.condition || "not provided") + ".",
      "Sample origin: " + (evidence.origin || "not provided") + ".",
      "What the user wants compared: " + (evidence.details || "not provided") + ".",
      photoNote,
      "Attachments are ordered as the original user sample photo(s), followed by any selected library example image(s). Use the sample first; library images are illustrative context, not proof of identity.",
      "Use the attached image(s) and every supplied page detail together. Separate direct visual observations from hypotheses. Do not ignore the image, and do not claim a visual feature that is not present.",
      "Use every relevant configured retrieval, reference, machine, and quality check available to improve the comparison, but do not add irrelevant context just to make the answer longer.",
      "Use everyday English. Say notes, library examples, first read, and next simple check. Avoid technical labels unless the user uses them first.",
      "Explain what fits the examples, what the current details cannot tell us, what might change the first read, and the next simple check.",
      difficultForm
        ? "This is a difficult visual case. Inspect the photo closely, describe specific visible features before interpreting them, do not choose one material as the answer from appearance alone, and treat a mixed sample as mixed. Use the headings What I can see, What this photo cannot tell us, What might change this, and Next simple check."
        : "Use the headings What fits, What this does not tell us, What might change this, and Next simple check.",
      "If the photo or notes are not enough, use the plain result label Unclear from photo and explain what extra detail would help.",
      "You may inspect the supplied image, but do not claim confirmed identity, test results, composition, grade, recyclability, legal status, safety clearance, price, yield, or process suitability. Name material types only as possibilities and keep uncertainty visible. Do not invent sources or measurements."
    ].join("\n\n");
  }
  async function sendComparisonRequest(phaseIndex) {
    const requestGeneration = conversationGeneration;
    comparisonPending = true;
    comparisonPhaseIndex = phaseIndex;
    lastFailedRequest = null;
    renderNotebook();
    const targetPage = state.pages[phaseIndex];
    try {
      const images = await modelImagesForPage(targetPage);
      const body = await sendAssistantMessage(comparisonPrompt(targetPage, phases[phaseIndex], state.title), (delta) => {
        if (requestGeneration !== conversationGeneration) return;
        targetPage.comparison += delta;
        renderRead(targetPage, phases[phaseIndex]);
      }, images);
      if (requestGeneration !== conversationGeneration) return;
      const assistantAvailable = !(body.data && body.data.ai_used === false) && !body.error && !isAssistantFailureText(body.text);
      targetPage.comparison = assistantAvailable ? withAssistantVerificationNotice(body.text || "Your notes are saved. Add another detail or library example when you are ready.") : "";
      targetPage.comparisonSources = assistantAvailable && body.data && Array.isArray(body.data.sources) ? body.data.sources : [];
      saveState();
      lastFailedRequest = assistantAvailable ? null : {kind: "comparison", phaseIndex};
    } catch (error) {
      if (requestGeneration !== conversationGeneration) return;
      showConnectionError(error, "comparison", phaseIndex);
    } finally {
      if (requestGeneration === conversationGeneration) {
        comparisonPending = false;
        comparisonPhaseIndex = null;
        renderAll();
        elements.compareEvidence.focus({preventScroll: true});
      }
    }
  }
  function compareEvidenceWithAssistant() {
    if (comparisonPending || requestPending) return;
    const phaseIndex = state.currentPhase;
    const page = state.pages[phaseIndex];
    if (!(
      page.observations.length || page.references.length || page.evidence.photos.length || page.evidence.condition || page.evidence.origin || page.evidence.details
    )) return;
    void sendComparisonRequest(phaseIndex);
  }
  function retryLastRequest() {
    if (!lastFailedRequest || requestPending || comparisonPending) return;
    const failed = lastFailedRequest;
    lastFailedRequest = null;
    if (failed.kind === "observation") {
      const page = state.pages[failed.phaseIndex];
      if (!page || !failed.text) return;
      page.reply = "";
      page.sources = [];
      void sendObservationRequest(failed.phaseIndex, failed.text);
      return;
    }
    if (state.pages[failed.phaseIndex]) void sendComparisonRequest(failed.phaseIndex);
  }
  function prepareEvidencePhoto(file) {
    if (!file || !SUPPORTED_VISION_IMAGE_TYPES.has(file.type.toLowerCase())) {
      return Promise.reject(new Error("Use PNG, JPEG, WebP, or GIF photos for visual analysis."));
    }
    return Promise.resolve(file.slice(0, file.size, file.type));
  }
  async function addEvidencePhotos(event) {
    const page = activePage();
    const available = Math.max(0, MAX_PHOTOS_PER_PAGE - page.evidence.photos.length);
    const files = Array.from(event.target.files || []).slice(0, available);
    if (!files.length) {
      event.target.value = "";
      return;
    }
    try {
      for (const file of files) {
        const blob = await prepareEvidencePhoto(file);
        const photo = {
          id: "photo-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7),
          name: file.name,
          type: blob.type || file.type || "image/jpeg",
          size: blob.size
        };
        await putPhoto(photo, blob);
        page.evidence.photos.push(photo);
      }
      page.comparison = "";
      page.comparisonSources = [];
      const persisted = saveState();
      renderAll();
      photoStorageError = "";
      if (persisted) elements.statusNote.textContent = "The original photo is saved here and will be sent with the next assistant comparison.";
    } catch (error) {
      photoStorageError = error.message || "The sample photo could not be saved.";
      renderNotebook();
    } finally {
      event.target.value = "";
    }
  }
  function fitNoteTitle() {
    elements.noteTitle.style.height = "0px";
    elements.noteTitle.style.height = Math.max(elements.noteTitle.scrollHeight, 1) + "px";
  }
  elements.noteTitle.addEventListener("input", () => {
    state.title = elements.noteTitle.value;
    fitNoteTitle();
    saveState();
  });
  elements.message.addEventListener("input", () => {
    activePage().draft = elements.message.value;
    saveState();
  });
  elements.message.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      elements.composer.requestSubmit();
    }
  });
  elements.composer.addEventListener("submit", saveObservation);
  elements.compareEvidence.addEventListener("click", compareEvidenceWithAssistant);
  elements.retryRequest.addEventListener("click", retryLastRequest);
  if (elements.clearDetachedPhotos) {
    elements.clearDetachedPhotos.addEventListener("click", () => {
      void clearDetachedPhotos().catch((error) => {
        photoStorageError = error.message || "Removed local photos could not be cleared.";
        renderNotebook();
      });
    });
  }
  elements.evidencePhotoInput.addEventListener("change", addEvidencePhotos);
  elements.evidenceForm.addEventListener("change", () => {
    activePage().evidence.form = elements.evidenceForm.value;
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
    renderNotebook();
  });
  elements.evidenceCondition.addEventListener("change", () => {
    activePage().evidence.condition = elements.evidenceCondition.value;
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
    renderNotebook();
  });
  elements.evidenceOrigin.addEventListener("input", () => {
    activePage().evidence.origin = elements.evidenceOrigin.value.slice(0, 140);
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
  });
  elements.evidenceDetails.addEventListener("input", () => {
    activePage().evidence.details = elements.evidenceDetails.value.slice(0, 220);
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
  });
  elements.previousPage.addEventListener("click", () => turnToPhase(state.currentPhase - 1));
  elements.nextPage.addEventListener("click", markPhaseAndAdvance);
  elements.usePrompt.addEventListener("click", () => {
    elements.message.value = phases[state.currentPhase].question + " ";
    activePage().draft = elements.message.value;
    saveState();
    elements.message.focus({preventScroll: true});
  });
  elements.libraryToggle.addEventListener("click", (event) => setLibraryOpen(true, event.currentTarget));
  elements.libraryClose.addEventListener("click", () => setLibraryOpen(false));
  elements.libraryBackdrop.addEventListener("click", () => setLibraryOpen(false));
  const libraryNav = document.querySelector('.nav-link[href="#library"]');
  if (libraryNav) {
    libraryNav.addEventListener("click", (event) => {
      event.preventDefault();
      if (window.location.hash === "#kb" || window.location.hash === "#settings") window.location.hash = "#notebook";
      setLibraryOpen(true, event.currentTarget);
    });
  }
  document.addEventListener("keydown", (event) => {
    const isMobile = window.innerWidth <= 1080;
    const isOpen = elements.library.dataset.open === "true";
    if (event.key === "Escape" && isOpen && isMobile) {
      event.preventDefault();
      setLibraryOpen(false);
      return;
    }
    if (event.key !== "Tab" || !isOpen || !isMobile) return;
    const focusable = Array.from(elements.library.querySelectorAll("button, input, [href], select, textarea, [tabindex]:not([tabindex='-1'])")).filter((item) => !item.disabled && item.offsetParent !== null);
    if (!focusable.length) {
      event.preventDefault();
      elements.library.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  elements.materialSearch.addEventListener("input", () => renderLibrary());
  elements.globalSearch.addEventListener("input", () => {
    elements.materialSearch.value = elements.globalSearch.value;
    setLibraryOpen(true);
    renderLibrary();
  });
  elements.newNote.addEventListener("click", startNewNote);
  elements.themeToggle.addEventListener("click", () => setTheme(elements.body.dataset.theme === "dark" ? "light" : "dark"));
  if (elements.settingsForm) {
    elements.settingsForm.addEventListener("submit", saveSettings);
    elements.settingsProvider.addEventListener("change", () => {
      const keyStatus = loadedSettings && loadedSettings.api_keys && loadedSettings.api_keys[elements.settingsProvider.value];
      if (keyStatus && keyStatus.configured) {
        elements.settingsKeyStatus.textContent = keyStatus.source === "encrypted"
          ? "An encrypted key is saved for this provider."
          : "A key is supplied by the server environment.";
      } else if (loadedSettings && !loadedSettings.api_key_storage_available) {
        elements.settingsKeyStatus.textContent = "Encrypted key storage is unavailable; set HELPME_MASTER_KEY before saving a key.";
      } else {
        elements.settingsKeyStatus.textContent = "No key is saved for this provider.";
      }
    });
  }
  elements.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    token = elements.authInput.value.trim();
    elements.authError.hidden = true;
    sessionId = null;
    state.sessionId = null;
    const persisted = saveState();
    elements.authGate.hidden = true;
    elements.statusNote.textContent = persisted
      ? "Connection key saved for this browser. The assistant will connect when you send an observation."
      : persistenceError;
  });
  window.addEventListener("online", renderNotebook);
  window.addEventListener("offline", renderNotebook);
  window.addEventListener("hashchange", () => {
    if (window.location.hash === "#settings") void loadSettings();
  });

  setTheme(loadTheme());
  renderAll();
  if (window.innerWidth <= 1080) setLibraryOpen(false);
  void migrateLegacyPhotos().then(refreshDetachedPhotoStatus);
  void loadModelIdentity();
  if (window.location.hash === "#settings") void loadSettings();
})();

(() => {
  const KB_TOKEN_KEY = "helpme.green.kb.token";
  const notebook = document.getElementById("notebook");
  const settingsView = document.getElementById("settingsView");
  const kbView = document.getElementById("kbView");
  if (!notebook || !kbView || !settingsView) return;

  let kbToken = "";
  try { kbToken = localStorage.getItem(KB_TOKEN_KEY) || ""; } catch (_) {}

  const els = {
    uploadToggle: document.getElementById("kbUploadToggle"),
    auth: document.getElementById("kbAuth"),
    authForm: document.getElementById("kbAuthForm"),
    token: document.getElementById("kbToken"),
    authError: document.getElementById("kbAuthError"),
    search: document.getElementById("kbSearch"),
    filter: document.getElementById("kbFilter"),
    refresh: document.getElementById("kbRefresh"),
    status: document.getElementById("kbStatus"),
    tableBody: document.getElementById("kbTableBody"),
    uploadPanel: document.getElementById("kbUploadPanel"),
    uploadForm: document.getElementById("kbUploadForm"),
    fileInput: document.getElementById("kbFileInput"),
    uploadTitle: document.getElementById("kbUploadTitle"),
    uploadFamilies: document.getElementById("kbUploadFamilies"),
    uploadStatus: document.getElementById("kbUploadStatus"),
    detail: document.getElementById("kbDetail"),
    tabDocs: document.getElementById("kbTabDocs"),
    tabJobs: document.getElementById("kbTabJobs"),
    jobsPanel: document.getElementById("kbJobs"),
    docsPanel: document.getElementById("kbDocs"),
    jobsBody: document.getElementById("kbJobsBody")
  };

  function setStatus(text, kind) {
    els.status.textContent = text || "";
    els.status.dataset.kind = kind || "";
  }

  async function kbFetch(url, options) {
    const headers = Object.assign({}, (options && options.headers) || {});
    if (kbToken) headers.Authorization = "Bearer " + kbToken;
    let response;
    try {
      response = await fetch(url, Object.assign({}, options, {headers}));
    } catch (_) {
      const error = new Error("The knowledge base is unreachable right now.");
      error.code = "network";
      throw error;
    }
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      els.auth.hidden = false;
      els.token.focus();
      const error = new Error("Operator authorization is required.");
      error.code = "unauthorized";
      error.status = 401;
      throw error;
    }
    if (response.status === 403) {
      const code = body.error && body.error.code ? body.error.code : "forbidden";
      if (code === "kb_disabled") setStatus("The knowledge base console is disabled on this server.", "error");
      if (code === "kb_operator_unconfigured") setStatus("No operator key is configured on this server; access is refused.", "error");
      const error = new Error((body.error && body.error.message) || "Access refused.");
      error.code = code;
      error.status = 403;
      throw error;
    }
    if (!response.ok) {
      const error = new Error((body.error && body.error.message) || ("Request failed (" + response.status + ")"));
      error.code = body.error && body.error.code ? body.error.code : "request_failed";
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function kbErrorText(error) {
    return error && error.message ? error.message : "The knowledge base could not complete the request.";
  }

  function navActive(hash) {
    document.querySelectorAll(".primary-nav .nav-link").forEach((link) => {
      const href = link.getAttribute("href") || "";
      if (href === "#kb") link.classList.toggle("active", hash === "#kb");
      if (href === "#settings") link.classList.toggle("active", hash === "#settings");
      if (href === "#notebook") link.classList.toggle("active", hash !== "#kb" && hash !== "#settings" && hash !== "#library");
    });
  }

  async function kbRoute() {
    const hash = location.hash || "#notebook";
    const kbActive = hash === "#kb";
    const settingsActive = hash === "#settings";
    notebook.hidden = kbActive || settingsActive;
    settingsView.hidden = !settingsActive;
    kbView.hidden = !kbActive;
    document.title = kbActive
      ? "helpme.green — Knowledge base"
      : settingsActive
        ? "helpme.green — Settings"
        : "helpme.green — Lab Notebook";
    navActive(hash);
    if (kbActive) {
      await kbLoad();
    }
  }

  async function kbLoad() {
    els.auth.hidden = true;
    els.authError.hidden = true;
    setStatus("Loading knowledge base...", "busy");
    try {
      await kbFetch("/api/kb/capabilities");
      setStatus("", "");
      await Promise.all([loadDocuments(), loadJobs()]);
    } catch (error) {
      if (error && error.code === "unauthorized") {
        setStatus("", "");
      } else if (!(error && error.code === "kb_disabled") && !(error && error.code === "kb_operator_unconfigured")) {
        setStatus(kbErrorText(error), "error");
      }
    }
  }

  function filterParams() {
    const filter = els.filter.value;
    const params = new URLSearchParams();
    if (filter === "review") {
      params.set("origin", "user-upload");
      params.set("status", "review");
    } else if (filter === "manifest") {
      params.set("origin", "manifest");
    } else if (filter === "user-upload") {
      params.set("origin", "user-upload");
    }
    if (els.search.value.trim()) params.set("q", els.search.value.trim());
    params.set("limit", "200");
    return params.toString();
  }

  function textCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value == null ? "" : String(value);
    return cell;
  }

  async function loadDocuments() {
    try {
      const body = await kbFetch("/api/kb/documents?" + filterParams());
      const items = Array.isArray(body.items) ? body.items : [];
      els.tableBody.replaceChildren();
      if (!items.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 7;
        cell.textContent = "No documents match this view yet.";
        row.appendChild(cell);
        els.tableBody.appendChild(row);
        return;
      }
      items.forEach((item) => {
        const row = document.createElement("tr");
        row.tabIndex = 0;
        row.setAttribute("role", "button");
        row.setAttribute("aria-label", "Open document " + (item.title || item.documentId));
        const title = document.createElement("td");
        title.textContent = item.title || item.documentId || "";
        const origin = textCell(item.origin === "user-upload" ? "User upload" : "Manifest");
        const status = textCell(item.sourceStatus);
        const extraction = textCell(item.extractionStatus);
        const family = textCell(Array.isArray(item.materialFamilies) ? item.materialFamilies.join(", ") : "");
        const chunks = textCell(item.chunkCount);
        const updated = textCell(item.fetchedAt ? new Date(item.fetchedAt).toLocaleString() : "");
        row.append(title, origin, status, extraction, family, chunks, updated);
        row.addEventListener("click", () => openDetail(item.documentId));
        row.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDetail(item.documentId); }
        });
        els.tableBody.appendChild(row);
      });
      setStatus("", "");
    } catch (error) {
      if (!(error && (error.code === "unauthorized" || error.code === "kb_disabled" || error.code === "kb_operator_unconfigured"))) {
        setStatus(kbErrorText(error), "error");
      }
    }
  }

  async function loadJobs() {
    try {
      const body = await kbFetch("/api/kb/jobs?limit=200");
      const jobs = Array.isArray(body.jobs) ? body.jobs : [];
      els.jobsBody.replaceChildren();
      if (!jobs.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 5;
        cell.textContent = "No jobs recorded.";
        row.appendChild(cell);
        els.jobsBody.appendChild(row);
        return;
      }
      jobs.forEach((job) => {
        const row = document.createElement("tr");
        const id = document.createElement("td");
        id.textContent = job.jobId || "";
        const kind = textCell(job.kind);
        const status = textCell(job.status);
        const attempts = textCell(job.attempts);
        const updated = textCell(job.updatedAt ? new Date(job.updatedAt).toLocaleString() : "");
        row.append(id, kind, status, attempts, updated);
        els.jobsBody.appendChild(row);
      });
    } catch (error) {
      if (!(error && (error.code === "unauthorized" || error.code === "kb_disabled" || error.code === "kb_operator_unconfigured"))) {
        setStatus(kbErrorText(error), "error");
      }
    }
  }

  function actionButton(label, kind, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.className = "kb-action kb-action-" + kind;
    button.addEventListener("click", onClick);
    return button;
  }

  async function openDetail(documentId) {
    els.detail.hidden = false;
    els.detail.replaceChildren();
    els.detail.appendChild(heading("Document detail"));
    const busy = document.createElement("p");
    busy.textContent = "Loading detail...";
    els.detail.appendChild(busy);
    let detail;
    try {
      detail = await kbFetch("/api/kb/documents/" + encodeURIComponent(documentId));
    } catch (error) {
      busy.textContent = kbErrorText(error);
      return;
    }
    els.detail.replaceChildren();
    els.detail.appendChild(heading(detail.title || documentId));
    const definition = document.createElement("dl");
    definition.className = "kb-definition";
    const fields = [
      ["Document", detail.documentId], ["Source", detail.sourceId], ["Origin", detail.origin === "user-upload" ? "User upload" : "Manifest"],
      ["Status", detail.sourceStatus], ["Extraction", detail.extractionStatus], ["Publisher", detail.publisher || "—"],
      ["Material families", (detail.materialFamilies || []).join(", ") || "—"], ["Jurisdiction", detail.jurisdiction || "—"],
      ["Raw hash", (detail.contentSha256 || "—")], ["Metadata origin", detail.metadataOrigin || "—"],
      ["Review note", detail.reviewNote || "—"], ["Limitations", detail.limitations || "—"]
    ];
    fields.forEach(([label, value]) => {
      const term = document.createElement("dt");
      term.textContent = label;
      const description = document.createElement("dd");
      description.textContent = value == null ? "" : String(value);
      definition.append(term, description);
    });
    els.detail.appendChild(definition);

    const previewHeading = heading("Preview");
    els.detail.appendChild(previewHeading);
    const preview = document.createElement("pre");
    preview.className = "kb-preview";
    preview.textContent = detail.preview || "";
    els.detail.appendChild(preview);

    if (detail.origin === "user-upload" && (detail.sourceStatus === "review" || detail.sourceStatus === "active")) {
      const actions = document.createElement("div");
      actions.className = "kb-actions";
      const explanation = document.createElement("p");
      explanation.textContent = "Approval makes this document eligible for relevant assistant context. It remains labelled as user-supplied and not independently verified.";
      actions.appendChild(explanation);
      actions.appendChild(actionButton("Approve", "approve", async () => {
        try {
          await kbFetch("/api/kb/uploads/" + encodeURIComponent(detail.uploadIdForReview || await findUploadId(documentId)) + "/approve", {method: "POST", body: "{}"});
          setStatus("Document approved.", "success");
          await loadDocuments();
        } catch (error) { setStatus(kbErrorText(error), "error"); }
      }));
      actions.appendChild(actionButton("Quarantine", "quarantine", async () => {
        try {
          await kbFetch("/api/kb/uploads/" + encodeURIComponent(detail.uploadIdForReview || await findUploadId(documentId)) + "/quarantine", {method: "POST", body: "{}"});
          setStatus("Document quarantined.", "success");
          await loadDocuments();
        } catch (error) { setStatus(kbErrorText(error), "error"); }
      }));
      els.detail.appendChild(actions);
    }

    const relatedHeading = heading("Related references");
    els.detail.appendChild(relatedHeading);
    const relatedList = document.createElement("ul");
    relatedList.className = "kb-related";
    try {
      const related = await kbFetch("/api/kb/documents/" + encodeURIComponent(documentId) + "/related");
      const refs = Array.isArray(related.related) ? related.related : [];
      if (!refs.length) {
        const empty = document.createElement("li");
        empty.textContent = "No related references.";
        relatedList.appendChild(empty);
      } else {
        refs.forEach((ref) => {
          const item = document.createElement("li");
          item.textContent = ref.edgeType + " → " + (ref.label || ref.nodeId) + (ref.reasonDetail ? " (" + ref.reasonDetail + ")" : "");
          relatedList.appendChild(item);
        });
      }
    } catch (error) {
      const failed = document.createElement("li");
      failed.textContent = kbErrorText(error);
      relatedList.appendChild(failed);
    }
    els.detail.appendChild(relatedList);
  }

  async function findUploadId(documentId) {
    try {
      const body = await kbFetch("/api/kb/uploads?limit=200");
      const uploads = Array.isArray(body.uploads) ? body.uploads : [];
      const match = uploads.find((upload) => upload.documentId === documentId);
      return match ? match.uploadId : "";
    } catch (_) {
      return "";
    }
  }

  function heading(text) {
    const h = document.createElement("h2");
    h.className = "kb-section-title";
    h.textContent = text;
    return h;
  }

  async function submitUpload(event) {
    event.preventDefault();
    const files = Array.from(els.fileInput.files || []);
    if (!files.length) {
      els.uploadStatus.textContent = "Choose at least one reference file.";
      return;
    }
    const form = new FormData();
    files.slice(0, 10).forEach((file) => form.append("files", file, file.name));
    if (els.uploadTitle.value.trim()) form.append("title", els.uploadTitle.value.trim());
    if (els.uploadFamilies.value.trim()) form.append("materialFamilies", els.uploadFamilies.value.trim());
    els.uploadStatus.textContent = "Uploading for review...";
    try {
      const body = await kbFetch("/api/kb/uploads", {method: "POST", body: form});
      const uploads = Array.isArray(body.uploads) ? body.uploads : [];
      const lines = uploads.map((upload) => upload.filename + ": " + upload.status + (upload.errorDetail ? " — " + upload.errorDetail : ""));
      els.uploadStatus.textContent = lines.join(" · ") || "Upload queued.";
      els.fileInput.value = "";
      els.uploadTitle.value = "";
      els.uploadFamilies.value = "";
      await loadDocuments();
      await loadJobs();
    } catch (error) {
      els.uploadStatus.textContent = kbErrorText(error);
    }
  }

  function switchTab(which) {
    const docs = which === "docs";
    els.docsPanel.hidden = !docs;
    els.jobsPanel.hidden = docs;
    els.tabDocs.setAttribute("aria-selected", docs ? "true" : "false");
    els.tabJobs.setAttribute("aria-selected", docs ? "false" : "true");
    if (!docs) loadJobs();
  }

  els.authForm.addEventListener("submit", (event) => {
    event.preventDefault();
    kbToken = els.token.value.trim();
    els.authError.hidden = true;
    try { localStorage.setItem(KB_TOKEN_KEY, kbToken); } catch (_) {}
    void kbLoad();
  });
  els.uploadToggle.addEventListener("click", () => {
    els.uploadPanel.hidden = !els.uploadPanel.hidden;
  });
  els.uploadForm.addEventListener("submit", submitUpload);
  els.search.addEventListener("input", () => { if (!kbView.hidden) loadDocuments(); });
  els.filter.addEventListener("change", () => { if (!kbView.hidden) loadDocuments(); });
  els.refresh.addEventListener("click", () => { if (!kbView.hidden) { void loadDocuments(); void loadJobs(); } });
  els.tabDocs.addEventListener("click", () => switchTab("docs"));
  els.tabJobs.addEventListener("click", () => switchTab("jobs"));

  window.addEventListener("hashchange", () => { void kbRoute(); });
  void kbRoute();
})();
