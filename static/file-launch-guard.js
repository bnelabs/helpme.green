(() => {
  const fileLaunch = window.location.protocol === "file:";
  if (fileLaunch) document.documentElement.classList.add("file-launch");
  const guard = document.querySelector(".file-launch-guard");
  const appShell = document.querySelector(".app-shell");
  if (fileLaunch) {
    if (guard) guard.removeAttribute("hidden");
    return;
  }
  if (appShell) appShell.removeAttribute("hidden");
})();
