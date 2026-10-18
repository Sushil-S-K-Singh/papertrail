/**
 * PaperTrail — Main Client-Side JavaScript
 * Pure Vanilla JavaScript — Zero external dependencies
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Navigation Toggle
  const mobileToggle = document.querySelector(".mobile-nav-toggle");
  const navLinks = document.querySelector(".nav-links");
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener("click", function () {
      navLinks.classList.toggle("show");
    });
  }

  // 2. Password Visibility Toggle
  const passwordToggles = document.querySelectorAll(".password-toggle-btn");
  passwordToggles.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const targetId = btn.getAttribute("data-target");
      const input = targetId ? document.getElementById(targetId) : btn.previousElementSibling;
      if (input) {
        if (input.type === "password") {
          input.type = "text";
          btn.textContent = "Hide";
        } else {
          input.type = "password";
          btn.textContent = "Show";
        }
      }
    });
  });

  // 3. Dismissible Alert Banners
  const alertCloses = document.querySelectorAll(".alert-close");
  alertCloses.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const alert = btn.closest(".alert");
      if (alert) {
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-8px)";
        alert.style.transition = "all 0.2s ease";
        setTimeout(function () {
          alert.remove();
        }, 200);
      }
    });
  });

  // 4. Confirmation Dialogs on Destructive Actions
  const confirmForms = document.querySelectorAll("form[data-confirm]");
  confirmForms.forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const message = form.getAttribute("data-confirm") || "Are you sure you want to proceed?";
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });
});
