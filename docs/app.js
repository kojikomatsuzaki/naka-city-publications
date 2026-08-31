"use strict";

/* ==========================================
   Application state
========================================== */

const applicationState = {
  dataset: null,
  searchTerm: "",
  publicationNumber: "all",
  volume: "all",
  uncertainOnly: false,
};

const elements = {
  publicationCount: document.querySelector("#publication-count"),
  entryCount: document.querySelector("#entry-count"),
  uncertainCount: document.querySelector("#uncertain-count"),
  datasetVersion: document.querySelector("#dataset-version"),
  resultSummary: document.querySelector("#result-summary"),
  searchForm: document.querySelector("#search-form"),
  searchInput: document.querySelector("#search-input"),
  publicationFilter: document.querySelector("#publication-filter"),
  volumeFilter: document.querySelector("#volume-filter"),
  uncertainFilter: document.querySelector("#uncertain-filter"),
  resetButton: document.querySelector("#reset-button"),
  results: document.querySelector("#results"),
  emptyMessage: document.querySelector("#empty-message"),
};


/* ==========================================
   Small display helpers
========================================== */

function displayText(value) {
  return value ?? "";
}

function normalizedSearchText(value) {
  return displayText(value).normalize("NFKC").toLocaleLowerCase("ja");
}

function headingText(entry) {
  if (entry.heading_level === "chapter") return entry.chapter;
  if (entry.heading_level === "section") return entry.section;
  return entry.item;
}

function pageText(entry) {
  if (entry.start_page !== null) return `p. ${entry.start_page}`;
  if (entry.page_reference.status === "parent_only") {
    return `親見出し p. ${entry.page_reference.parent_start_page}`;
  }
  return "ページ記載なし";
}

function contextText(entry) {
  const contextParts = [];
  if (entry.heading_level === "section" && entry.chapter) contextParts.push(entry.chapter);
  if (entry.heading_level === "item") {
    if (entry.chapter) contextParts.push(entry.chapter);
    if (entry.section) contextParts.push(entry.section);
  }
  return contextParts.join(" › ");
}

function entrySearchText(publication, entry) {
  return normalizedSearchText([
    publication.publication_number,
    publication.title,
    entry.volume,
    entry.chapter,
    entry.section,
    entry.item,
    entry.start_page,
    entry.verification?.note,
  ].join(" "));
}


/* ==========================================
   Filter options
========================================== */

function addOption(selectElement, value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  selectElement.append(option);
}

function populatePublicationOptions() {
  for (const document of applicationState.dataset.publications) {
    const publication = document.publication;
    addOption(
      elements.publicationFilter,
      publication.publication_number,
      `No${publication.publication_number}　${publication.title}`,
    );
  }
}

function availableVolumes() {
  const volumes = new Set();
  for (const document of applicationState.dataset.publications) {
    if (
      applicationState.publicationNumber !== "all"
      && document.publication.publication_number !== applicationState.publicationNumber
    ) {
      continue;
    }
    for (const entry of document.entries) {
      if (entry.volume) volumes.add(entry.volume);
    }
  }
  return [...volumes];
}

function refreshVolumeOptions() {
  const selectedVolume = applicationState.volume;
  elements.volumeFilter.replaceChildren();
  addOption(elements.volumeFilter, "all", "すべて");
  for (const volume of availableVolumes()) addOption(elements.volumeFilter, volume, volume);

  const selectedVolumeStillExists = [...elements.volumeFilter.options]
    .some((option) => option.value === selectedVolume);
  applicationState.volume = selectedVolumeStillExists ? selectedVolume : "all";
  elements.volumeFilter.value = applicationState.volume;
}


/* ==========================================
   Filtering
========================================== */

function entryMatches(publication, entry) {
  if (
    applicationState.publicationNumber !== "all"
    && publication.publication_number !== applicationState.publicationNumber
  ) {
    return false;
  }

  if (applicationState.volume !== "all" && entry.volume !== applicationState.volume) {
    return false;
  }

  if (applicationState.uncertainOnly && entry.verification?.status !== "uncertain") {
    return false;
  }

  const searchWords = normalizedSearchText(applicationState.searchTerm)
    .split(/\s+/)
    .filter(Boolean);
  const searchableText = entrySearchText(publication, entry);
  return searchWords.every((word) => searchableText.includes(word));
}

function filteredDocuments() {
  return applicationState.dataset.publications
    .map((document) => ({
      publication: document.publication,
      entries: document.entries.filter((entry) => entryMatches(document.publication, entry)),
    }))
    .filter((document) => document.entries.length > 0);
}


/* ==========================================
   Result rendering
========================================== */

function createTextElement(tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  return element;
}

function createEntryElement(entry) {
  const item = document.createElement("li");
  item.className = `toc-entry toc-entry--${entry.heading_level}`;
  item.dataset.entryId = entry.id;

  const headingArea = document.createElement("div");
  const heading = createTextElement("p", "toc-heading", headingText(entry));
  if (entry.verification?.status === "uncertain") {
    heading.append(createTextElement("span", "status-badge", "要確認"));
  }
  headingArea.append(heading);

  const context = contextText(entry);
  if (context) headingArea.append(createTextElement("p", "toc-context", context));
  if (entry.volume) headingArea.append(createTextElement("p", "toc-volume", `巻号：${entry.volume}`));

  item.append(headingArea);
  item.append(createTextElement("p", "toc-page", pageText(entry)));

  if (entry.verification?.note) {
    item.append(createTextElement("p", "toc-note", entry.verification.note));
  }
  return item;
}

function createPublicationCard(publicationDocument, cardIndex, filtersAreActive) {
  const card = document.createElement("details");
  card.className = "publication-card";
  card.open = filtersAreActive || cardIndex === 0;

  const summary = document.createElement("summary");
  const titleArea = document.createElement("div");
  titleArea.className = "publication-title";
  titleArea.append(
    createTextElement(
      "span",
      "publication-number",
      `No${publicationDocument.publication.publication_number}`,
    ),
    createTextElement("h3", "", publicationDocument.publication.title),
  );
  summary.append(
    titleArea,
    createTextElement("span", "publication-result-count", `${publicationDocument.entries.length.toLocaleString("ja-JP")}件`),
  );

  const content = document.createElement("div");
  content.className = "publication-content";
  const actions = document.createElement("div");
  actions.className = "publication-actions";
  const pdfLink = document.createElement("a");
  pdfLink.href = publicationDocument.publication.source_pdf_url;
  pdfLink.target = "_blank";
  pdfLink.rel = "noopener noreferrer";
  pdfLink.textContent = "参照PDFを開く";
  actions.append(pdfLink);

  const list = document.createElement("ol");
  list.className = "toc-list";
  list.append(...publicationDocument.entries.map(createEntryElement));
  content.append(actions, list);
  card.append(summary, content);
  return card;
}

function renderResults() {
  const documents = filteredDocuments();
  const matchingEntryCount = documents.reduce((sum, document) => sum + document.entries.length, 0);
  const filtersAreActive = Boolean(
    applicationState.searchTerm
    || applicationState.publicationNumber !== "all"
    || applicationState.volume !== "all"
    || applicationState.uncertainOnly,
  );

  elements.results.replaceChildren(
    ...documents.map((document, index) => createPublicationCard(document, index, filtersAreActive)),
  );
  elements.results.setAttribute("aria-busy", "false");
  elements.emptyMessage.hidden = matchingEntryCount !== 0;
  elements.resultSummary.textContent = `${matchingEntryCount.toLocaleString("ja-JP")}件を表示`;
}


/* ==========================================
   User interaction
========================================== */

function updateStateFromControls() {
  applicationState.searchTerm = elements.searchInput.value.trim();
  applicationState.publicationNumber = elements.publicationFilter.value;
  applicationState.volume = elements.volumeFilter.value;
  applicationState.uncertainOnly = elements.uncertainFilter.checked;
}

function handleFilterChange(event) {
  updateStateFromControls();
  if (event.target === elements.publicationFilter) refreshVolumeOptions();
  renderResults();
}

function handleReset() {
  window.setTimeout(() => {
    applicationState.searchTerm = "";
    applicationState.publicationNumber = "all";
    applicationState.volume = "all";
    applicationState.uncertainOnly = false;
    refreshVolumeOptions();
    renderResults();
  }, 0);
}

function connectControls() {
  elements.searchInput.addEventListener("input", handleFilterChange);
  elements.publicationFilter.addEventListener("change", handleFilterChange);
  elements.volumeFilter.addEventListener("change", handleFilterChange);
  elements.uncertainFilter.addEventListener("change", handleFilterChange);
  elements.searchForm.addEventListener("reset", handleReset);
}


/* ==========================================
   Data loading and startup
========================================== */

function displayDatasetSummary() {
  const statistics = applicationState.dataset.statistics;
  elements.publicationCount.textContent = `${statistics.publication_count.toLocaleString("ja-JP")}点`;
  elements.entryCount.textContent = `${statistics.entry_count.toLocaleString("ja-JP")}件`;
  elements.uncertainCount.textContent = `${statistics.uncertain_entry_count.toLocaleString("ja-JP")}件`;
  elements.datasetVersion.textContent = `v${applicationState.dataset.dataset_version}`;
}

function showLoadingError(error) {
  console.error(error);
  elements.results.setAttribute("aria-busy", "false");
  elements.results.replaceChildren(
    createTextElement(
      "p",
      "error-message",
      "データを読み込めませんでした。時間をおいて再読み込みするか、CSV・JSONをご利用ください。",
    ),
  );
  elements.resultSummary.textContent = "読込みエラー";
}

async function startApplication() {
  try {
    const response = await fetch("./data/naka-city-publications.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`JSONの読込みに失敗しました: ${response.status}`);
    applicationState.dataset = await response.json();
    displayDatasetSummary();
    populatePublicationOptions();
    refreshVolumeOptions();
    connectControls();
    renderResults();
  } catch (error) {
    showLoadingError(error);
  }
}

startApplication();
