/*
 * Property of Data-Blitz Inc.
 * Author: Paul Harvener
 *
 * Frontend controller for AI search and header catalog search interactions.
 */

const form = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt");
const siteSearchInput = document.getElementById("site-search-input");
const siteSearchButton = document.getElementById("site-search-button");
const statusNode = document.getElementById("status");
const responseNode = document.getElementById("response");
const resultsNode = document.getElementById("results");
const resultCountNode = document.getElementById("result-count");

/**
 * Args:
 *   value: unknown
 *     Numeric value to format as USD.
 * Returns:
 *   string
 *     Currency-formatted text or "n/a" for missing input.
 */
function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(value));
}

/**
 * Args:
 *   value: unknown
 *     Text candidate that may include unsafe HTML.
 * Returns:
 *   string
 *     Escaped text safe to inject into HTML templates.
 */
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/**
 * Args:
 *   text: string
 *     Message shown in status line.
 * Returns:
 *   void
 *     Updates status node content.
 */
function setStatus(text) {
  statusNode.textContent = text;
}

/**
 * Args:
 *   quantity: number | null | undefined
 *     Inventory quantity from API payload.
 * Returns:
 *   string
 *     Human-friendly stock status label.
 */
function stockLabel(quantity) {
  if (quantity === null || quantity === undefined) {
    return "Unknown Stock";
  }
  if (quantity >= 5000) {
    return "High Stock";
  }
  if (quantity >= 500) {
    return "In Stock";
  }
  if (quantity > 0) {
    return "Limited Stock";
  }
  return "Out of Stock";
}

/**
 * Args:
 *   message: string
 *     Empty-state explanation for results table.
 * Returns:
 *   void
 *     Renders an empty row with message and resets result count chip.
 */
function renderEmptyState(message) {
  resultsNode.innerHTML = `<tr><td class="empty-row" colspan="7">${escapeHtml(message)}</td></tr>`;
  resultCountNode.textContent = "0 Results";
}

/**
 * Args:
 *   products: Array<object>
 *     Result rows from AI search or direct catalog search.
 *   sourceLabel: string
 *     Optional source annotation shown in result count chip.
 * Returns:
 *   void
 *     Replaces table body rows with rendered product results.
 */
function renderProducts(products, sourceLabel = "") {
  if (!products || products.length === 0) {
    renderEmptyState("No matching products were returned for this request.");
    return;
  }

  resultCountNode.textContent = `${products.length} Result${products.length > 1 ? "s" : ""}${
    sourceLabel ? ` (${sourceLabel})` : ""
  }`;
  resultsNode.innerHTML = "";

  for (const p of products) {
    const quantity = p.quantity_available ?? null;
    const partNumber = p.manufacturer_part_number || p.id || "Unknown Part";
    const fitText = p.fit_reason || "Catalog result.";
    const score = p.recommendation_score;
    const scoreDisplay = score !== null && score !== undefined ? String(score) : "n/a";

    const productUrl = p.product_url || `https://www.digikey.com/en/products/result?s=${encodeURIComponent(partNumber)}`;
    const datasheetUrl = p.datasheet_url;

    const row = document.createElement("tr");

    row.innerHTML = `
      <td>
        <div class="part-number">${escapeHtml(partNumber)}</div>
        <div class="manufacturer">${escapeHtml(p.manufacturer || "Unknown Manufacturer")}</div>
      </td>
      <td>
        <div class="desc-title">${escapeHtml(p.name || partNumber)}</div>
        <div class="desc-copy">${escapeHtml(p.description || "No description available")}</div>
      </td>
      <td>${escapeHtml(p.category || "Uncategorized")}</td>
      <td>
        <span class="stock-badge">${stockLabel(quantity)}</span>
        <div class="fit-text">Qty Available: ${quantity ?? "n/a"}</div>
      </td>
      <td class="price">${money(p.unit_price)}</td>
      <td>
        <span class="score-chip">${escapeHtml(scoreDisplay)}</span>
        <div class="fit-text">${escapeHtml(fitText)}</div>
      </td>
      <td>
        <div class="table-links">
          <a href="${escapeHtml(productUrl)}" target="_blank" rel="noreferrer">Product Page</a>
          ${
            datasheetUrl
              ? `<a href="${escapeHtml(datasheetUrl)}" target="_blank" rel="noreferrer">Datasheet</a>`
              : ""
          }
        </div>
      </td>
    `;

    resultsNode.appendChild(row);
  }
}

/**
 * Args:
 *   sourceLabel: string
 *     Raw source label from backend response.
 * Returns:
 *   string
 *     User-facing source label.
 */
function prettySourceLabel(sourceLabel) {
  if (sourceLabel === "mock_catalog" || sourceLabel === "mock") {
    return "Mock Catalog";
  }
  return sourceLabel || "Catalog";
}

/**
 * Args:
 *   message: string
 *     Natural-language assistant prompt.
 * Returns:
 *   Promise<object>
 *     Parsed JSON response from /api/chat endpoint.
 */
async function doAiSearch(message) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Args:
 *   query: string
 *     Header search keyword query.
 * Returns:
 *   Promise<object>
 *     Parsed JSON response from /api/digikey-search endpoint.
 */
async function doDirectSearch(query) {
  const response = await fetch("/api/digikey-search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit: 12 }),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Args:
 *   event: SubmitEvent
 *     Form submit event object.
 * Returns:
 *   Promise<void>
 *     Executes assistant flow and refreshes results table.
 * Notes:
 *   This is the primary AI-assisted search interaction path.
 */
async function handleAssistantSubmit(event) {
  event.preventDefault();
  const message = promptInput.value.trim();
  if (!message) {
    return;
  }

  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  setStatus("Interpreting request and querying Mock Catalog...");
  responseNode.style.display = "none";
  renderEmptyState("Searching...");

  try {
    const payload = await doAiSearch(message);
    const sourceLabel = prettySourceLabel(payload.mode);
    setStatus(`Source: ${sourceLabel} | Intent: ${payload.intent.keywords}`);
    responseNode.style.display = "block";
    responseNode.textContent = payload.warning ? `${payload.answer} ${payload.warning}` : payload.answer;
    renderProducts(payload.products, sourceLabel);
  } catch (error) {
    setStatus("Request failed. Check service logs.");
    responseNode.style.display = "block";
    responseNode.textContent = error.message;
    renderEmptyState("No products returned due to request error.");
  } finally {
    button.disabled = false;
  }
}

/**
 * Args:
 *   None
 * Returns:
 *   Promise<void>
 *     Executes direct header search against the mock catalog.
 */
async function triggerHeaderSearch() {
  const query = siteSearchInput.value.trim();
  if (!query) {
    return;
  }

  siteSearchButton.disabled = true;
  setStatus("Searching mock catalog...");
  responseNode.style.display = "none";
  renderEmptyState("Searching catalog...");

  try {
    const payload = await doDirectSearch(query);
    const sourceLabel = prettySourceLabel(payload.source);
    setStatus(`Header search | Source: ${sourceLabel} | Query: ${payload.query}`);
    responseNode.style.display = "block";
    responseNode.textContent = payload.warning ? payload.warning : "Showing mock catalog results.";
    renderProducts(payload.products, sourceLabel);
  } catch (error) {
    setStatus("Header search failed.");
    responseNode.style.display = "block";
    responseNode.textContent = error.message;
    renderEmptyState("No products returned due to request error.");
  } finally {
    siteSearchButton.disabled = false;
  }
}

/**
 * Args:
 *   event: KeyboardEvent
 *     Keyboard interaction from header search input.
 * Returns:
 *   void
 *     Triggers direct search when Enter is pressed.
 */
function handleHeaderSearchInputKeydown(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    triggerHeaderSearch();
  }
}

// Initialize default table placeholder before first search.
renderEmptyState("Use AI search or the top search bar to find products.");

// Bind primary search interactions.
form.addEventListener("submit", handleAssistantSubmit);
siteSearchButton.addEventListener("click", triggerHeaderSearch);
siteSearchInput.addEventListener("keydown", handleHeaderSearchInputKeydown);
