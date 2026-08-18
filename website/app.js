(() => {
  "use strict";

  const menuButton = document.querySelector(".nav-toggle");
  const mobileMenu = document.querySelector("#mobile-menu");

  function setMenu(open) {
    if (!menuButton || !mobileMenu) return;
    menuButton.setAttribute("aria-expanded", String(open));
    mobileMenu.hidden = !open;
    document.body.classList.toggle("menu-open", open);
  }

  menuButton?.addEventListener("click", () => {
    setMenu(menuButton.getAttribute("aria-expanded") !== "true");
  });

  mobileMenu?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setMenu(false));
  });

  const tabs = Array.from(document.querySelectorAll("[data-install-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-install-panel]"));

  function activateInstallTab(name) {
    tabs.forEach((tab) => {
      const active = tab.dataset.installTab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panels.forEach((panel) => {
      panel.hidden = panel.dataset.installPanel !== name;
    });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateInstallTab(tab.dataset.installTab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      const nextTab = tabs[nextIndex];
      activateInstallTab(nextTab.dataset.installTab);
      nextTab.focus();
    });
  });

  activateInstallTab("binary");
})();
