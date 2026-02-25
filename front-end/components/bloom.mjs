import {apiService} from "../index.mjs"
import { handleErrorDialog } from "./error.mjs";
/**
 * Create a bloom component
 * @param {string} template - The ID of the template to clone
 * @param {Object} bloom - The bloom data
 * @returns {DocumentFragment} - The bloom fragment of UI, for items in the Timeline
 * btw a bloom object is composed thus
 * {"id": Number,
 * "sender": username,
 * "content": "string from textarea",
 * "sent_timestamp": "datetime as ISO 8601 formatted string"}

 */
const createBloom = (template, bloom) => {
  if (!bloom) return;
  const bloomFrag = document.getElementById(template).content.cloneNode(true);
  const bloomParser = new DOMParser();

  const bloomArticle = bloomFrag.querySelector("[data-bloom]");
  const bloomUsername = bloomFrag.querySelector("[data-username]");
  const bloomTime = bloomFrag.querySelector("[data-time]");
  const bloomTimeLink = bloomFrag.querySelector("a:has(> [data-time])");
  const bloomContent = bloomFrag.querySelector("[data-content]");

  const rebloomEl = bloomFrag.querySelector("[data-rebloom]")
  const rebloomCount = bloomFrag.querySelector("[data-rebloom-count]");
  const rebloomBtn = bloomFrag.querySelector("[data-rebloom-button]");

  bloomArticle.setAttribute("data-bloom-id", bloom.id);
  bloomUsername.setAttribute("href", `/profile/${bloom.sender}`);
  bloomUsername.textContent = bloom.sender;
  bloomTime.textContent = _formatTimestamp(bloom.sent_timestamp);
  bloomTimeLink.setAttribute("href", `/bloom/${bloom.id}`);
  bloomContent.replaceChildren(
    ...bloomParser.parseFromString(_formatHashtags(bloom.content), "text/html")
      .body.childNodes
  );

  rebloomBtn.addEventListener("click", async (e) =>  handleRebloomClick(e, bloom));
  renderRebloom(rebloomEl, bloom);
  setupRebloomCount(rebloomCount,rebloomCount, bloom);

  return bloomFrag;
};

function renderRebloom(container, bloom) {
  if (!container) return;

  if (!bloom.rebloomed_by) {
    container.hidden = true;
    return;
  }

  container.replaceChildren();

  const originalBloomerLink = document.createElement("a");
  originalBloomerLink.href = `/profile/${bloom.rebloom_from}`;
  originalBloomerLink.textContent = bloom.rebloom_from;

  originalBloomerLink.style.fontWeight = "bold";

  container.append( "Originally bloomed by ", originalBloomerLink );
}

function setupRebloomCount(rebloomCount, article, bloom) {
  if (!rebloomCount) return;

  const count = Number(bloom.rebloom_count || 0);
  const isRebloom = Boolean(bloom.rebloomed_by);

  if (isRebloom || count === 0) {
    rebloomCount.hidden = true;
    return;
  }

  rebloomCount.hidden = false;
  rebloomCount.style.cursor = "pointer";
  rebloomCount.textContent = `Rebloomed ${String(count)} times (click to view)`;

  rebloomCount.addEventListener("click", (e) => {
    e.preventDefault();
    toggleRebloomers(article, rebloomCount, bloom.id);
  });
}

async function toggleRebloomers(article, anchor, bloomId) {
  const existing = article.querySelector("[data-rebloomers]");
  if (existing) {
    existing.remove();
    return;
  }

  try {
    const usernames = await apiService.getRebloomers(bloomId);

    const container = document.createElement("div");
    container.dataset.rebloomers = "";
    
    usernames.forEach((name, idx) => {
      if (idx > 0) container.append(", ");
      const a = document.createElement("a");
      a.href = `/profile/${name}`;
      a.textContent = name;
      container.append(a);
    });

    anchor.insertAdjacentElement("afterend", container);
  } catch (error) {
    handleErrorDialog(error)
  }
}

function _formatHashtags(text) {
  if (!text) return text;
  return text.replace(
    /\B#[^#]+/g,
    (match) => `<a href="/hashtag/${match.slice(1)}">${match}</a>`
  );
}

function _formatTimestamp(timestamp) {
  if (!timestamp) return "";

  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    // Less than a minute
    if (diffSeconds < 60) {
      return `${diffSeconds}s`;
    }

    // Less than an hour
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) {
      return `${diffMinutes}m`;
    }

    // Less than a day
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) {
      return `${diffHours}h`;
    }

    // Less than a week
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) {
      return `${diffDays}d`;
    }

    // Format as month and day for older dates
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
    }).format(date);
  } catch (error) {
    console.error("Failed to format timestamp:", error);
    return "";
  }
}

async function handleRebloomClick(event, bloom) {
  event.preventDefault();
  const button = event.currentTarget;
  const originalText = button.textContent;

  try {
    // Make button inert while calling backend
    button.inert = true;
    button.textContent = "Reblooming...";

    await apiService.postRebloom(bloom);

  } catch (error) {
    handleErrorDialog(error)
  } finally {
    // Restore UI state
    button.textContent = originalText;
    button.inert = false;
  }
}


export {createBloom};
