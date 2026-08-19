#!/usr/bin/env node

import {spawn, execFileSync} from "node:child_process";
import {createServer} from "node:net";
import {promises as fs} from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import {setTimeout as delay} from "node:timers/promises";

const VIEWPORTS = Object.freeze({
  desktop: Object.freeze({width: 1280, height: 900, deviceScaleFactor: 1, mobile: false}),
  mobile: Object.freeze({width: 390, height: 844, deviceScaleFactor: 1, mobile: true}),
});

function parseArguments(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (!value.startsWith("--")) continue;
    const name = value.slice(2);
    const next = argv[index + 1];
    if (next && !next.startsWith("--")) {
      result[name] = next;
      index += 1;
    } else {
      result[name] = true;
    }
  }
  return result;
}

function browserCandidates() {
  return [
    process.env.HELPME_BROWSER_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
}

function findBrowser(configuredPath) {
  if (configuredPath) return configuredPath;
  for (const candidate of browserCandidates()) {
    try {
      execFileSync("test", ["-x", candidate], {stdio: "ignore"});
      return candidate;
    } catch (_) {
      continue;
    }
  }
  for (const command of ["google-chrome", "chromium", "chromium-browser"]) {
    try {
      return execFileSync("which", [command], {encoding: "utf8"}).trim();
    } catch (_) {
      continue;
    }
  }
  return null;
}

function resolveViewport(name) {
  const viewportName = String(name || "desktop").trim().toLowerCase();
  const viewport = VIEWPORTS[viewportName];
  if (!viewport) {
    throw new Error(`--viewport must be one of: ${Object.keys(VIEWPORTS).join(", ")}.`);
  }
  return {name: viewportName, ...viewport};
}

async function freePort() {
  const listener = createServer();
  await new Promise((resolve, reject) => {
    listener.once("error", reject);
    listener.listen(0, "127.0.0.1", resolve);
  });
  const address = listener.address();
  const port = typeof address === "object" && address ? address.port : 0;
  await new Promise((resolve) => listener.close(resolve));
  return port;
}

async function jsonRequest(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Browser debugging endpoint returned ${response.status}.`);
  return response.json();
}

async function waitForJson(url, predicate, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const value = await jsonRequest(url);
      if (predicate(value)) return value;
    } catch (error) {
      lastError = error;
    }
    await delay(50);
  }
  throw new Error(`Timed out waiting for ${url}: ${lastError?.message || "no response"}`);
}

class DevToolsConnection {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id);
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message || "DevTools error."));
        else pending.resolve(message.result || {});
        return;
      }
      const callbacks = this.listeners.get(message.method) || [];
      callbacks.forEach((callback) => callback(message.params || {}));
    });
    socket.addEventListener("close", () => {
      for (const pending of this.pending.values()) {
        pending.reject(new Error("Browser debugging connection closed."));
      }
      this.pending.clear();
    });
  }

  on(method, callback) {
    const callbacks = this.listeners.get(method) || [];
    callbacks.push(callback);
    this.listeners.set(method, callbacks);
  }

  command(method, params = {}, sessionId = undefined) {
    const id = this.nextId++;
    const message = {id, method, params};
    if (sessionId) message.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.socket.send(JSON.stringify(message));
    });
  }
}

function waitForSocket(socket) {
  if (socket.readyState === WebSocket.OPEN) return Promise.resolve();
  return new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, {once: true});
    socket.addEventListener("error", reject, {once: true});
  });
}

async function evaluate(connection, sessionId, expression) {
  const response = await connection.command(
    "Runtime.evaluate",
    {expression, awaitPromise: true, returnByValue: true},
    sessionId,
  );
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description || "Page evaluation failed.");
  }
  return response.result?.value;
}

async function waitForPage(connection, sessionId, expression, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      if (await evaluate(connection, sessionId, expression)) return;
    } catch (_) {
      // The page may still be loading; try again until the bounded deadline.
    }
    await delay(50);
  }
  throw new Error(`Timed out waiting for page condition: ${expression}`);
}

async function click(connection, sessionId, selector) {
  const expression = `(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) throw new Error("Missing selector: ${selector}");
    element.click();
    return true;
  })()`;
  return evaluate(connection, sessionId, expression);
}

async function fill(connection, sessionId, selector, value) {
  const expression = `(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) throw new Error("Missing selector: ${selector}");
    element.focus();
    element.value = ${JSON.stringify(value)};
    element.dispatchEvent(new Event("input", {bubbles: true}));
    return true;
  })()`;
  return evaluate(connection, sessionId, expression);
}

async function textState(connection, sessionId) {
  return evaluate(connection, sessionId, `(() => {
    const visible = (selector) => {
      const element = document.querySelector(selector);
      if (!element || element.hidden) return false;
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
    };
    return {
      title: document.title,
      url: location.href,
      appVisible: Boolean(document.querySelector(".app-shell:not([hidden])")),
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      documentWidth: document.documentElement.scrollWidth,
      viewportClientWidth: document.documentElement.clientWidth,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      coreControlsVisible: ["#message", "#send", "#newNote"].every(visible),
      observationCount: document.querySelector("#observationCount")?.textContent || "",
      observations: [...document.querySelectorAll("#observationList .observation-text")].map((item) => item.textContent || ""),
      assistantVisible: document.querySelector("#assistantRead")?.hidden === false,
      assistantText: document.querySelector("#assistantText")?.textContent || "",
      frameworkOverlay: /(?:Vite|Next\.js|Webpack|Unhandled Runtime Error)/i.test(document.body?.innerText || ""),
    };
  })()`);
}

async function captureScreenshot(connection, sessionId, destination) {
  if (!destination) return;
  const result = await connection.command(
    "Page.captureScreenshot",
    {format: "png", captureBeyondViewport: false},
    sessionId,
  );
  await fs.writeFile(destination, Buffer.from(result.data, "base64"));
}

function assertResponsiveState(state, viewport, label) {
  if (state.viewportWidth !== viewport.width || state.viewportHeight !== viewport.height) {
    throw new Error(`${label} viewport mismatch: ${JSON.stringify(state)}`);
  }
  if (state.horizontalOverflow) {
    throw new Error(`${label} has horizontal overflow: ${JSON.stringify(state)}`);
  }
  if (!state.coreControlsVisible) {
    throw new Error(`${label} core controls are not usable: ${JSON.stringify(state)}`);
  }
}

async function stopProcess(browserProcess) {
  if (browserProcess.exitCode !== null || browserProcess.signalCode !== null) return;
  const exited = new Promise((resolve) => browserProcess.once("exit", resolve));
  browserProcess.kill("SIGTERM");
  await Promise.race([exited, delay(1000)]);
  if (browserProcess.exitCode === null && browserProcess.signalCode === null) {
    browserProcess.kill("SIGKILL");
    await Promise.race([exited, delay(1000)]);
  }
}

async function runReplay(options) {
  const url = String(options.url || "").trim();
  if (!url) throw new Error("--url is required.");
  const timeoutMs = Number(options["timeout-ms"] || 15_000);
  const browserPath = findBrowser(options.browser);
  if (!browserPath) throw new Error("No Chromium-compatible browser executable was found.");
  const viewport = resolveViewport(options.viewport);

  const debuggingPort = await freePort();
  const userDataDir = await fs.mkdtemp(path.join(os.tmpdir(), "helpme-green-browser-"));
  const browserArgs = [
    "--headless=new",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${userDataDir}`,
    `--remote-debugging-port=${debuggingPort}`,
    "about:blank",
  ];
  if (typeof process.getuid === "function" && process.getuid() === 0) browserArgs.push("--no-sandbox");
  const browserProcess = spawn(browserPath, browserArgs, {
    stdio: ["ignore", "ignore", "ignore"],
  });
  let socket = null;
  try {
    const endpoint = await waitForJson(
      `http://127.0.0.1:${debuggingPort}/json/version`,
      (value) => typeof value.webSocketDebuggerUrl === "string",
      timeoutMs,
    );
    socket = new WebSocket(endpoint.webSocketDebuggerUrl);
    await waitForSocket(socket);
    const connection = new DevToolsConnection(socket);
    const target = await connection.command("Target.createTarget", {url: "about:blank"});
    const attached = await connection.command("Target.attachToTarget", {
      targetId: target.targetId,
      flatten: true,
    });
    const sessionId = attached.sessionId;
    const consoleIssues = [];
    connection.on("Runtime.consoleAPICalled", (event) => {
      if (["error", "warning"].includes(event.type)) {
        consoleIssues.push({type: event.type, text: (event.args || []).map((item) => item.value ?? "").join(" ")});
      }
    });
    connection.on("Runtime.exceptionThrown", (event) => {
      consoleIssues.push({type: "exception", text: event.exceptionDetails?.text || "Page exception"});
    });
    connection.on("Log.entryAdded", (event) => {
      if (["error", "warning"].includes(event.entry?.level)) {
        consoleIssues.push({type: event.entry.level, text: event.entry.text || "Browser log entry"});
      }
    });
    await connection.command("Runtime.enable", {}, sessionId);
    await connection.command("Log.enable", {}, sessionId);
    await connection.command("Page.enable", {}, sessionId);
    await connection.command("Emulation.setDeviceMetricsOverride", {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: viewport.deviceScaleFactor,
      mobile: viewport.mobile,
    }, sessionId);
    await connection.command("Page.navigate", {url}, sessionId);
    await waitForPage(
      connection,
      sessionId,
      `document.readyState === "complete" && Boolean(document.querySelector(".app-shell:not([hidden])"))`,
      timeoutMs,
    );
    const initial = await textState(connection, sessionId);
    if (initial.title !== "helpme.green — Lab Notebook" || !initial.appVisible) {
      throw new Error(`Unexpected initial page state: ${JSON.stringify(initial)}`);
    }
    assertResponsiveState(initial, viewport, "Initial page");

    const materialObservation = "I have a dark, flexible rubber sample and want to understand what to check next.";
    await fill(connection, sessionId, "#message", materialObservation);
    await click(connection, sessionId, "#send");
    await waitForPage(
      connection,
      sessionId,
      `document.querySelector("#observationCount")?.textContent === "1 saved" && document.querySelector("#assistantRead")?.hidden === false && !document.querySelector("#send")?.disabled`,
      timeoutMs,
    );

    const unrelatedObservation = "What is the capital of Portugal?";
    await fill(connection, sessionId, "#message", unrelatedObservation);
    await click(connection, sessionId, "#send");
    await waitForPage(
      connection,
      sessionId,
      `document.querySelector("#observationCount")?.textContent === "2 saved" && document.querySelector("#assistantRead")?.hidden === false && !document.querySelector("#send")?.disabled`,
      timeoutMs,
    );
    const beforeReload = await textState(connection, sessionId);
    await captureScreenshot(connection, sessionId, options.screenshot);
    await connection.command("Page.reload", {ignoreCache: true}, sessionId);
    await waitForPage(
      connection,
      sessionId,
      `document.readyState === "complete" && document.querySelector("#observationCount")?.textContent === "2 saved"`,
      timeoutMs,
    );
    const afterReload = await textState(connection, sessionId);
    assertResponsiveState(afterReload, viewport, "Reloaded page");
    const observations = afterReload.observations;
    if (!observations.includes(materialObservation) || !observations.includes(unrelatedObservation)) {
      throw new Error(`Reload lost an observation: ${JSON.stringify(afterReload)}`);
    }
    return {
      url: afterReload.url,
      title: afterReload.title,
      viewport,
      initial,
      beforeReload,
      afterReload,
      consoleIssues,
      screenshot: options.screenshot || null,
    };
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    await stopProcess(browserProcess);
    await fs.rm(userDataDir, {recursive: true, force: true, maxRetries: 10, retryDelay: 100});
  }
}

const options = parseArguments(process.argv.slice(2));
runReplay(options)
  .then((result) => {
    process.stdout.write(`${JSON.stringify(result)}\n`);
  })
  .catch((error) => {
    process.stderr.write(`${JSON.stringify({error: error.message})}\n`);
    process.exitCode = 1;
  });
