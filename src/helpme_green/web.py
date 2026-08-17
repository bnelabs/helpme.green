from __future__ import annotations

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f4f0e7">
<meta name="description" content="A calm, source-aware material investigation notebook.">
<link rel="icon" href="/assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/brand-mark.png">
<title>helpme.green — Lab Notebook</title>
<style>
:root {
  color-scheme: light;
  --ink: #1d281e;
  --ink-soft: #39463a;
  --muted: #6f786c;
  --quiet: #8e9688;
  --faint: #aab0a4;
  --canvas: #f1eee6;
  --canvas-deep: #e8e3d8;
  --paper: #fffdf7;
  --paper-alt: #f8f5ed;
  --paper-warm: #f2ede2;
  --panel: rgba(255, 254, 249, .92);
  --panel-solid: #fbfaf5;
  --line: #ddd9cd;
  --line-strong: #c9c6b9;
  --forest: #203d1c;
  --forest-2: #31562a;
  --moss: #80935e;
  --moss-soft: #e8eddc;
  --amber: #a66d17;
  --amber-soft: #f6edd6;
  --coral: #bd5e4d;
  --coral-soft: #f7e3dc;
  --shadow: 0 26px 70px rgba(53, 48, 36, .15), 0 4px 14px rgba(53, 48, 36, .08);
  --shadow-soft: 0 14px 34px rgba(53, 48, 36, .1);
  --sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --serif: Iowan Old Style, Baskerville, "Times New Roman", serif;
  --note: "Segoe Print", "Bradley Hand", "Comic Sans MS", cursive;
}
body[data-theme="dark"] {
  color-scheme: dark;
  --ink: #f4f0e5;
  --ink-soft: #d7d8c9;
  --muted: #b0b8aa;
  --quiet: #929d90;
  --faint: #6f7d6f;
  --canvas: #101a14;
  --canvas-deep: #17231b;
  --paper: #18241b;
  --paper-alt: #1d2a20;
  --paper-warm: #202f23;
  --panel: rgba(24, 36, 27, .94);
  --panel-solid: #19261c;
  --line: #3c4b3d;
  --line-strong: #566554;
  --forest: #d7e7ae;
  --forest-2: #b9d08e;
  --moss: #a9bf7d;
  --moss-soft: #2b3d2a;
  --amber: #edbd62;
  --amber-soft: #493820;
  --coral: #ef9c89;
  --coral-soft: #4c2e29;
  --shadow: 0 28px 75px rgba(0, 0, 0, .3), 0 4px 14px rgba(0, 0, 0, .2);
  --shadow-soft: 0 16px 38px rgba(0, 0, 0, .23);
}
* { box-sizing: border-box; }
html {
  min-width: 320px;
  background: var(--canvas);
  scroll-behavior: smooth;
}
body {
  min-width: 320px;
  margin: 0;
  overflow-x: hidden;
  overscroll-behavior-x: none;
  background:
    radial-gradient(circle at 8% 4%, rgba(129, 149, 96, .12), transparent 27rem),
    radial-gradient(circle at 95% 70%, rgba(181, 147, 83, .08), transparent 31rem),
    var(--canvas);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  transition: background .35s ease, color .35s ease;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  opacity: .3;
  background-image: radial-gradient(rgba(53, 48, 36, .09) .55px, transparent .55px);
  background-size: 7px 7px;
  mix-blend-mode: multiply;
}
body[data-theme="dark"]::before {
  opacity: .08;
  mix-blend-mode: screen;
}
button, input, textarea { font: inherit; }
button { cursor: pointer; touch-action: manipulation; }
button:focus-visible, input:focus-visible, textarea:focus-visible, summary:focus-visible, a:focus-visible {
  outline: 2px solid var(--amber);
  outline-offset: 3px;
}
button:disabled { cursor: wait; opacity: .5; }
a { color: inherit; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.app-shell { min-height: 100vh; }
.topbar {
  align-items: center;
  background: color-mix(in srgb, var(--panel-solid) 88%, transparent);
  border-bottom: 1px solid var(--line);
  display: grid;
  gap: 22px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  min-height: 76px;
  padding: 0 clamp(16px, 3vw, 42px);
  position: sticky;
  top: 0;
  z-index: 50;
  -webkit-backdrop-filter: blur(18px);
  backdrop-filter: blur(18px);
}
.brand-lockup {
  align-items: center;
  display: inline-flex;
  gap: 9px;
  min-height: 44px;
  text-decoration: none;
}
.brand-mark { display: block; height: 33px; object-fit: contain; width: 33px; }
.wordmark {
  font-family: var(--serif);
  font-size: 25px;
  letter-spacing: -.055em;
  white-space: nowrap;
}
.wordmark span { color: var(--moss); }
.primary-nav { align-items: center; display: flex; gap: 28px; margin-left: 14px; }
.nav-link {
  color: var(--muted);
  font-size: 14px;
  padding: 28px 0 25px;
  text-decoration: none;
  transition: color .22s ease, border-color .22s ease;
}
.nav-link:hover, .nav-link.active { color: var(--ink); }
.nav-link.active { border-bottom: 2px solid var(--forest); }
.topbar-tools { align-items: center; display: flex; gap: 10px; justify-content: flex-end; min-width: 0; }
.global-search {
  align-items: center;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 10px;
  display: flex;
  min-width: min(250px, 25vw);
  padding: 0 12px;
  transition: border-color .22s ease, box-shadow .22s ease;
}
.global-search:focus-within { border-color: var(--forest-2); box-shadow: 0 0 0 3px var(--moss-soft); }
.global-search input {
  background: transparent;
  border: 0;
  color: var(--ink);
  min-height: 38px;
  min-width: 0;
  outline: 0;
  padding: 0;
  width: 100%;
}
.global-search input::placeholder, .material-search input::placeholder { color: var(--quiet); }
.new-note, .primary-button {
  align-items: center;
  background: var(--forest);
  border: 1px solid var(--forest);
  border-radius: 9px;
  color: #fffdf4;
  display: inline-flex;
  font-size: 13px;
  justify-content: center;
  min-height: 40px;
  padding: 0 15px;
  transition: background .22s ease, box-shadow .22s ease, transform .22s ease;
}
.new-note:hover, .primary-button:hover { background: var(--forest-2); box-shadow: var(--shadow-soft); transform: translateY(-1px); }
.theme-toggle, .profile-button {
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 9px;
  color: var(--ink-soft);
  font-size: 12px;
  min-height: 40px;
  padding: 0 12px;
  transition: background .22s ease, border-color .22s ease;
}
.theme-toggle:hover, .profile-button:hover { background: var(--moss-soft); border-color: var(--line-strong); }
.profile-button { border-radius: 50%; font-weight: 700; padding: 0; width: 40px; }
.notebook-workspace {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr) 300px;
  min-height: calc(100vh - 76px);
  max-width: 1800px;
  margin: 0 auto;
}
.phase-rail {
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 31px 17px 23px;
}
.rail-kicker, .page-kicker, .library-kicker {
  color: var(--moss);
  display: block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .15em;
  line-height: 1.4;
  text-transform: uppercase;
}
.phase-list {
  list-style: none;
  margin: 28px 0 0;
  padding: 0;
  position: relative;
}
.phase-list::before {
  background: var(--line-strong);
  content: "";
  height: calc(100% - 36px);
  left: 16px;
  position: absolute;
  top: 18px;
  width: 1px;
}
.phase-step { position: relative; }
.phase-button {
  align-items: flex-start;
  background: transparent;
  border: 0;
  color: var(--muted);
  display: flex;
  gap: 10px;
  padding: 0 0 25px;
  position: relative;
  text-align: left;
  width: 100%;
}
.phase-number {
  align-items: center;
  background: var(--paper);
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  color: var(--muted);
  display: flex;
  flex: 0 0 33px;
  font-size: 12px;
  height: 33px;
  justify-content: center;
  position: relative;
  transition: background .22s ease, border-color .22s ease, color .22s ease, box-shadow .22s ease;
  z-index: 1;
}
.phase-copy { display: block; min-width: 0; padding-top: 2px; }
.phase-label { color: var(--ink-soft); display: block; font-size: 12px; font-weight: 700; line-height: 1.2; }
.phase-detail { color: var(--quiet); display: block; font-size: 10px; line-height: 1.35; margin-top: 4px; }
.phase-step[data-state="active"] .phase-number {
  background: var(--forest);
  border-color: var(--forest);
  box-shadow: 0 0 0 5px var(--moss-soft);
  color: #fffdf4;
}
.phase-step[data-state="active"] .phase-label { color: var(--ink); }
.phase-step[data-state="complete"] .phase-number { background: var(--moss-soft); border-color: var(--moss); color: var(--forest); }
.phase-status {
  color: var(--quiet);
  display: block;
  font-size: 9px;
  letter-spacing: .04em;
  margin-top: 4px;
}
.phase-step[data-state="active"] .phase-status { color: var(--forest-2); }
.phase-step[data-state="complete"] .phase-status { color: var(--forest-2); }
.rail-footer { border-top: 1px solid var(--line); margin-top: auto; padding-top: 18px; }
.rail-page-count { color: var(--ink-soft); font-family: var(--serif); font-size: 14px; }
.rail-progress { background: var(--line); border-radius: 999px; height: 5px; margin-top: 9px; overflow: hidden; }
.rail-progress span { background: var(--forest); border-radius: inherit; display: block; height: 100%; transition: width .4s ease; }
.notebook-column { min-width: 0; padding: 26px clamp(14px, 3vw, 45px) 34px; }
.mobile-toolbar { align-items: center; display: flex; justify-content: space-between; margin: 0 auto 15px; max-width: 1120px; }
.mobile-toolbar .rail-kicker { margin: 0; }
.page-state { color: var(--muted); font-size: 12px; }
.library-toggle {
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 9px;
  color: var(--ink-soft);
  display: none;
  font-size: 12px;
  min-height: 40px;
  padding: 0 12px;
}
.notebook-stage { margin: 0 auto; max-width: 1120px; }
.notebook-spread {
  background: var(--paper-warm);
  border: 1px solid var(--line-strong);
  border-radius: 17px;
  box-shadow: var(--shadow);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  min-height: 650px;
  overflow: hidden;
  perspective: 1400px;
  position: relative;
  transform-origin: center;
}
.notebook-spread::before {
  background: linear-gradient(90deg, transparent 0%, rgba(64, 74, 55, .25) 45%, rgba(255,255,255,.32) 55%, transparent 100%);
  content: "";
  height: 100%;
  left: 50%;
  pointer-events: none;
  position: absolute;
  transform: translateX(-50%);
  width: 18px;
  z-index: 5;
}
.notebook-spread.is-turning-forward { animation: page-turn-forward .62s cubic-bezier(.22, .75, .2, 1); }
.notebook-spread.is-turning-back { animation: page-turn-back .62s cubic-bezier(.22, .75, .2, 1); }
.page {
  background: var(--paper);
  min-width: 0;
  padding: clamp(24px, 3.4vw, 48px) clamp(21px, 3.5vw, 52px) 31px;
  position: relative;
}
.page-left { border-right: 1px solid var(--line); }
.page-right { background: var(--paper-alt); }
.page-header { align-items: flex-start; display: flex; justify-content: space-between; }
.note-date { color: var(--muted); font-size: 10px; letter-spacing: .14em; }
.note-tag { color: var(--moss); font-size: 10px; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; }
.note-title {
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--line-strong);
  color: var(--ink);
  display: block;
  font-family: var(--note);
  font-size: clamp(24px, 3vw, 39px);
  line-height: 1.15;
  margin: 21px 0 19px;
  max-width: 100%;
  outline: 0;
  padding: 0 0 8px;
  width: 100%;
}
.note-title:focus { border-color: var(--forest); }
.page-lede { color: var(--ink-soft); font-size: 13px; line-height: 1.65; margin: 0; max-width: 48ch; }
.evidence-board {
  display: grid;
  gap: 7px;
  grid-template-columns: 1.35fr 1fr 1fr;
  margin: 23px 0 28px;
}
.board-card { background: var(--paper-warm); border: 1px solid var(--line); border-radius: 6px; margin: 0; overflow: hidden; }
.board-card:first-child { grid-row: span 2; }
.board-card img { display: block; height: 100%; min-height: 82px; object-fit: cover; width: 100%; }
.board-card:first-child img { min-height: 172px; }
.board-caption { color: var(--muted); font-size: 9px; letter-spacing: .1em; margin-top: 8px; text-transform: uppercase; }
.section-title {
  align-items: center;
  color: var(--ink-soft);
  display: flex;
  font-size: 10px;
  font-weight: 700;
  justify-content: space-between;
  letter-spacing: .13em;
  margin: 0 0 9px;
  text-transform: uppercase;
}
.observation-list { list-style: none; margin: 0; padding: 0; }
.observation-row {
  align-items: flex-start;
  border-top: 1px solid var(--line);
  display: flex;
  gap: 10px;
  padding: 10px 0;
}
.observation-index {
  align-items: center;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  color: var(--muted);
  display: flex;
  flex: 0 0 24px;
  font-size: 10px;
  height: 24px;
  justify-content: center;
}
.observation-text { color: var(--ink-soft); font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
.empty-row { color: var(--quiet); font-style: italic; padding: 13px 0; }
.reference-section { border-top: 1px solid var(--line); margin-top: 13px; padding-top: 17px; }
.reference-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.reference-chip {
  align-items: center;
  background: var(--paper-warm);
  border: 1px solid var(--line-strong);
  border-radius: 7px;
  color: var(--ink-soft);
  display: inline-flex;
  font-size: 11px;
  gap: 7px;
  min-height: 30px;
  padding: 0 8px 0 6px;
}
.reference-chip img { border-radius: 4px; height: 20px; object-fit: cover; width: 20px; }
.reference-chip button { background: transparent; border: 0; color: var(--muted); font-size: 10px; min-height: auto; padding: 2px; }
.reference-empty { color: var(--quiet); font-size: 11px; line-height: 1.45; }
.evidence-capture { border-top: 1px solid var(--line); margin-top: 16px; padding-top: 17px; }
.evidence-intro { color: var(--muted); font-size: 11px; line-height: 1.5; margin: 0 0 11px; }
.evidence-photo-row { align-items: center; display: flex; flex-wrap: wrap; gap: 7px; }
.evidence-photo {
  background: var(--paper-warm);
  border: 1px solid var(--line-strong);
  border-radius: 7px;
  height: 92px;
  overflow: hidden;
  position: relative;
  width: 64px;
}
.evidence-photo img { display: block; height: 64px; object-fit: cover; width: 100%; }
.evidence-photo button {
  background: var(--paper-alt);
  border: 0;
  border-top: 1px solid var(--line);
  color: var(--muted);
  display: block;
  font-size: 9px;
  height: 27px;
  min-height: 27px;
  padding: 0;
  width: 100%;
}
.evidence-photo button:hover { background: var(--coral); }
.evidence-empty { color: var(--quiet); font-size: 11px; padding: 8px 0; }
.evidence-upload {
  align-items: center;
  background: var(--paper-alt);
  border: 1px dashed var(--line-strong);
  border-radius: 7px;
  color: var(--forest-2);
  cursor: pointer;
  display: inline-flex;
  font-size: 11px;
  min-height: 92px;
  padding: 0 11px;
  transition: background .22s ease, border-color .22s ease, transform .22s ease;
}
.evidence-upload:hover { background: var(--moss-soft); border-color: var(--moss); transform: translateY(-1px); }
.evidence-upload-input { display: none; }
.evidence-fields { display: grid; gap: 8px; grid-template-columns: minmax(0, .85fr) minmax(0, 1.15fr); margin-top: 11px; }
.evidence-field { color: var(--muted); display: grid; font-size: 10px; gap: 5px; letter-spacing: .04em; }
.evidence-field input, .evidence-field select {
  background: var(--paper-alt);
  border: 1px solid var(--line);
  border-radius: 7px;
  color: var(--ink-soft);
  min-height: 36px;
  min-width: 0;
  padding: 0 9px;
}
.evidence-detail { margin-top: 8px; }
.evidence-detail input { width: 100%; }
.evidence-note { color: var(--quiet); font-size: 10px; line-height: 1.45; margin-top: 9px; }
.evidence-guidance {
  background: color-mix(in srgb, var(--amber-soft) 72%, var(--paper-alt));
  border: 1px solid color-mix(in srgb, var(--amber) 38%, var(--line));
  border-radius: 8px;
  color: var(--ink-soft);
  margin-top: 10px;
  padding: 10px 11px;
}
.evidence-guidance strong { color: var(--amber); display: block; font-size: 10px; letter-spacing: .08em; text-transform: uppercase; }
.evidence-guidance p { font-size: 11px; line-height: 1.5; margin: 5px 0 0; }
.comparison-actions { align-items: center; display: flex; flex-wrap: wrap; gap: 9px; margin-top: 12px; }
.comparison-hint { color: var(--quiet); font-size: 10px; line-height: 1.4; }
.comparison-read {
  background: color-mix(in srgb, var(--amber-soft) 64%, var(--paper-alt));
  border: 1px solid color-mix(in srgb, var(--amber) 45%, var(--line));
  border-radius: 9px;
  margin-top: 20px;
  padding: 13px;
}
.comparison-read p { color: var(--ink-soft); font-size: 13px; line-height: 1.65; margin: 8px 0 0; white-space: pre-wrap; }
.comparison-read .page-kicker { color: var(--amber); }
.comparison-disclaimer { color: var(--muted); font-size: 10px !important; line-height: 1.45 !important; margin-top: 10px !important; }
.working-read { border-bottom: 1px solid var(--line); padding-bottom: 22px; }
.working-read h2 {
  color: var(--ink);
  font-family: var(--serif);
  font-size: clamp(23px, 2.6vw, 34px);
  font-weight: 400;
  letter-spacing: -.04em;
  line-height: 1.08;
  margin: 14px 0 12px;
}
.working-read p, .read-list, .change-list, .next-question p { color: var(--ink-soft); font-size: 13px; line-height: 1.65; }
.read-list, .change-list { margin: 0; padding-left: 17px; }
.read-list li + li, .change-list li + li { margin-top: 8px; }
.read-section { border-bottom: 1px solid var(--line); padding: 20px 0; }
.read-section .section-title { color: var(--forest-2); }
.read-section.change .section-title { color: var(--amber); }
.next-question { padding: 21px 0 0; }
.next-question p { margin: 10px 0 14px; }
.text-button, .quiet-button {
  background: transparent;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  color: var(--ink-soft);
  font-size: 12px;
  min-height: 38px;
  padding: 0 12px;
  transition: background .22s ease, border-color .22s ease, transform .22s ease;
}
.text-button:hover, .quiet-button:hover { background: var(--moss-soft); border-color: var(--moss); transform: translateY(-1px); }
.assistant-read {
  background: var(--moss-soft);
  border: 1px solid color-mix(in srgb, var(--moss) 50%, var(--line));
  border-radius: 9px;
  margin-top: 20px;
  padding: 13px;
}
.assistant-read p { margin: 8px 0 0; white-space: pre-wrap; }
.source-note { color: var(--muted); font-size: 10px; line-height: 1.45; margin: 9px 0 0; }
.observation-composer {
  background: var(--paper);
  border: 1px solid var(--line-strong);
  border-radius: 13px;
  box-shadow: 0 8px 22px rgba(53, 48, 36, .07);
  margin-top: 25px;
  padding: 11px 12px 10px;
  transition: border-color .22s ease, box-shadow .22s ease;
}
.observation-composer:focus-within { border-color: var(--forest-2); box-shadow: 0 0 0 4px var(--moss-soft); }
.observation-composer textarea {
  background: transparent;
  border: 0;
  color: var(--ink);
  display: block;
  line-height: 1.55;
  min-height: 70px;
  outline: 0;
  padding: 2px 2px 0;
  resize: vertical;
  width: 100%;
}
.observation-composer textarea::placeholder { color: var(--quiet); }
.composer-footer { align-items: center; display: flex; gap: 10px; justify-content: space-between; padding-top: 8px; }
.composer-hint { color: var(--quiet); font-size: 10px; line-height: 1.4; }
.save-observation {
  background: var(--forest);
  border: 1px solid var(--forest);
  border-radius: 8px;
  color: #fffdf4;
  font-size: 12px;
  min-height: 37px;
  padding: 0 13px;
}
.save-observation:hover { background: var(--forest-2); }
.page-nav {
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: var(--shadow-soft);
  display: grid;
  gap: 13px;
  grid-template-columns: minmax(118px, auto) 1fr minmax(180px, auto);
  margin-top: 16px;
  padding: 10px 12px;
}
.page-progress { align-items: center; display: flex; gap: 8px; justify-content: center; }
.page-dot {
  background: var(--line-strong);
  border: 0;
  border-radius: 999px;
  height: 7px;
  min-height: 7px;
  padding: 0;
  transition: background .22s ease, transform .22s ease, width .22s ease;
  width: 7px;
}
.page-dot.active { background: var(--forest); transform: scale(1.15); width: 23px; }
.page-dot.complete { background: var(--moss); }
.page-nav .primary-button { min-height: 44px; }
.auth-card {
  background: var(--paper);
  border: 1px solid var(--line-strong);
  border-radius: 13px;
  box-shadow: var(--shadow-soft);
  margin: 0 auto 15px;
  max-width: 1120px;
  padding: 17px;
}
.auth-card[hidden] { display: none; }
.auth-card p { color: var(--ink-soft); font-size: 13px; line-height: 1.5; margin: 0 0 11px; }
.auth-form { align-items: center; display: flex; gap: 9px; }
.auth-form input {
  background: var(--paper-alt);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--ink);
  min-height: 40px;
  min-width: 0;
  padding: 0 11px;
  width: min(320px, 100%);
}
.auth-error { color: var(--coral); font-size: 12px; margin-top: 9px; }
.auth-error[hidden] { display: none; }
.status-note { color: var(--quiet); font-size: 10px; line-height: 1.45; margin: 12px 2px 0; min-height: 15px; }
.library-drawer {
  background: var(--panel);
  border-left: 1px solid var(--line);
  min-width: 0;
  overflow-y: auto;
  padding: 27px 16px 25px;
  position: relative;
  z-index: 20;
}
.library-header { align-items: flex-start; display: flex; justify-content: space-between; }
.library-header h2 { font-size: 17px; letter-spacing: -.02em; margin: 8px 0 0; }
.library-close {
  background: transparent;
  border: 0;
  color: var(--muted);
  font-size: 12px;
  min-height: 34px;
  padding: 0 4px;
}
.library-close:hover { color: var(--ink); }
.material-search {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 9px;
  margin: 20px 0 15px;
  padding: 0 10px;
}
.material-search input {
  background: transparent;
  border: 0;
  color: var(--ink);
  min-height: 39px;
  outline: 0;
  width: 100%;
}
.category-list { display: grid; gap: 5px; }
.category-block { border-bottom: 1px solid var(--line); padding-bottom: 6px; }
.category-button {
  align-items: center;
  background: transparent;
  border: 0;
  border-radius: 9px;
  color: var(--ink-soft);
  display: flex;
  gap: 9px;
  min-height: 51px;
  padding: 5px 6px;
  text-align: left;
  width: 100%;
}
.category-button:hover, .category-button.active { background: var(--moss-soft); }
.category-thumb { border: 1px solid var(--line); border-radius: 7px; flex: 0 0 40px; height: 40px; object-fit: cover; width: 40px; }
.category-copy { min-width: 0; }
.category-name { display: block; font-size: 12px; font-weight: 700; line-height: 1.2; }
.category-count { color: var(--quiet); display: block; font-size: 10px; margin-top: 4px; }
.category-state { color: var(--muted); font-size: 15px; margin-left: auto; transform: rotate(90deg); transition: transform .22s ease; }
.category-button.active .category-state { transform: rotate(-90deg); }
.subtype-list { display: grid; gap: 4px; padding: 3px 0 7px 12px; }
.subtype-button {
  align-items: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--ink-soft);
  display: flex;
  gap: 8px;
  min-height: 53px;
  padding: 4px 6px;
  text-align: left;
  width: 100%;
}
.subtype-button:hover, .subtype-button.selected { background: var(--paper-warm); border-color: var(--line-strong); }
.subtype-thumb { border: 1px solid var(--line); border-radius: 6px; flex: 0 0 44px; height: 44px; object-fit: cover; width: 44px; }
.subtype-copy { min-width: 0; }
.subtype-code { color: var(--forest-2); display: block; font-size: 11px; font-weight: 800; line-height: 1.1; }
.subtype-label { display: block; font-size: 11px; line-height: 1.25; margin-top: 3px; overflow-wrap: anywhere; }
.subtype-state { color: var(--forest-2); font-size: 10px; margin-left: auto; }
.library-note {
  background: var(--amber-soft);
  border: 1px solid color-mix(in srgb, var(--amber) 36%, var(--line));
  border-radius: 9px;
  color: var(--ink-soft);
  font-size: 10px;
  line-height: 1.45;
  margin-top: 18px;
  padding: 11px;
}
.library-backdrop { display: none; }
.note-history { border-top: 1px solid var(--line); margin-top: 18px; padding-top: 15px; }
.note-history[hidden] { display: none; }
.note-history summary { color: var(--muted); cursor: pointer; font-size: 11px; }
.history-list { display: grid; gap: 7px; margin-top: 9px; }
.history-item {
  align-items: center;
  background: var(--paper-alt);
  border: 1px solid var(--line);
  border-radius: 7px;
  color: var(--ink-soft);
  display: flex;
  font-size: 10px;
  gap: 7px;
  justify-content: space-between;
  padding: 7px;
  text-align: left;
  width: 100%;
}
.history-item:hover { border-color: var(--moss); }
.history-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@keyframes page-turn-forward {
  0% { transform: rotateY(0deg) translateX(0); }
  45% { transform: rotateY(-4deg) translateX(-4px); }
  100% { transform: rotateY(0deg) translateX(0); }
}
@keyframes page-turn-back {
  0% { transform: rotateY(0deg) translateX(0); }
  45% { transform: rotateY(4deg) translateX(4px); }
  100% { transform: rotateY(0deg) translateX(0); }
}
@media (max-width: 1260px) {
  .notebook-workspace { grid-template-columns: 122px minmax(0, 1fr) 280px; }
  .notebook-column { padding-inline: 22px; }
  .page { padding-inline: 30px; }
}
@media (max-width: 1080px) {
  .notebook-workspace { grid-template-columns: 112px minmax(0, 1fr); }
  .library-toggle { display: inline-flex; }
  .library-drawer {
    bottom: 0;
    box-shadow: -24px 0 55px rgba(0, 0, 0, .18);
    max-width: calc(100vw - 22px);
    position: fixed;
    right: 0;
    top: 76px;
    transform: translateX(110%);
    transition: transform .35s cubic-bezier(.22, .75, .2, 1);
    width: 330px;
  }
  .library-drawer[data-open="true"] { transform: translateX(0); }
  .library-backdrop {
    background: rgba(22, 28, 20, .32);
    bottom: 0;
    display: block;
    left: 0;
    opacity: 0;
    pointer-events: none;
    position: fixed;
    right: 0;
    top: 76px;
    transition: opacity .25s ease;
    z-index: 19;
  }
  .library-backdrop[data-open="true"] { opacity: 1; pointer-events: auto; }
}
@media (max-width: 760px) {
  .topbar {
    gap: 9px;
    grid-template-columns: minmax(0, 1fr) auto;
    min-height: 68px;
    padding-inline: 13px;
  }
  .brand-mark { height: 29px; width: 29px; }
  .wordmark { font-size: 22px; }
  .primary-nav, .global-search { display: none; }
  .topbar-tools { gap: 6px; }
  .new-note { font-size: 0; min-height: 38px; padding: 0; width: 42px; }
  .new-note::before { color: #fffdf4; content: "+"; font-size: 22px; font-weight: 300; }
.theme-toggle { font-size: 0; min-height: 38px; padding: 0; width: 48px; }
.theme-toggle::before { content: "Mode"; font-size: 10px; font-weight: 700; letter-spacing: .02em; }
  .profile-button { display: none; }
  .notebook-workspace { display: block; min-height: 0; }
  .phase-rail { border-bottom: 1px solid var(--line); border-right: 0; padding: 12px 13px 10px; }
  .phase-rail > .rail-kicker { padding-inline: 4px; }
  .phase-list { display: flex; gap: 6px; margin: 10px 0 0; overflow-x: auto; padding-bottom: 3px; }
  .phase-list::before { display: none; }
  .phase-step { flex: 0 0 auto; }
  .phase-button { align-items: center; background: var(--paper-alt); border: 1px solid var(--line); border-radius: 9px; gap: 7px; min-height: 44px; padding: 5px 8px 5px 5px; width: auto; }
  .phase-number { flex-basis: 29px; height: 29px; }
  .phase-copy { padding: 0; }
  .phase-label { font-size: 11px; }
  .phase-detail, .phase-status { display: none; }
  .phase-step[data-state="active"] .phase-button { border-color: var(--moss); }
  .rail-footer { display: none; }
  .notebook-column { padding: 14px 11px 28px; }
  .mobile-toolbar { margin-bottom: 11px; }
  .mobile-toolbar .rail-kicker { font-size: 9px; }
  .page-state { font-size: 11px; }
  .library-toggle { min-height: 36px; }
  .notebook-spread { border-radius: 14px; display: block; min-height: 0; }
  .notebook-spread::before { display: none; }
  .notebook-spread.is-turning-forward, .notebook-spread.is-turning-back { animation-duration: .48s; }
  .page { padding: 24px 19px 25px; }
  .page-left { border-bottom: 1px solid var(--line); border-right: 0; }
  .page-right { min-height: 460px; }
  .note-title { font-size: 27px; margin-top: 17px; }
  .page-lede { font-size: 12px; }
  .evidence-board { margin-top: 19px; }
  .board-card img { min-height: 64px; }
  .board-card:first-child img { min-height: 136px; }
  .evidence-fields { grid-template-columns: 1fr; }
  .observation-text, .working-read p, .read-list, .change-list, .next-question p { font-size: 12px; }
  .page-nav { grid-template-columns: 1fr 1fr; margin-top: 11px; padding: 8px; }
  .page-progress { grid-column: 1 / -1; grid-row: 1; }
  .page-nav .quiet-button, .page-nav .primary-button { min-height: 42px; min-width: 0; width: 100%; }
  .page-nav .primary-button { grid-column: 2; grid-row: 2; }
  .page-nav .quiet-button { grid-column: 1; grid-row: 2; }
  .auth-form { align-items: stretch; flex-direction: column; }
  .auth-form input { width: 100%; }
  .auth-form .primary-button { width: 100%; }
  .library-drawer { max-width: calc(100vw - 10px); top: 68px; width: min(340px, calc(100vw - 10px)); }
  .library-backdrop { top: 68px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: .001ms !important;
  }
}
@media (prefers-contrast: more) {
  :root { --line: #a3a79b; --line-strong: #707768; }
  body[data-theme="dark"] { --line: #83907f; --line-strong: #b5c3a8; }
}
</style>
</head>
<body data-theme="light">
<div class="app-shell">
  <header class="topbar">
    <a class="brand-lockup" href="/" aria-label="helpme.green home">
      <img class="brand-mark" src="/assets/brand-mark.png" alt="" width="33" height="33">
      <span class="wordmark">helpme<span>.green</span></span>
    </a>
    <nav class="primary-nav" aria-label="Primary navigation">
      <a class="nav-link active" href="#notebook">Lab Notebook</a>
      <a class="nav-link" href="#notebook">Explore</a>
      <a class="nav-link" href="#library">Library</a>
    </nav>
    <div class="topbar-tools">
      <label class="global-search">
        <span class="sr-only">Search notes and materials</span>
        <input id="globalSearch" type="search" autocomplete="off" placeholder="Search notes, materials...">
      </label>
      <button class="new-note" id="newNote" type="button">New note</button>
      <button class="theme-toggle" id="themeToggle" type="button">Dark mode</button>
      <button class="profile-button" type="button" aria-label="Profile">MR</button>
    </div>
  </header>

  <main class="notebook-workspace" id="notebook">
    <aside class="phase-rail" aria-label="Investigation phases">
      <span class="rail-kicker">Investigation</span>
      <ol class="phase-list" id="phaseList"></ol>
      <div class="rail-footer">
        <div class="rail-page-count" id="railPageCount">Phase 1 of 5</div>
        <div class="rail-progress" aria-label="Overall progress"><span id="railProgress" style="width:20%"></span></div>
      </div>
    </aside>

    <section class="notebook-column" aria-label="Material investigation notebook">
      <div class="mobile-toolbar">
        <span class="rail-kicker">Working notebook</span>
        <div>
          <span class="page-state" id="pageState">Phase 1 of 5</span>
          <button class="library-toggle" id="libraryToggle" type="button">Material library</button>
        </div>
      </div>

      <section class="auth-card" id="authGate" hidden>
        <p>This notebook can connect to a local assistant when you want a second read. Enter the connection key to enable it.</p>
        <form class="auth-form" id="authForm">
          <label class="sr-only" for="token">Connection key</label>
          <input id="token" type="password" autocomplete="off" placeholder="Connection key">
          <button class="primary-button" type="submit">Connect</button>
        </form>
        <div class="auth-error" id="authError" hidden></div>
      </section>

      <div class="notebook-stage">
        <div class="notebook-spread" id="notebookSpread">
          <article class="page page-left" aria-label="Investigation notes">
            <header class="page-header">
              <span class="note-date">NOTE — 11 AUG 2026</span>
              <span class="note-tag" id="leftPageTag">OBSERVE</span>
            </header>
            <label class="sr-only" for="noteTitle">Investigation title</label>
            <input class="note-title" id="noteTitle" maxlength="90" value="New material note" aria-label="Investigation title">
            <p class="page-lede" id="pageLede">Describe what is in front of you, what is happening with it, or what you need to understand. Your words stay attached to this phase.</p>

            <div class="evidence-board" aria-label="Material examples">
              <figure class="board-card">
                <img id="boardImagePrimary" src="/assets/material-plastics.webp" alt="Plastic material example">
              </figure>
              <figure class="board-card">
                <img id="boardImageSecondary" src="/assets/material-paper.webp" alt="Paper and board example">
              </figure>
              <figure class="board-card">
                <img id="boardImageTertiary" src="/assets/material-metals.webp" alt="Metal material example">
              </figure>
            </div>
            <div class="board-caption">Library examples — real scrap looks, not proof of what this is</div>

            <section aria-labelledby="observationsTitle">
              <h2 class="section-title" id="observationsTitle"><span>Observations</span><span id="observationCount">0 saved</span></h2>
              <ol class="observation-list" id="observationList"></ol>
            </section>

            <section class="evidence-capture" aria-labelledby="sampleEvidenceTitle">
              <h2 class="section-title" id="sampleEvidenceTitle"><span>Your material</span><span id="evidenceCount">0 photos</span></h2>
              <p class="evidence-intro">Add a photo of the real scrap if you have one. The assistant compares your notes with the library examples. Your photos stay here for now.</p>
              <div class="evidence-photo-row" id="evidencePhotos"></div>
              <label class="evidence-upload" for="evidencePhotoInput">Add a photo</label>
              <input class="evidence-upload-input" id="evidencePhotoInput" type="file" accept="image/*" capture="environment" multiple>
              <div class="evidence-fields">
                <label class="evidence-field" for="evidenceForm">What form is the sample?
                  <select id="evidenceForm">
                    <option value="">Choose sample form</option>
                    <option value="whole">Whole piece</option>
                    <option value="flakes">Flakes / chips</option>
                    <option value="granules">Granules / pellets</option>
                    <option value="powder">Powder / dust</option>
                    <option value="mixed">Mixed pieces</option>
                    <option value="closed">Closed container (do not open)</option>
                  </select>
                </label>
                <label class="evidence-field" for="evidenceCondition">What is it like?
                  <select id="evidenceCondition">
                    <option value="">Choose condition</option>
                    <option value="clean">Clean / intact</option>
                    <option value="worn">Worn / weathered</option>
                    <option value="dirty">Dirty / contaminated</option>
                    <option value="mixed">Mixed / attached</option>
                    <option value="damaged">Cut / damaged</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </label>
                <label class="evidence-field" for="evidenceOrigin">Where did it come from? (optional)
                  <input id="evidenceOrigin" type="text" maxlength="140" placeholder="Where did it come from?">
                </label>
              </div>
              <div class="evidence-guidance" id="evidenceGuidance" role="note" hidden>
                <strong id="evidenceGuidanceTitle"></strong>
                <p id="evidenceGuidanceText"></p>
              </div>
              <label class="evidence-field evidence-detail" for="evidenceDetails">What should the assistant look at? (optional)
                <input id="evidenceDetails" type="text" maxlength="220" placeholder="For example: surface, stiffness, colour, or attached parts">
              </label>
              <div class="evidence-note" id="evidenceNote">No photo yet. Your notes are enough to start.</div>
            </section>

            <section class="reference-section" aria-labelledby="referencesTitle">
              <h2 class="section-title" id="referencesTitle"><span>Library examples</span><span>Library</span></h2>
              <div class="reference-chips" id="referenceChips"></div>
              <div class="comparison-actions">
                <button class="text-button" id="compareEvidence" type="button">Compare with assistant</button>
                <span class="comparison-hint" id="comparisonHint">Your notes + library examples</span>
              </div>
            </section>

            <form class="observation-composer" id="composer" aria-busy="false">
              <label class="sr-only" for="message">Add an observation</label>
              <textarea id="message" rows="3" placeholder="Add an observation..."></textarea>
              <div class="composer-footer">
                <span class="composer-hint">Enter to save · Shift+Enter for a new line</span>
                <button class="save-observation" id="send" type="submit">Save observation</button>
              </div>
            </form>
            <div class="status-note" id="statusNote" aria-live="polite">Autosaved in this browser. Nothing is lost when you move between phases.</div>
          </article>

          <article class="page page-right" aria-label="Assistant's first look">
            <section class="working-read">
              <span class="page-kicker">Assistant's first look</span>
              <h2 id="workingTitle">Start with the first look</h2>
              <p id="workingRead">No answer is assumed. Add a note and keep the first look, the open question, and the library examples together.</p>
            </section>
            <section class="read-section" aria-labelledby="evidenceTitle">
              <h2 class="section-title" id="evidenceTitle">What we have so far</h2>
              <ul class="read-list" id="readEvidence"></ul>
            </section>
            <section class="read-section change" aria-labelledby="changeTitle">
              <h2 class="section-title" id="changeTitle">What could change this</h2>
              <ul class="change-list" id="changeList"></ul>
            </section>
            <section class="next-question" aria-labelledby="nextQuestionTitle">
              <h2 class="section-title" id="nextQuestionTitle">Next question</h2>
              <p id="nextQuestion">What do you see, and what would you like to understand?</p>
              <button class="text-button" id="usePrompt" type="button">Use as observation prompt</button>
            </section>
            <section class="assistant-read" id="assistantRead" hidden>
              <span class="page-kicker">Assistant's note — saved here</span>
              <p id="assistantText"></p>
              <p class="source-note" id="sourceNote"></p>
            </section>
            <section class="comparison-read" id="comparisonRead" hidden>
              <span class="page-kicker">Assistant comparison — first read</span>
              <p id="comparisonText"></p>
              <p class="source-note" id="comparisonSourceNote"></p>
              <p class="comparison-disclaimer">This uses your notes and the library examples. It is not a test or a final answer.</p>
            </section>
          </article>
        </div>

        <nav class="page-nav" aria-label="Notebook page navigation">
          <button class="quiet-button" id="previousPage" type="button">Previous phase</button>
          <div class="page-progress" id="pageProgress" aria-label="Phase progress"></div>
          <button class="primary-button" id="nextPage" type="button">Continue to identification</button>
        </nav>
        <details class="note-history" id="noteHistory" hidden>
          <summary>Previous notes kept on this device</summary>
          <div class="history-list" id="historyList"></div>
        </details>
      </div>
    </section>

    <aside class="library-drawer" id="library" data-open="true" aria-label="Material library">
      <header class="library-header">
        <div>
      <span class="library-kicker">Examples only</span>
          <h2>Material library</h2>
        </div>
        <button class="library-close" id="libraryClose" type="button">Close</button>
      </header>
      <label class="material-search">
        <span class="sr-only">Search materials</span>
        <input id="materialSearch" type="search" autocomplete="off" placeholder="Search materials...">
      </label>
      <div class="category-list" id="categoryList"></div>
      <div class="library-note">These are used or worked-on materials, not a way to name a plastic or metal with certainty. Keep your notes, where it came from, and any test with the page.</div>
    </aside>
    <div class="library-backdrop" id="libraryBackdrop" data-open="false"></div>
  </main>
</div>

<script>
(() => {
  const STORAGE_KEY = "helpme.green.notebook.v2";
  const THEME_KEY = "helpme.green.theme";
  const phases = [
    {id: "observe", label: "Observe", detail: "What is in front of you?", heading: "Start with the first look", lede: "Describe what is in front of you, what is happening with it, or what you need to understand. Your words stay attached to this phase.", question: "What do you see, and what would you like to understand?", change: ["A clearer view of surface, form, or condition.", "A note about what is known, suspected, or still open."]},
    {id: "identify", label: "Identify", detail: "Name with care", heading: "Name the material with care", lede: "Use the library to keep a helpful example nearby. A visual match is a starting point, not a confirmed answer.", question: "Which material type is worth checking next?", change: ["A label, document, or test result that supports the name.", "A mixed, coated, or layered piece that changes the first read."]},
    {id: "understand", label: "Understand", detail: "Keep the details", heading: "Keep the details together", lede: "Keep what you saw, the examples you chose, and the question you are trying to answer on the same page.", question: "What would change how you see this material?", change: ["A missing detail about its condition or past use.", "Something that does not fit the first read."]},
    {id: "options", label: "Options", detail: "Compare routes", heading: "Compare possible routes", lede: "Look at possible directions before you choose one. Keep the limits and the next check in view.", question: "Which direction is worth looking into first, and why?", change: ["A limit that makes one route less useful.", "A missing source, measurement, or expert check."]},
    {id: "next", label: "Next steps", detail: "Choose the next check", heading: "Choose the next useful check", lede: "End with a clear, reversible next action linked to your question—not a conclusion that goes beyond what you know.", question: "What is the simplest useful next check?", change: ["A new detail that answers the open question.", "A result that makes the next choice clearer."]}
  ];
  const categories = [
    {id: "plastics", label: "Plastics", image: "/assets/material-plastics.webp", subtypes: [
      {id: "pp", code: "PP", label: "Polypropylene", image: "/assets/material-pp.webp"},
      {id: "hdpe", code: "HDPE", label: "High-density polyethylene", image: "/assets/material-hdpe.webp"},
      {id: "ldpe", code: "LDPE", label: "Low-density polyethylene", image: "/assets/material-ldpe.webp"},
      {id: "abs", code: "ABS", label: "Acrylonitrile butadiene styrene", image: "/assets/material-abs.webp"},
      {id: "pet", code: "PET", label: "Polyethylene terephthalate", image: "/assets/material-pet.webp"},
      {id: "pvc", code: "PVC", label: "Polyvinyl chloride", image: "/assets/material-pvc.webp"},
      {id: "ps", code: "PS", label: "Polystyrene", image: "/assets/material-ps.webp"}
    ]},
    {id: "metals", label: "Metals", image: "/assets/material-metals.webp", subtypes: [
      {id: "steel", code: "Steel", label: "Carbon steel", image: "/assets/material-steel.webp"},
      {id: "aluminium", code: "Al", label: "Aluminium", image: "/assets/material-aluminium.webp"},
      {id: "copper", code: "Cu", label: "Copper", image: "/assets/material-copper.webp"},
      {id: "brass", code: "Brass", label: "Brass", image: "/assets/material-brass.webp"},
      {id: "stainless", code: "SS", label: "Stainless steel", image: "/assets/material-stainless.webp"},
      {id: "mixed-metal", code: "Mixed", label: "Mixed metal", image: "/assets/material-mixed-metal.webp"}
    ]},
    {id: "cable", label: "Cable & Harness", image: "/assets/material-cable-harness.webp", subtypes: [
      {id: "copper-cable", code: "Cable", label: "Copper conductor cable", image: "/assets/material-cable-harness.webp"},
      {id: "aluminium-cable", code: "Cable", label: "Aluminium conductor cable", image: "/assets/material-cable-harness.webp"},
      {id: "control-harness", code: "Harness", label: "Control harness", image: "/assets/material-cable-harness.webp"},
      {id: "data-cable", code: "Data", label: "Data cable", image: "/assets/material-cable-harness.webp"},
      {id: "coaxial", code: "Coax", label: "Coaxial cable", image: "/assets/material-cable-harness.webp"}
    ]},
    {id: "paper", label: "Paper & Board", image: "/assets/material-paper.webp", subtypes: [
      {id: "corrugated", code: "Board", label: "Corrugated board", image: "/assets/material-paper.webp"},
      {id: "kraft", code: "Paper", label: "Kraft paper", image: "/assets/material-paper.webp"},
      {id: "office", code: "Paper", label: "Office paper", image: "/assets/material-paper.webp"},
      {id: "coated", code: "Paper", label: "Coated paper", image: "/assets/material-paper.webp"},
      {id: "fiberboard", code: "Board", label: "Fiberboard", image: "/assets/material-paper.webp"}
    ]},
    {id: "glass", label: "Glass", image: "/assets/material-glass.webp", subtypes: [
      {id: "clear-glass", code: "Glass", label: "Clear glass", image: "/assets/material-glass.webp"},
      {id: "green-glass", code: "Glass", label: "Green glass", image: "/assets/material-glass.webp"},
      {id: "amber-glass", code: "Glass", label: "Amber glass", image: "/assets/material-glass.webp"},
      {id: "glass-fiber", code: "Fiber", label: "Glass fiber", image: "/assets/material-glass.webp"}
    ]},
    {id: "textiles", label: "Textiles", image: "/assets/material-textiles.webp", subtypes: [
      {id: "cotton", code: "Fiber", label: "Cotton", image: "/assets/material-textiles.webp"},
      {id: "polyester", code: "Fiber", label: "Polyester", image: "/assets/material-textiles.webp"},
      {id: "nylon", code: "Fiber", label: "Nylon", image: "/assets/material-textiles.webp"},
      {id: "wool", code: "Fiber", label: "Wool", image: "/assets/material-textiles.webp"},
      {id: "blend", code: "Blend", label: "Blended textile", image: "/assets/material-textiles.webp"},
      {id: "elastane", code: "Fiber", label: "Elastane", image: "/assets/material-textiles.webp"}
    ]}
  ];

  const elements = {
    body: document.body,
    phaseList: document.getElementById("phaseList"),
    pageState: document.getElementById("pageState"),
    railPageCount: document.getElementById("railPageCount"),
    railProgress: document.getElementById("railProgress"),
    leftPageTag: document.getElementById("leftPageTag"),
    pageLede: document.getElementById("pageLede"),
    noteTitle: document.getElementById("noteTitle"),
    boardImagePrimary: document.getElementById("boardImagePrimary"),
    boardImageSecondary: document.getElementById("boardImageSecondary"),
    boardImageTertiary: document.getElementById("boardImageTertiary"),
    observationList: document.getElementById("observationList"),
    observationCount: document.getElementById("observationCount"),
    evidencePhotos: document.getElementById("evidencePhotos"),
    evidencePhotoInput: document.getElementById("evidencePhotoInput"),
    evidenceCount: document.getElementById("evidenceCount"),
    evidenceForm: document.getElementById("evidenceForm"),
    evidenceCondition: document.getElementById("evidenceCondition"),
    evidenceOrigin: document.getElementById("evidenceOrigin"),
    evidenceDetails: document.getElementById("evidenceDetails"),
    evidenceNote: document.getElementById("evidenceNote"),
    evidenceGuidance: document.getElementById("evidenceGuidance"),
    evidenceGuidanceTitle: document.getElementById("evidenceGuidanceTitle"),
    evidenceGuidanceText: document.getElementById("evidenceGuidanceText"),
    referenceChips: document.getElementById("referenceChips"),
    compareEvidence: document.getElementById("compareEvidence"),
    comparisonHint: document.getElementById("comparisonHint"),
    composer: document.getElementById("composer"),
    message: document.getElementById("message"),
    send: document.getElementById("send"),
    statusNote: document.getElementById("statusNote"),
    workingTitle: document.getElementById("workingTitle"),
    workingRead: document.getElementById("workingRead"),
    readEvidence: document.getElementById("readEvidence"),
    changeList: document.getElementById("changeList"),
    nextQuestion: document.getElementById("nextQuestion"),
    usePrompt: document.getElementById("usePrompt"),
    assistantRead: document.getElementById("assistantRead"),
    assistantText: document.getElementById("assistantText"),
    sourceNote: document.getElementById("sourceNote"),
    comparisonRead: document.getElementById("comparisonRead"),
    comparisonText: document.getElementById("comparisonText"),
    comparisonSourceNote: document.getElementById("comparisonSourceNote"),
    previousPage: document.getElementById("previousPage"),
    nextPage: document.getElementById("nextPage"),
    pageProgress: document.getElementById("pageProgress"),
    noteHistory: document.getElementById("noteHistory"),
    historyList: document.getElementById("historyList"),
    library: document.getElementById("library"),
    libraryToggle: document.getElementById("libraryToggle"),
    libraryClose: document.getElementById("libraryClose"),
    libraryBackdrop: document.getElementById("libraryBackdrop"),
    materialSearch: document.getElementById("materialSearch"),
    categoryList: document.getElementById("categoryList"),
    globalSearch: document.getElementById("globalSearch"),
    newNote: document.getElementById("newNote"),
    themeToggle: document.getElementById("themeToggle"),
    authGate: document.getElementById("authGate"),
    authForm: document.getElementById("authForm"),
    authInput: document.getElementById("token"),
    authError: document.getElementById("authError")
  };

  let sessionId = null;
  let conversationGeneration = 0;
  let token = "";
  let starting = false;
  let requestPending = false;
  let comparisonPending = false;
  let turnTimer = null;

  function blankEvidence() {
    return {photos: [], form: "", condition: "", origin: "", details: ""};
  }
  function blankPage() {
    return {draft: "", observations: [], references: [], reply: "", sources: [], comparison: "", comparisonSources: [], evidence: blankEvidence()};
  }
  function freshState() {
    return {
      title: "New material note",
      currentPhase: 0,
      selectedCategory: "plastics",
      pages: phases.map(() => blankPage()),
      history: []
    };
  }
  function migrateMaterialAsset(value) {
    if (typeof value !== "string") return value;
    return value.replace(/^(\/assets\/material-[^?]+)\.png$/, "$1.webp");
  }
  function isAssistantFailureText(value) {
    return typeof value === "string" && /^(I couldn.?t get a response from the local model just now|I couldn.?t answer that right now)/i.test(value.trim());
  }
  function validState(value) {
    if (!value || !Array.isArray(value.pages)) return freshState();
    const next = freshState();
    next.title = typeof value.title === "string" ? value.title : next.title;
    next.currentPhase = Number.isInteger(value.currentPhase) ? Math.min(Math.max(value.currentPhase, 0), phases.length - 1) : 0;
    next.selectedCategory = categories.some((category) => category.id === value.selectedCategory) ? value.selectedCategory : "plastics";
    next.history = Array.isArray(value.history) ? value.history.slice(0, 5) : [];
    next.pages = phases.map((_, index) => {
      const source = value.pages[index] || {};
      return {
        draft: typeof source.draft === "string" ? source.draft : "",
        observations: Array.isArray(source.observations) ? source.observations.filter((item) => typeof item === "string").slice(0, 80) : [],
        references: Array.isArray(source.references) ? source.references.filter((item) => item && typeof item.id === "string").slice(0, 40).map((item) => Object.assign({}, item, {image: migrateMaterialAsset(item.image)})) : [],
        reply: typeof source.reply === "string" && !isAssistantFailureText(source.reply) ? source.reply : "",
        sources: Array.isArray(source.sources) ? source.sources.slice(0, 20) : [],
        comparison: typeof source.comparison === "string" && !isAssistantFailureText(source.comparison) ? source.comparison : "",
        comparisonSources: Array.isArray(source.comparisonSources) ? source.comparisonSources.slice(0, 20) : [],
        evidence: validEvidence(source.evidence)
      };
    });
    return next;
  }
  function validEvidence(value) {
    const evidence = blankEvidence();
    if (!value || typeof value !== "object") return evidence;
    const allowedForms = ["", "whole", "flakes", "granules", "powder", "mixed", "closed"];
    const allowedConditions = ["", "clean", "worn", "dirty", "mixed", "damaged", "unknown"];
    evidence.form = allowedForms.includes(value.form) ? value.form : "";
    evidence.condition = allowedConditions.includes(value.condition) ? value.condition : "";
    evidence.origin = typeof value.origin === "string" ? value.origin.slice(0, 140) : "";
    evidence.details = typeof value.details === "string" ? value.details.slice(0, 220) : "";
    evidence.photos = Array.isArray(value.photos) ? value.photos.filter((photo) => (
      photo && typeof photo.dataUrl === "string" && photo.dataUrl.startsWith("data:image/") && photo.dataUrl.length <= 1600000
    )).slice(0, 3).map((photo, index) => ({
      id: typeof photo.id === "string" ? photo.id : "photo-" + index,
      name: typeof photo.name === "string" ? photo.name.slice(0, 80) : "Sample photo",
      dataUrl: photo.dataUrl
    })) : [];
    return evidence;
  }
  function loadState() {
    try { return validState(JSON.parse(localStorage.getItem(STORAGE_KEY) || "null")); }
    catch (_) { return freshState(); }
  }
  let state = loadState();

  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (_) { /* Local persistence is best effort. */ }
  }
  function activePage() { return state.pages[state.currentPhase]; }
  function findSubtype(id) {
    for (const category of categories) {
      const subtype = category.subtypes.find((item) => item.id === id);
      if (subtype) return {category, subtype};
    }
    return null;
  }
  function phaseHasWork(index) {
    const page = state.pages[index];
    return Boolean(page && (
      page.observations.length || page.references.length || page.reply || page.comparison || page.draft.trim() ||
      page.evidence.photos.length || page.evidence.condition || page.evidence.origin.trim() || page.evidence.details.trim()
    ));
  }
  function phaseState(index) {
    if (index === state.currentPhase) return "active";
    if (phaseHasWork(index) || index < state.currentPhase) return "complete";
    return "pending";
  }
  function setTheme(theme) {
    const next = theme === "dark" ? "dark" : "light";
    elements.body.dataset.theme = next;
    elements.themeToggle.textContent = next === "dark" ? "Light mode" : "Dark mode";
    document.querySelector('meta[name="theme-color"]').setAttribute("content", next === "dark" ? "#101a14" : "#f4f0e7");
    try { localStorage.setItem(THEME_KEY, next); } catch (_) {}
  }
  function loadTheme() {
    try { return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light"; }
    catch (_) { return "light"; }
  }
  function renderPhaseRail() {
    elements.phaseList.replaceChildren();
    phases.forEach((phase, index) => {
      const item = document.createElement("li");
      item.className = "phase-step";
      item.dataset.state = phaseState(index);
      const button = document.createElement("button");
      button.className = "phase-button";
      button.type = "button";
      button.setAttribute("aria-label", "Open phase " + (index + 1) + ": " + phase.label);
      const number = document.createElement("span");
      number.className = "phase-number";
      number.textContent = String(index + 1);
      const copy = document.createElement("span");
      copy.className = "phase-copy";
      const label = document.createElement("span");
      label.className = "phase-label";
      label.textContent = phase.label;
      const detail = document.createElement("span");
      detail.className = "phase-detail";
      detail.textContent = phase.detail;
      const status = document.createElement("span");
      status.className = "phase-status";
      status.textContent = phaseState(index) === "complete" ? "Saved" : phaseState(index) === "active" ? "In progress" : "Not started";
      copy.append(label, detail, status);
      button.append(number, copy);
      button.addEventListener("click", () => goToPhase(index));
      item.appendChild(button);
      elements.phaseList.appendChild(item);
    });
    const progress = ((state.currentPhase + 1) / phases.length) * 100;
    elements.railPageCount.textContent = "Phase " + (state.currentPhase + 1) + " of " + phases.length;
    elements.railProgress.style.width = progress + "%";
  }
  function renderPageProgress() {
    elements.pageProgress.replaceChildren();
    phases.forEach((phase, index) => {
      const dot = document.createElement("button");
      dot.className = "page-dot";
      dot.type = "button";
      dot.setAttribute("aria-label", "Go to phase " + (index + 1) + ": " + phase.label);
      if (index === state.currentPhase) dot.classList.add("active");
      if (phaseState(index) === "complete" && index !== state.currentPhase) dot.classList.add("complete");
      dot.addEventListener("click", () => goToPhase(index));
      elements.pageProgress.appendChild(dot);
    });
  }
  function renderObservations(page) {
    elements.observationList.replaceChildren();
    elements.observationCount.textContent = page.observations.length + " saved";
    if (!page.observations.length) {
      const empty = document.createElement("li");
      empty.className = "empty-row";
      empty.textContent = "Your observations will stay on this page.";
      elements.observationList.appendChild(empty);
      return;
    }
    page.observations.forEach((observation, index) => {
      const row = document.createElement("li");
      row.className = "observation-row";
      const number = document.createElement("span");
      number.className = "observation-index";
      number.textContent = String(index + 1).padStart(2, "0");
      const text = document.createElement("span");
      text.className = "observation-text";
      text.textContent = observation;
      row.append(number, text);
      elements.observationList.appendChild(row);
    });
  }
  function renderEvidence(page) {
    const evidence = page.evidence || blankEvidence();
    const formGuidance = {
      whole: {
        title: "Whole piece",
        text: "A photo can show shape and surface. It still cannot confirm the exact material, grade, or blend."
      },
      flakes: {
        title: "Flakes / chips",
        text: "A photo can show colour, shape, and visible mix. If safe, add an overall view and a close-up. It cannot confirm the exact material from appearance alone."
      },
      granules: {
        title: "Granules / pellets",
        text: "A photo can show colour, size, shape, and whether the sample looks mixed. If safe, add a close-up with a size reference. It cannot confirm the polymer, alloy, or blend."
      },
      powder: {
        title: "Powder / dust",
        text: "Photos can show colour and texture, but not reliably name the material. If safe, photograph the container or settled sample. If the dust may be unsafe, keep it closed and do not spread it just for a photo."
      },
      mixed: {
        title: "Mixed pieces",
        text: "Treat this as a mixture first. If safe, add an overview and a close-up of the different pieces. The assistant will describe what is visible instead of forcing one material name."
      },
      closed: {
        title: "Closed container",
        text: "Keep an unknown sample closed. A photo of the container, label, and source can help, but a photo alone cannot name what is inside."
      }
    };
    elements.evidencePhotos.replaceChildren();
    elements.evidenceCount.textContent = evidence.photos.length + " photo" + (evidence.photos.length === 1 ? "" : "s");
    if (!evidence.photos.length) {
      const empty = document.createElement("span");
      empty.className = "evidence-empty";
      empty.textContent = "Add a photo of the real piece when you have one.";
      elements.evidencePhotos.appendChild(empty);
    } else {
      evidence.photos.forEach((photo, index) => {
        const frame = document.createElement("div");
        frame.className = "evidence-photo";
        const image = document.createElement("img");
        image.src = photo.dataUrl;
        image.alt = "User sample photo " + (index + 1);
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", "Remove user sample photo " + (index + 1));
        remove.addEventListener("click", () => {
          activePage().evidence.photos = activePage().evidence.photos.filter((item) => item.id !== photo.id);
          activePage().comparison = "";
          activePage().comparisonSources = [];
          saveState();
          renderAll();
        });
        frame.append(image, remove);
        elements.evidencePhotos.appendChild(frame);
      });
    }
    elements.evidenceForm.value = evidence.form;
    elements.evidenceCondition.value = evidence.condition;
    elements.evidenceOrigin.value = evidence.origin;
    elements.evidenceDetails.value = evidence.details;
    const guidance = formGuidance[evidence.form];
    elements.evidenceGuidance.hidden = !guidance;
    if (guidance) {
      elements.evidenceGuidanceTitle.textContent = guidance.title;
      elements.evidenceGuidanceText.textContent = guidance.text;
    } else {
      elements.evidenceGuidanceTitle.textContent = "";
      elements.evidenceGuidanceText.textContent = "";
    }
    const detail = evidence.form || evidence.condition || evidence.origin || evidence.details;
    elements.evidenceNote.textContent = evidence.photos.length
      ? "Your photo" + (evidence.photos.length === 1 ? " stays" : "s stay") + " here. The assistant will keep the sample form and limits with the comparison."
      : detail
        ? "These details stay with this page. Add a photo when you have one."
        : "No photo yet. Your notes are enough to start.";
  }
  function renderReferences(page) {
    elements.referenceChips.replaceChildren();
    if (!page.references.length) {
      const empty = document.createElement("span");
      empty.className = "reference-empty";
      empty.textContent = "Choose a family or subtype from the library when it helps.";
      elements.referenceChips.appendChild(empty);
      return;
    }
    page.references.forEach((reference) => {
      const chip = document.createElement("span");
      chip.className = "reference-chip";
      const image = document.createElement("img");
      image.src = reference.image;
      image.alt = "";
      const label = document.createElement("span");
      label.textContent = reference.code + " — " + reference.label;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", "Remove " + reference.label);
      remove.addEventListener("click", () => {
        activePage().references = activePage().references.filter((item) => item.id !== reference.id);
        activePage().comparison = "";
        activePage().comparisonSources = [];
        saveState();
        renderAll();
      });
      chip.append(image, label, remove);
      elements.referenceChips.appendChild(chip);
    });
  }
  function renderRead(page, phase) {
    elements.workingTitle.textContent = phase.heading;
    elements.pageLede.textContent = phase.lede;
    elements.nextQuestion.textContent = phase.question;
    elements.changeList.replaceChildren();
    phase.change.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      elements.changeList.appendChild(item);
    });
    elements.readEvidence.replaceChildren();
    const evidence = [];
    if (page.observations.length) evidence.push(page.observations.length + " note" + (page.observations.length === 1 ? "" : "s") + " saved on this phase.");
    if (page.references.length) evidence.push(page.references.length + " library example" + (page.references.length === 1 ? "" : "s") + " kept with this phase.");
    if (!evidence.length) evidence.push("Nothing has been added to this phase yet.");
    evidence.push("The library images are examples; a material name still needs context or a test.");
    evidence.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      elements.readEvidence.appendChild(item);
    });
    if (page.reply) {
      elements.assistantRead.hidden = false;
      elements.assistantText.textContent = page.reply;
      const sources = page.sources || [];
      elements.sourceNote.textContent = sources.length ? sources.map((source) => source.label || "Reference").join(" · ") : "No source linked to this read yet.";
    } else {
      elements.assistantRead.hidden = true;
      elements.assistantText.textContent = "";
      elements.sourceNote.textContent = "";
    }
    if (page.comparison) {
      elements.comparisonRead.hidden = false;
      elements.comparisonText.textContent = page.comparison;
      const comparisonSources = page.comparisonSources || [];
      elements.comparisonSourceNote.textContent = comparisonSources.length
        ? comparisonSources.map((source) => source.label || "Reference").join(" · ")
        : "No source linked to this comparison yet.";
    } else {
      elements.comparisonRead.hidden = true;
      elements.comparisonText.textContent = "";
      elements.comparisonSourceNote.textContent = "";
    }
  }
  function renderNotebook() {
    const page = activePage();
    const phase = phases[state.currentPhase];
    const difficultForm = ["granules", "powder", "mixed", "closed"].includes(page.evidence.form);
    elements.noteTitle.value = state.title;
    elements.leftPageTag.textContent = phase.label.toUpperCase();
    elements.pageState.textContent = "Phase " + (state.currentPhase + 1) + " of " + phases.length;
    elements.message.value = page.draft;
    elements.message.placeholder = "Add an observation for " + phase.label.toLowerCase() + "...";
    renderObservations(page);
    renderEvidence(page);
    renderReferences(page);
    renderRead(page, phase);
    renderPageProgress();
    elements.previousPage.disabled = state.currentPhase === 0;
    elements.nextPage.textContent = state.currentPhase === phases.length - 1 ? "Finish this note" : "Continue to " + phases[state.currentPhase + 1].label.toLowerCase();
    elements.statusNote.textContent = comparisonPending
      ? difficultForm
        ? "Making a careful comparison. The sample form may limit what a photo can show..."
        : "Comparing your notes with the library examples..."
      : requestPending
        ? "Reading this page..."
        : "Autosaved in this browser. Nothing is lost when you move between phases.";
    elements.compareEvidence.disabled = comparisonPending || requestPending || !(
      page.observations.length || page.references.length || page.evidence.photos.length || page.evidence.condition || page.evidence.origin || page.evidence.details
    );
    elements.compareEvidence.textContent = comparisonPending ? "Comparing..." : difficultForm ? "Compare carefully" : "Compare with assistant";
    elements.comparisonHint.textContent = difficultForm ? "Photo alone may not be enough · Unclear from photo is valid" : "Your notes + library examples";
  }
  function renderHistory() {
    elements.historyList.replaceChildren();
    const history = Array.isArray(state.history) ? state.history : [];
    elements.noteHistory.hidden = history.length === 0;
    history.forEach((snapshot, index) => {
      const button = document.createElement("button");
      button.className = "history-item";
      button.type = "button";
      const label = document.createElement("span");
      label.textContent = snapshot.title || "Untitled note";
      const restore = document.createElement("span");
      restore.textContent = "Restore";
      button.append(label, restore);
      button.addEventListener("click", () => restoreHistory(index));
      elements.historyList.appendChild(button);
    });
  }
  function renderLibrary() {
    const query = elements.materialSearch.value.trim().toLowerCase();
    elements.categoryList.replaceChildren();
    categories.forEach((category) => {
      const matchingSubtypes = category.subtypes.filter((subtype) => !query || (category.label + " " + subtype.code + " " + subtype.label).toLowerCase().includes(query));
      if (query && !matchingSubtypes.length && !category.label.toLowerCase().includes(query)) return;
      const block = document.createElement("section");
      block.className = "category-block";
      const categoryButton = document.createElement("button");
      categoryButton.className = "category-button" + (state.selectedCategory === category.id ? " active" : "");
      categoryButton.type = "button";
      categoryButton.setAttribute("aria-expanded", state.selectedCategory === category.id ? "true" : "false");
      const image = document.createElement("img");
      image.className = "category-thumb";
      image.src = category.image;
      image.alt = "";
      const copy = document.createElement("span");
      copy.className = "category-copy";
      const name = document.createElement("span");
      name.className = "category-name";
      name.textContent = category.label;
      const count = document.createElement("span");
      count.className = "category-count";
      count.textContent = category.subtypes.length + " types";
      copy.append(name, count);
      const stateMark = document.createElement("span");
      stateMark.className = "category-state";
      stateMark.textContent = state.selectedCategory === category.id ? "Close" : "Open";
      categoryButton.append(image, copy, stateMark);
      categoryButton.addEventListener("click", () => {
        state.selectedCategory = state.selectedCategory === category.id ? "" : category.id;
        saveState();
        renderLibrary();
      });
      block.appendChild(categoryButton);
      if (state.selectedCategory === category.id || query) {
        const subtypeList = document.createElement("div");
        subtypeList.className = "subtype-list";
        const subtypes = query ? matchingSubtypes : category.subtypes;
        subtypes.forEach((subtype) => {
          const selected = activePage().references.some((reference) => reference.id === subtype.id);
          const subtypeButton = document.createElement("button");
          subtypeButton.className = "subtype-button" + (selected ? " selected" : "");
          subtypeButton.type = "button";
          subtypeButton.setAttribute("aria-pressed", selected ? "true" : "false");
          const subtypeImage = document.createElement("img");
          subtypeImage.className = "subtype-thumb";
          subtypeImage.src = subtype.image || category.image;
          subtypeImage.alt = "";
          const subtypeCopy = document.createElement("span");
          subtypeCopy.className = "subtype-copy";
          const code = document.createElement("span");
          code.className = "subtype-code";
          code.textContent = subtype.code;
          const subtypeLabel = document.createElement("span");
          subtypeLabel.className = "subtype-label";
          subtypeLabel.textContent = subtype.label;
          subtypeCopy.append(code, subtypeLabel);
          const selectedMark = document.createElement("span");
          selectedMark.className = "subtype-state";
          selectedMark.textContent = selected ? "Saved" : "Add";
          subtypeButton.append(subtypeImage, subtypeCopy, selectedMark);
          subtypeButton.addEventListener("click", () => toggleReference(category, subtype));
          subtypeList.appendChild(subtypeButton);
        });
        block.appendChild(subtypeList);
      }
      elements.categoryList.appendChild(block);
    });
  }
  function renderBoard(page) {
    const images = page.references.length ? page.references.map((item) => item.image) : ["/assets/material-plastics.webp", "/assets/material-paper.webp", "/assets/material-metals.webp"];
    elements.boardImagePrimary.src = images[0] || "/assets/material-plastics.webp";
    elements.boardImageSecondary.src = images[1] || images[0] || "/assets/material-paper.webp";
    elements.boardImageTertiary.src = images[2] || images[1] || images[0] || "/assets/material-metals.webp";
  }
  function renderAll() {
    renderPhaseRail();
    renderNotebook();
    renderBoard(activePage());
    renderHistory();
    renderLibrary();
  }
  function turnToPhase(index) {
    if (index < 0 || index >= phases.length || index === state.currentPhase) return;
    if (turnTimer) window.clearTimeout(turnTimer);
    const direction = index > state.currentPhase ? "is-turning-forward" : "is-turning-back";
    elements.notebookSpread = elements.notebookSpread || document.getElementById("notebookSpread");
    elements.notebookSpread.classList.remove("is-turning-forward", "is-turning-back");
    void elements.notebookSpread.offsetWidth;
    elements.notebookSpread.classList.add(direction);
    const oldIndex = state.currentPhase;
    turnTimer = window.setTimeout(() => {
      state.currentPhase = index;
      saveState();
      renderAll();
      elements.notebookSpread.classList.remove("is-turning-forward", "is-turning-back");
      if (oldIndex !== index) elements.message.focus({preventScroll: true});
    }, 230);
  }
  function goToPhase(index) {
    if (index === state.currentPhase) return;
    turnToPhase(index);
  }
  function markPhaseAndAdvance() {
    if (state.currentPhase < phases.length - 1) {
      if (!phaseHasWork(state.currentPhase)) {
        elements.message.focus({preventScroll: true});
        elements.statusNote.textContent = "Add an observation or a reference before moving on. Your page is still ready.";
        return;
      }
      turnToPhase(state.currentPhase + 1);
      return;
    }
    elements.statusNote.textContent = "This note is complete as a working record. You can still return to any phase.";
  }
  function toggleReference(category, subtype) {
    const page = activePage();
    const existing = page.references.findIndex((reference) => reference.id === subtype.id);
    if (existing >= 0) page.references.splice(existing, 1);
    else page.references.push({id: subtype.id, code: subtype.code, label: subtype.label, image: subtype.image || category.image});
    page.comparison = "";
    page.comparisonSources = [];
    saveState();
    renderAll();
  }
  function setLibraryOpen(open) {
    elements.library.dataset.open = open ? "true" : "false";
    elements.library.setAttribute("aria-hidden", open ? "false" : "true");
    elements.libraryBackdrop.dataset.open = open ? "true" : "false";
  }
  function archiveCurrentNote() {
    if (!state.pages.some((_, index) => phaseHasWork(index))) return;
    state.history = [{title: state.title, pages: state.pages, savedAt: new Date().toISOString()}, ...(state.history || [])].slice(0, 5);
  }
  function startNewNote() {
    archiveCurrentNote();
    const history = state.history || [];
    const theme = elements.body.dataset.theme;
    state = freshState();
    state.history = history;
    state.theme = theme;
    saveState();
    conversationGeneration += 1;
    sessionId = null;
    requestPending = false;
    comparisonPending = false;
    renderAll();
    createSession();
    elements.noteTitle.focus({preventScroll: true});
  }
  function restoreHistory(index) {
    const snapshot = state.history[index];
    if (!snapshot || !Array.isArray(snapshot.pages)) return;
    const current = {title: state.title, pages: state.pages, savedAt: new Date().toISOString()};
    state.title = snapshot.title || "Restored material investigation";
    state.pages = validState({pages: snapshot.pages}).pages;
    state.currentPhase = 0;
    state.history = [current, ...state.history.filter((_, itemIndex) => itemIndex !== index)].slice(0, 5);
    saveState();
    renderAll();
  }
  function headers() {
    const result = {"Content-Type": "application/json"};
    if (token) result.Authorization = "Bearer " + token;
    return result;
  }
  async function request(url, options) {
    const response = await fetch(url, Object.assign({}, options, {headers: headers()}));
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      elements.authGate.hidden = false;
      elements.authInput.focus();
      throw new Error("auth_required");
    }
    if (!response.ok) throw new Error(body.error || ("Request failed (" + response.status + ")"));
    return body;
  }
  function showConnectionError(error, kind) {
    requestPending = false;
    comparisonPending = false;
    renderNotebook();
    if (error && error.message === "auth_required") return;
    elements.statusNote.textContent = kind === "comparison"
      ? "Your notes are saved on this page. The comparison is not available right now."
      : "The observation is saved on this page. The assistant read is not available right now.";
  }
  async function createSession() {
    if (starting || sessionId) return;
    starting = true;
    elements.send.disabled = true;
    try {
      const body = await request("/api/sessions", {method: "POST", body: "{}"});
      sessionId = body.session_id;
      elements.authGate.hidden = true;
    } catch (error) {
      showConnectionError(error);
    } finally {
      starting = false;
      elements.send.disabled = false;
    }
  }
  async function saveObservation(event) {
    event.preventDefault();
    const text = elements.message.value.trim();
    if (!text || requestPending || comparisonPending) return;
    const phaseIndex = state.currentPhase;
    const requestGeneration = conversationGeneration;
    const requestSessionId = sessionId;
    const page = state.pages[phaseIndex];
    page.observations.push(text);
    page.draft = "";
    page.reply = "";
    page.sources = [];
    page.comparison = "";
    page.comparisonSources = [];
    saveState();
    renderAll();
    if (!requestSessionId) {
      await createSession();
      if (!sessionId) return;
    }
    requestPending = true;
    renderNotebook();
    try {
      const body = await request("/api/sessions/" + encodeURIComponent(requestSessionId || sessionId) + "/message", {
        method: "POST",
        body: JSON.stringify({message: text})
      });
      if (requestGeneration !== conversationGeneration) return;
      const targetPage = state.pages[phaseIndex];
      targetPage.reply = body.text || "The observation is saved. Add another detail when you are ready.";
      targetPage.sources = body.data && Array.isArray(body.data.sources) ? body.data.sources : [];
      saveState();
      requestPending = false;
      renderAll();
    } catch (error) {
      if (requestGeneration !== conversationGeneration) return;
      showConnectionError(error);
    } finally {
      elements.message.focus({preventScroll: true});
    }
  }
  function comparisonPrompt(page, phase) {
    const observations = page.observations.slice(-10).map((item, index) => (index + 1) + ". " + item.slice(0, 320)).join("\n") || "None recorded.";
    const references = page.references.map((item) => item.code + " — " + item.label).join(", ") || "None selected.";
    const evidence = page.evidence || blankEvidence();
    const sampleFormLabels = {
      whole: "whole piece",
      flakes: "flakes or chips",
      granules: "granules or pellets",
      powder: "powder or dust",
      mixed: "mixed pieces",
      closed: "a closed container"
    };
    const sampleForm = sampleFormLabels[evidence.form] || "not provided";
    const difficultForm = ["granules", "powder", "mixed", "closed"].includes(evidence.form);
    const photoNote = evidence.photos.length
      ? evidence.photos.length + " user-provided sample photo(s) are saved locally. Do not inspect or describe their pixels in this text-only comparison."
      : "No user-provided sample photo is attached.";
    return [
      "Please compare this material investigation in ordinary language.",
      "The phase is " + phase.label + ".",
      "User notes (treat as supplied details, not verified fact):\n" + observations,
      "Selected library examples (used or worked-on material examples only): " + references,
      "Sample form: " + sampleForm + ".",
      "Sample condition: " + (evidence.condition || "not provided") + ".",
      "Sample origin: " + (evidence.origin || "not provided") + ".",
      "What the user wants compared: " + (evidence.details || "not provided") + ".",
      photoNote,
      "Use everyday English. Say notes, library examples, first read, and next simple check. Avoid technical labels unless the user uses them first.",
      "Explain what fits the examples, what the current details cannot tell us, what might change the first read, and the next simple check.",
      difficultForm
        ? "This is a difficult photo case. Start by saying that a photo alone is not enough to name the material. Describe only visible features, do not choose one material as the answer, and treat a mixed sample as mixed. Use the headings What I can see, What this photo cannot tell us, What might change this, and Next simple check."
        : "Use the headings What fits, What this does not tell us, What might change this, and Next simple check.",
      "If the photo or notes are not enough, use the plain result label Unclear from photo and explain what extra detail would help.",
      "Do not claim image inspection, confirmed identity, test results, composition, grade, recyclability, legal status, safety clearance, price, yield, or process suitability. Name material types only as possibilities and keep uncertainty visible. Do not invent sources or measurements."
    ].join("\n\n").slice(0, 3950);
  }
  async function compareEvidenceWithAssistant() {
    if (comparisonPending || requestPending) return;
    const phaseIndex = state.currentPhase;
    const page = state.pages[phaseIndex];
    if (!(
      page.observations.length || page.references.length || page.evidence.photos.length || page.evidence.condition || page.evidence.origin || page.evidence.details
    )) return;
    const requestGeneration = conversationGeneration;
    const requestSessionId = sessionId;
    if (!requestSessionId) {
      await createSession();
      if (!sessionId) return;
    }
    comparisonPending = true;
    renderNotebook();
    try {
      const body = await request("/api/sessions/" + encodeURIComponent(requestSessionId || sessionId) + "/message", {
        method: "POST",
        body: JSON.stringify({message: comparisonPrompt(page, phases[phaseIndex])})
      });
      if (requestGeneration !== conversationGeneration) return;
      const targetPage = state.pages[phaseIndex];
      const assistantAvailable = !(body.data && body.data.ai_used === false);
      targetPage.comparison = assistantAvailable ? (body.text || "Your notes are saved. Add another detail or library example when you are ready.") : "";
      targetPage.comparisonSources = assistantAvailable && body.data && Array.isArray(body.data.sources) ? body.data.sources : [];
      saveState();
      comparisonPending = false;
      renderAll();
      if (!assistantAvailable) elements.statusNote.textContent = "Your notes are saved. The assistant is not available right now.";
    } catch (error) {
      if (requestGeneration !== conversationGeneration) return;
      showConnectionError(error, "comparison");
    } finally {
      elements.compareEvidence.focus({preventScroll: true});
    }
  }
  function resizeEvidencePhoto(file) {
    return new Promise((resolve, reject) => {
      if (!file || !file.type.startsWith("image/")) {
        reject(new Error("Choose an image file."));
        return;
      }
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("The sample photo could not be read."));
      reader.onload = () => {
        const image = new Image();
        image.onerror = () => reject(new Error("The sample photo could not be opened."));
        image.onload = () => {
          const maxDimension = 1200;
          const scale = Math.min(1, maxDimension / Math.max(image.naturalWidth, image.naturalHeight));
          const canvas = document.createElement("canvas");
          canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
          canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
          const context = canvas.getContext("2d");
          if (!context) {
            reject(new Error("The sample photo could not be prepared."));
            return;
          }
          context.drawImage(image, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL("image/jpeg", .78));
        };
        image.src = reader.result;
      };
      reader.readAsDataURL(file);
    });
  }
  async function addEvidencePhotos(event) {
    const page = activePage();
    const available = Math.max(0, 3 - page.evidence.photos.length);
    const files = Array.from(event.target.files || []).slice(0, available);
    if (!files.length) {
      event.target.value = "";
      return;
    }
    try {
      for (const file of files) {
        const dataUrl = await resizeEvidencePhoto(file);
        page.evidence.photos.push({
          id: "photo-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7),
          name: file.name,
          dataUrl
        });
      }
      page.comparison = "";
      page.comparisonSources = [];
      saveState();
      renderAll();
      elements.statusNote.textContent = "The sample photo is saved locally on this page.";
    } catch (error) {
      elements.statusNote.textContent = error.message || "The sample photo could not be saved.";
    } finally {
      event.target.value = "";
    }
  }
  elements.noteTitle.addEventListener("input", () => {
    state.title = elements.noteTitle.value;
    saveState();
  });
  elements.message.addEventListener("input", () => {
    activePage().draft = elements.message.value;
    saveState();
  });
  elements.message.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      elements.composer.requestSubmit();
    }
  });
  elements.composer.addEventListener("submit", saveObservation);
  elements.compareEvidence.addEventListener("click", compareEvidenceWithAssistant);
  elements.evidencePhotoInput.addEventListener("change", addEvidencePhotos);
  elements.evidenceForm.addEventListener("change", () => {
    activePage().evidence.form = elements.evidenceForm.value;
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
    renderNotebook();
  });
  elements.evidenceCondition.addEventListener("change", () => {
    activePage().evidence.condition = elements.evidenceCondition.value;
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
    renderNotebook();
  });
  elements.evidenceOrigin.addEventListener("input", () => {
    activePage().evidence.origin = elements.evidenceOrigin.value.slice(0, 140);
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
  });
  elements.evidenceDetails.addEventListener("input", () => {
    activePage().evidence.details = elements.evidenceDetails.value.slice(0, 220);
    activePage().comparison = "";
    activePage().comparisonSources = [];
    saveState();
  });
  elements.previousPage.addEventListener("click", () => turnToPhase(state.currentPhase - 1));
  elements.nextPage.addEventListener("click", markPhaseAndAdvance);
  elements.usePrompt.addEventListener("click", () => {
    elements.message.value = phases[state.currentPhase].question + " ";
    activePage().draft = elements.message.value;
    saveState();
    elements.message.focus({preventScroll: true});
  });
  elements.libraryToggle.addEventListener("click", () => setLibraryOpen(true));
  elements.libraryClose.addEventListener("click", () => setLibraryOpen(false));
  elements.libraryBackdrop.addEventListener("click", () => setLibraryOpen(false));
  elements.materialSearch.addEventListener("input", () => renderLibrary());
  elements.globalSearch.addEventListener("input", () => {
    elements.materialSearch.value = elements.globalSearch.value;
    setLibraryOpen(true);
    renderLibrary();
  });
  elements.newNote.addEventListener("click", startNewNote);
  elements.themeToggle.addEventListener("click", () => setTheme(elements.body.dataset.theme === "dark" ? "light" : "dark"));
  elements.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    token = elements.authInput.value.trim();
    elements.authError.hidden = true;
    sessionId = null;
    await createSession();
    if (!sessionId) {
      elements.authError.hidden = false;
      elements.authError.textContent = "That key did not start a session. Check it and try again.";
    }
  });

  setTheme(loadTheme());
  renderAll();
  if (window.innerWidth <= 1080) setLibraryOpen(false);
  createSession();
})();
</script>
</body>
</html>"""
