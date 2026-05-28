const state = { articles: [], query: "", filters: { type: "", topic: "", year: "" } };

const elements = {
  articles: document.querySelector("#articles"),
  totalCount: document.querySelector("#totalCount"),
  updatedAt: document.querySelector("#updatedAt"),
  resultCount: document.querySelector("#resultCount"),
  searchInput: document.querySelector("#searchInput"),
  typeFilter: document.querySelector("#typeFilter"),
  topicFilter: document.querySelector("#topicFilter"),
  yearFilter: document.querySelector("#yearFilter"),
  topicStats: document.querySelector("#topicStats"),
  queryButton: document.querySelector("#queryButton"),
  queryDialog: document.querySelector("#queryDialog"),
  queryText: document.querySelector("#queryText")
};

function escapeHtml(value = "") {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[character]);
}

function formatDate(dateString) {
  if (!dateString) return "日期未知";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return dateString;
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "long" }).format(date);
}

function compactAuthors(authors) {
  if (!authors?.length) return "Authors unavailable";
  return authors.length > 3 ? `${authors.slice(0, 3).join(", ")} et al.` : authors.join(", ");
}

function renderJournalMetrics(metrics = {}) {
  const items = [];
  if (metrics.partition) items.push(`<span><b>期刊分区</b>${escapeHtml(metrics.partition)}</span>`);
  if (metrics.score) {
    const label = metrics.scoreLabel || "分数";
    items.push(`<span><b>${escapeHtml(label)}</b>${escapeHtml(metrics.score)}</span>`);
  }
  if (metrics.source || metrics.year) {
    items.push(`<span><b>来源</b>${escapeHtml([metrics.source, metrics.year].filter(Boolean).join(" · "))}</span>`);
  }
  if (!items.length) {
    items.push("<span><b>期刊指标</b>待补充</span>");
  }
  return `<div class="journal-metrics">${items.join("")}</div>`;
}

function populateSelect(select, values) {
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  });
}

function matches(article) {
  const query = state.query.toLowerCase();
  const haystack = [
    article.title, article.abstract, article.journal, ...(article.authors || [])
  ].join(" ").toLowerCase();
  return (!query || haystack.includes(query))
    && (!state.filters.type || article.publicationTypes?.includes(state.filters.type))
    && (!state.filters.topic || article.topics?.includes(state.filters.topic))
    && (!state.filters.year || article.year === state.filters.year);
}

function renderArticles() {
  const filtered = state.articles.filter(matches);
  elements.resultCount.textContent = `显示 ${filtered.length} / ${state.articles.length} 篇`;
  if (!filtered.length) {
    elements.articles.innerHTML = '<p class="empty">没有匹配的文献，请尝试调整筛选条件。</p>';
    return;
  }
  elements.articles.innerHTML = filtered.map((article) => {
    const badges = [
      ...(article.topics || []).slice(0, 2).map((topic) => `<span class="badge">${escapeHtml(topic)}</span>`),
      ...(article.publicationTypes || []).slice(0, 1).map((type) => `<span class="badge type">${escapeHtml(type)}</span>`)
    ].join("");
    const doiLink = article.doi
      ? `<a href="https://doi.org/${encodeURIComponent(article.doi)}" target="_blank" rel="noopener">DOI ↗</a>`
      : "";
    return `
      <article class="article">
        <div class="badges">${badges}</div>
        <h3><a href="${escapeHtml(article.pubmedUrl)}" target="_blank" rel="noopener">${escapeHtml(article.title)}</a></h3>
        <p class="citation">${escapeHtml(compactAuthors(article.authors))} · <strong>${escapeHtml(article.journal)}</strong> · ${escapeHtml(article.publicationDate || article.year)} · PMID: ${escapeHtml(article.pmid)}</p>
        ${renderJournalMetrics(article.journalMetrics)}
        ${article.abstract ? `<p class="abstract">${escapeHtml(article.abstract)}</p>` : ""}
        <div class="article-links">
          <a href="${escapeHtml(article.pubmedUrl)}" target="_blank" rel="noopener">查看 PubMed ↗</a>
          ${doiLink}
        </div>
      </article>
    `;
  }).join("");
}

function renderTopicStats() {
  const counts = {};
  state.articles.forEach((article) => (article.topics || []).forEach((topic) => {
    counts[topic] = (counts[topic] || 0) + 1;
  }));
  elements.topicStats.innerHTML = Object.entries(counts)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 7)
    .map(([topic, count]) => `<button type="button" class="stat-button" data-topic="${escapeHtml(topic)}"><span>${escapeHtml(topic)}</span><b>${count}</b></button>`)
    .join("");
  elements.topicStats.addEventListener("click", (event) => {
    const button = event.target.closest("[data-topic]");
    if (!button) return;
    state.filters.topic = button.dataset.topic === state.filters.topic ? "" : button.dataset.topic;
    elements.topicFilter.value = state.filters.topic;
    document.querySelectorAll(".stat-button").forEach((item) => {
      item.classList.toggle("active", item.dataset.topic === state.filters.topic);
    });
    renderArticles();
  });
}

async function loadData() {
  try {
    const response = await fetch("data/articles.json");
    if (!response.ok) throw new Error("Data unavailable");
    const data = await response.json();
    state.articles = data.articles || [];
    elements.updatedAt.textContent = formatDate(data.updatedAt);
    elements.totalCount.textContent = String(state.articles.length);
    elements.queryText.textContent = data.query || "";
    const types = [...new Set(state.articles.flatMap((article) => article.publicationTypes || []))].sort();
    const topics = [...new Set(state.articles.flatMap((article) => article.topics || []))].sort();
    const years = [...new Set(state.articles.map((article) => article.year).filter(Boolean))].sort().reverse();
    populateSelect(elements.typeFilter, types);
    populateSelect(elements.topicFilter, topics);
    populateSelect(elements.yearFilter, years);
    renderTopicStats();
    renderArticles();
  } catch (error) {
    elements.updatedAt.textContent = "暂未生成";
    elements.articles.innerHTML = '<p class="empty">尚无文献数据。运行抓取脚本后，此处将显示最新 PubMed 英文研究。</p>';
  }
}

elements.searchInput.addEventListener("input", (event) => {
  state.query = event.target.value.trim();
  renderArticles();
});

[["type", elements.typeFilter], ["topic", elements.topicFilter], ["year", elements.yearFilter]].forEach(([filter, select]) => {
  select.addEventListener("change", (event) => {
    state.filters[filter] = event.target.value;
    renderArticles();
  });
});

elements.queryButton.addEventListener("click", () => elements.queryDialog.showModal());
loadData();
