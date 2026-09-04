const formatNumber = new Intl.NumberFormat("en-US");

const endpoints = {
  health: "/health",
  overview: "/stats/overview",
  monthlyTrends: "/stats/monthly-trends",
  questionTypes: "/stats/question-types",
  search: (query) => `/search?query=${encodeURIComponent(query)}`,
};

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function setHealth(status, ok = false) {
  const element = document.getElementById("healthStatus");
  element.textContent = status;
  element.classList.toggle("ok", ok);
  element.classList.toggle("error", !ok && status !== "Checking");
}

function renderOverview(data) {
  setText("conversationCount", formatNumber.format(data.conversation_count));
  setText("messageCount", formatNumber.format(data.message_count));
  setText("userMessageCount", formatNumber.format(data.role_counts.user ?? 0));
  setText("averageWords", data.average_user_message_words);
}

function renderMonthlyTrends(data) {
  const chart = document.getElementById("monthlyChart");
  const rows = data.monthly_user_trends ?? [];
  const maxMessages = Math.max(...rows.map((row) => row.user_messages), 1);

  chart.replaceChildren(
    ...rows.map((row) => {
      const item = document.createElement("div");
      const bar = document.createElement("div");
      const label = document.createElement("div");
      const height = Math.max((row.user_messages / maxMessages) * 220, 4);

      item.className = "barItem";
      bar.className = "bar";
      bar.style.height = `${height}px`;
      bar.title = `${row.month}: ${formatNumber.format(row.user_messages)} user messages`;
      label.className = "barLabel";
      label.textContent = row.month;

      item.append(bar, label);
      return item;
    }),
  );
}

function renderRankList(containerId, entries, valueLabel = "count") {
  const container = document.getElementById(containerId);
  const max = Math.max(...entries.map((entry) => entry[1]), 1);

  container.replaceChildren(
    ...entries.map(([name, value]) => {
      const row = document.createElement("div");
      const label = document.createElement("div");
      const count = document.createElement("div");
      const meter = document.createElement("div");
      const fill = document.createElement("span");

      row.className = "rankRow";
      label.className = "rankName";
      count.className = "rankValue";
      meter.className = "meter";

      label.textContent = name;
      count.textContent = `${formatNumber.format(value)} ${valueLabel}`;
      fill.style.width = `${Math.max((value / max) * 100, 2)}%`;
      meter.append(fill);
      row.append(label, count, meter);
      return row;
    }),
  );
}

function renderQuestionTypes(data) {
  renderRankList("questionTypes", Object.entries(data.question_type_counts ?? {}), "messages");
}

function renderSearch(data) {
  const entries = (data.top_matching_conversations ?? []).map((row) => [
    row.conversation_id,
    row.hit_count,
  ]);
  renderRankList("searchResults", entries, "hits");
}

async function runSearch(query) {
  const container = document.getElementById("searchResults");
  container.textContent = "Searching";
  try {
    renderSearch(await fetchJson(endpoints.search(query)));
  } catch (error) {
    const message = document.createElement("p");
    message.className = "errorText";
    message.textContent = error.message;
    container.replaceChildren(message);
  }
}

async function loadDashboard() {
  try {
    await fetchJson(endpoints.health);
    setHealth("Healthy", true);
  } catch (error) {
    setHealth("Offline");
    throw error;
  }

  const [overview, monthlyTrends, questionTypes] = await Promise.all([
    fetchJson(endpoints.overview),
    fetchJson(endpoints.monthlyTrends),
    fetchJson(endpoints.questionTypes),
  ]);

  renderOverview(overview);
  renderMonthlyTrends(monthlyTrends);
  renderQuestionTypes(questionTypes);
  await runSearch(document.getElementById("searchInput").value);
}

document.getElementById("searchForm").addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch(document.getElementById("searchInput").value.trim());
});

loadDashboard().catch((error) => {
  const message = document.createElement("p");
  message.className = "errorText";
  message.textContent = error.message;
  document.querySelector("main").replaceChildren(message);
});
