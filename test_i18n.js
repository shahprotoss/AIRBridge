/* Smoke tests for iPhone language selection and translation completeness. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "web", "i18n.js"), "utf8");
const page = fs.readFileSync(path.join(__dirname, "web", "index.html"), "utf8");
const client = fs.readFileSync(path.join(__dirname, "web", "client.js"), "utf8");

function launch(url, initialCookie = "", browserLanguage = "en-US") {
  const elements = [
    {dataset:{i18n:"connected"}, textContent:""},
    {dataset:{i18nAria:"file_input_aria"}, setAttribute(key, value){this[key]=value;}},
    {dataset:{lang:"en"}, classList:{toggle(_key, active){this.active=active;}},setAttribute(key,value){this[key]=value;}},
    {dataset:{lang:"ms"}, classList:{toggle(_key, active){this.active=active;}},setAttribute(key,value){this[key]=value;}}
  ];
  const doc = {
    _cookie: initialCookie,
    get cookie() { return this._cookie; },
    set cookie(value) { this._cookie = value; },
    documentElement:{lang:""},
    querySelectorAll(selector) {
      if(selector==="[data-i18n]") return elements.filter(x=>x.dataset.i18n);
      if(selector==="[data-i18n-aria]") return elements.filter(x=>x.dataset.i18nAria);
      if(selector==="[data-lang]") return elements.filter(x=>x.dataset.lang);
      return [];
    }
  };
  const win = {};
  vm.runInNewContext(source, {
    document:doc, location:{href:url}, navigator:{language:browserLanguage},
    URL, window:win,
  }, {filename:"i18n.js"});
  return {doc, i18n:win.AIRBridgeI18n, elements};
}

const english = launch("http://192.168.0.10:55000/?k=token&lang=en");
assert.equal(english.i18n.getLanguage(), "en");
assert.equal(english.doc.documentElement.lang, "en");
assert.equal(english.elements[0].textContent, "Connected locally");
english.i18n.setLanguage("ms");
assert.equal(english.i18n.getLanguage(), "ms");
assert.equal(english.elements[0].textContent, "Bersambung secara setempat");
assert.match(english.doc.cookie, /airbridge_lang=ms/);
assert.equal(english.elements[3]["aria-pressed"], "true");

// Cookies survive changing receiver port; they override the desktop's hint.
const reopened = launch(
  "http://192.168.0.10:61731/?k=newtoken&lang=en",
  "airbridge_lang=ms; Path=/"
);
assert.equal(reopened.i18n.getLanguage(), "ms");
assert.equal(reopened.i18n.t("upload_title"), "Hantar ke Windows");
reopened.i18n.setLanguage("en");
assert.equal(reopened.i18n.t("upload_title"), "Send to Windows");

const defaultMalay = launch("http://192.168.0.10:55000/?k=token", "", "ms-MY");
assert.equal(defaultMalay.i18n.getLanguage(), "ms");
const translations = english.i18n.translations;
assert.deepEqual(
  Object.keys(translations.en).sort(),
  Object.keys(translations.ms).sort(),
  "English and Bahasa Melayu must expose the same translation keys"
);

const keys = [...page.matchAll(/data-i18n(?:-aria)?="([^"]+)"/g)].map(match=>match[1]);
for (const key of keys) {
  assert.ok(key in translations.en, "Missing iPhone string for " + key);
}
for (const match of client.matchAll(/\bt\("([^"]+)"/g)) {
  assert.ok(match[1] in translations.en, "Missing dynamic text for " + match[1]);
}
for (const match of client.matchAll(/\b(?:setStatus|setSpeed|error)\("([^"]+)"/g)) {
  assert.ok(match[1] in translations.en, "Missing status/error text for " + match[1]);
}
console.log("PASS: bilingual sender UI, cookies, URL hint, runtime strings and translation parity");
