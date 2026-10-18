/**
 * PaperTrail — Dashboard & Document Interactive Helpers
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Live word count & reading time preview for document editor
  const contentInput = document.getElementById("document-content");
  const statsDisplay = document.getElementById("editor-live-stats");

  if (contentInput && statsDisplay) {
    function updateStats() {
      const text = contentInput.value.trim();
      const words = text ? text.split(/\s+/).length : 0;
      const chars = text.length;
      const estMinutes = (words / 200).toFixed(1);
      statsDisplay.textContent = `${words} words · ${chars} characters · ~${estMinutes} min read`;
    }
    contentInput.addEventListener("input", updateStats);
    updateStats();
  }

  // 2. Client-side quick filter for tables with data-searchable
  const searchFilterInput = document.getElementById("quick-table-search");
  if (searchFilterInput) {
    searchFilterInput.addEventListener("input", function () {
      const filter = this.value.toLowerCase();
      const rows = document.querySelectorAll(".data-table tbody tr");
      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? "" : "none";
      });
    });
  }
});
