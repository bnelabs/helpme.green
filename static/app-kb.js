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
