/* AIRBridge sender translations. No framework, account or cloud required. */
(() => {
  "use strict";

  const translations = {
    en: {
      connected: "Connected locally",
      eyebrow: "PRIVATE. FAST. EFFORTLESS.",
      hero_first: "Your files.",
      hero_second: "Just across.",
      hero_desc: "Send photos, videos and documents directly from your iPhone to your Windows PC. No cloud. No cables.",
      upload_title: "Send to Windows",
      upload_caption: "Choose one or more files from your iPhone.",
      select_title: "Choose files",
      formats: "Photos · Videos · Documents",
      browse: "Browse files",
      send_button: "Send to Windows →",
      status_ready: "Connection ready. Choose files to begin.",
      privacy_title: "Just between your devices.",
      privacy_desc: "Windows approval is required. Files are never uploaded to the cloud.",
      footer: "Inspired by simplicity, not affiliated with Apple.",
      file_input_aria: "Choose files to send",
      progress_aria: "Transfer progress",
      selection: "{count} file(s) · {size} · {names}",
      sending: "Sending…",
      waiting: "Waiting for approval on Windows…",
      approval_declined: "Windows declined the request.",
      approval_expired: "The request expired or was not approved.",
      upload_failed: "Upload failed. Please try again.",
      connection_lost: "Connection lost. Check Wi-Fi and your local network.",
      upload_timeout: "Upload timed out.",
      chunk_mismatch: "The file chunk confirmation did not match.",
      chunk_failed: "A file chunk could not be sent.",
      resuming: "Resuming the transfer…",
      progress_status: "Sending · {count}/{totalFiles} files complete · {sent} / {totalSize}",
      live_speed: "Current speed: {rate}/s",
      average_speed: "Average speed: {rate}/s",
      success: "✓ Success! {count} file(s) received ({size}).",
      server_error: "The receiver returned an error (HTTP {code}).",
    },
    ms: {
      connected: "Bersambung secara setempat",
      eyebrow: "PERIBADI. PANTAS. MUDAH.",
      hero_first: "Fail anda.",
      hero_second: "Terus sampai.",
      hero_desc: "Hantar gambar, video dan dokumen terus daripada iPhone ke PC Windows anda. Tanpa cloud. Tanpa kabel.",
      upload_title: "Hantar ke Windows",
      upload_caption: "Pilih satu atau lebih fail daripada iPhone.",
      select_title: "Pilih fail",
      formats: "Foto · Video · Dokumen",
      browse: "Cari fail",
      send_button: "Hantar ke Windows →",
      status_ready: "Sambungan tersedia. Pilih fail untuk mula.",
      privacy_title: "Hanya antara peranti anda.",
      privacy_desc: "Kelulusan Windows diperlukan. Fail tidak dimuat naik ke cloud.",
      footer: "Direka untuk kemudahan, bukan produk rasmi Apple.",
      file_input_aria: "Pilih fail untuk dihantar",
      progress_aria: "Kemajuan pemindahan",
      selection: "{count} fail · {size} · {names}",
      sending: "Sedang diproses…",
      waiting: "Menunggu kelulusan pada Windows…",
      approval_declined: "PC menolak permintaan.",
      approval_expired: "Permintaan tamat masa atau tidak diluluskan.",
      upload_failed: "Muat naik gagal. Cuba sekali lagi.",
      connection_lost: "Sambungan terputus. Semak Wi-Fi dan rangkaian.",
      upload_timeout: "Muat naik tamat masa.",
      chunk_mismatch: "Pengesahan ketulan fail tidak sepadan.",
      chunk_failed: "Ketulan fail tidak dapat dihantar.",
      resuming: "Menyambung semula penghantaran…",
      progress_status: "Menghantar · {count}/{totalFiles} fail selesai · {sent} / {totalSize}",
      live_speed: "Kelajuan semasa: {rate}/s",
      average_speed: "Kelajuan purata: {rate}/s",
      success: "✓ Berjaya! {count} fail diterima ({size}).",
      server_error: "Ralat pada penerima (HTTP {code}).",
    }
  };

  function readCookie() {
    const match = document.cookie.match(/(?:^|;\s*)airbridge_lang=(en|ms)(?:;|$)/);
    return match ? match[1] : null;
  }

  const queryLanguage = new URL(location.href).searchParams.get("lang");
  const requested = readCookie() || (["en", "ms"].includes(queryLanguage)
    ? queryLanguage : null);
  let language = requested || (navigator.language.toLowerCase().startsWith("ms") ? "ms" : "en");

  function t(key, values = {}) {
    const raw = translations[language][key];
    if (typeof raw !== "string") throw new Error("Missing translation: " + language + "." + key);
    return raw.replace(/\{([a-zA-Z]+)\}/g, (_, name) => String(values[name] ?? ""));
  }

  function render() {
    document.documentElement.lang = language;
    document.querySelectorAll("[data-i18n]").forEach(el => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(el => {
      el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });
    document.querySelectorAll("[data-lang]").forEach(el => {
      const selected = el.dataset.lang === language;
      el.classList.toggle("active", selected);
      el.setAttribute("aria-pressed", String(selected));
    });
  }

  function setLanguage(next) {
    if (!["en", "ms"].includes(next)) return;
    language = next;
    // Unlike localStorage, first-party cookies persist across changing server
    // ports, so the preference survives the next AIRBridge application launch.
    document.cookie = "airbridge_lang=" + next +
      "; Path=/; Max-Age=31536000; SameSite=Lax";
    render();
  }

  window.AIRBridgeI18n = { t, render, setLanguage, getLanguage: () => language, translations };
  render();
})();
