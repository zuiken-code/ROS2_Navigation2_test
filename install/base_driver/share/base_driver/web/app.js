const state = {
  sources: new Map(),
  values: {},
  widgets: [],
  connected: false,
  layoutLoaded: false,
};

const grid = document.querySelector("#grid");
const drawer = document.querySelector("#drawer");
const sourceList = document.querySelector("#sourceList");
const sourceSearch = document.querySelector("#sourceSearch");
const connectionText = document.querySelector("#connectionText");
const addWidgetButton = document.querySelector("#addWidgetButton");
const closeDrawerButton = document.querySelector("#closeDrawerButton");
const resetLayoutButton = document.querySelector("#resetLayoutButton");

const STORAGE_KEY = "ros2-dashboard-widgets";

function loadSavedWidgets(defaultWidgets) {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) {
    return defaultWidgets;
  }

  try {
    const parsed = JSON.parse(saved);
    return Array.isArray(parsed) ? parsed : defaultWidgets;
  } catch {
    return defaultWidgets;
  }
}

function saveWidgets() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.widgets));
}

function formatValue(source, rawValue) {
  if (rawValue === null || rawValue === undefined) {
    return "--";
  }

  if (source.kind === "boolean") {
    return rawValue ? "True" : "False";
  }

  if (source.kind === "number" && typeof rawValue === "number") {
    return rawValue.toFixed(source.precision ?? 3);
  }

  return String(rawValue);
}

function formatAge(value) {
  if (!value || !value.time) {
    return "No data yet";
  }

  const now = Date.now() / 1000;
  const age = Math.max(0, now - value.time);
  return `${age.toFixed(1)}s ago`;
}

function renderGrid() {
  grid.replaceChildren();

  for (const widget of state.widgets) {
    const source = state.sources.get(widget.source);
    if (!source) {
      continue;
    }

    const value = state.values[source.name] ?? {};
    const card = document.createElement("article");
    card.className = `widget ${widget.size === "large" ? "large" : ""}`;

    const head = document.createElement("div");
    head.className = "widget-head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("h2");
    title.className = "widget-title";
    title.textContent = source.label;

    const dataName = document.createElement("div");
    dataName.className = "data-name";
    dataName.textContent = source.name;

    titleWrap.append(title, dataName);

    const removeButton = document.createElement("button");
    removeButton.className = "remove-button";
    removeButton.type = "button";
    removeButton.title = "Remove widget";
    removeButton.textContent = "x";
    removeButton.addEventListener("click", () => removeWidget(source.name));

    head.append(titleWrap, removeButton);
    card.append(head);

    if (source.kind === "boolean") {
      const pill = document.createElement("div");
      pill.className = `boolean-pill ${value.value ? "true" : ""}`;
      pill.textContent = formatValue(source, value.value);
      card.append(pill);
    } else {
      const valueLine = document.createElement("div");
      valueLine.className = "value";
      valueLine.textContent = formatValue(source, value.value);

      if (source.unit) {
        const unit = document.createElement("span");
        unit.className = "unit";
        unit.textContent = source.unit;
        valueLine.append(unit);
      }

      card.append(valueLine);
    }

    const age = document.createElement("div");
    age.className = "age";
    age.textContent = formatAge(value);
    card.append(age);

    grid.append(card);
  }
}

function renderSourceList() {
  const query = sourceSearch.value.trim().toLowerCase();
  sourceList.replaceChildren();

  for (const source of state.sources.values()) {
    const haystack = `${source.name} ${source.label}`.toLowerCase();
    if (query && !haystack.includes(query)) {
      continue;
    }

    const button = document.createElement("button");
    button.className = "source-button";
    button.type = "button";
    button.innerHTML = `${source.label}<small>${source.name}</small>`;
    button.addEventListener("click", () => {
      addWidget(source.name);
      closeDrawer();
    });
    sourceList.append(button);
  }
}

function addWidget(sourceName) {
  state.widgets.push({
    source: sourceName,
    widget: "value",
    size: "medium",
  });
  saveWidgets();
  renderGrid();
}

function removeWidget(sourceName) {
  const index = state.widgets.findIndex((widget) => widget.source === sourceName);
  if (index >= 0) {
    state.widgets.splice(index, 1);
    saveWidgets();
    renderGrid();
  }
}

function openDrawer() {
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  sourceSearch.focus();
}

function closeDrawer() {
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

function setConnected(connected) {
  state.connected = connected;
  connectionText.textContent = connected ? "Live on robot network" : "Disconnected";
}

async function refreshState() {
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    const payload = await response.json();

    state.sources = new Map(payload.sources.map((source) => [source.name, source]));
    state.values = payload.values;
    if (!state.layoutLoaded) {
      state.widgets = loadSavedWidgets(payload.widgets);
      state.layoutLoaded = true;
    }

    setConnected(true);
    renderGrid();
    renderSourceList();
  } catch {
    setConnected(false);
  }
}

addWidgetButton.addEventListener("click", openDrawer);
closeDrawerButton.addEventListener("click", closeDrawer);
sourceSearch.addEventListener("input", renderSourceList);
resetLayoutButton.addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  state.widgets = [];
  state.layoutLoaded = false;
  refreshState();
});

refreshState();
setInterval(refreshState, 250);
