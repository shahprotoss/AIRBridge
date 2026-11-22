"""Generate verified English and Malay AIRBridge infographic PNGs from HTML.

These layouts intentionally use a non-scannable QR placeholder: the only valid
pairing code is created at runtime by AIRBridge.exe.
"""

from __future__ import annotations

import html
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
VERSION = "v1.6"
SIZE = (1600, 1100)

CONTENT = {
    "en": {
        "caption": "FROM IPHONE TO WINDOWS · LOCAL FILE TRANSFER",
        "name": "AIRBridge",
        "chip": "WINDOWS 11 + IPHONE",
        "eyebrow": "BILINGUAL · ENGLISH / BAHASA MELAYU",
        "title1": "Your files.",
        "title2": "Just across.",
        "summary": "Move photos, videos and documents from your iPhone to Windows in a few simple steps. No cloud storage. No cables.",
        "feature1": "Fast local transfers",
        "feature2": "No app-set file count or size limit",
        "feature3": "Approval on Windows",
        "demo": "AIRBRIDGE FOR WINDOWS",
        "ready": "Ready to receive",
        "scan": "Scan the live QR code in AIRBridge",
        "network": "Private local network",
        "incoming": "Incoming requests",
        "request": "iPhone wants to send 3 files",
        "accept": "Accept",
        "decline": "Decline",
        "phone_head": "AIRBridge",
        "phone_text": "Choose files",
        "phone_btn": "Send to Windows",
        "phone_url": "LOCAL SAFARI PAGE",
        "toast_title": "Transfer complete",
        "toast_desc": "3 files received",
        "steps_heading": "HOW TO USE AIRBRIDGE",
        "steps": [
            ("01", "Connect", "Use the same trusted local network. Windows can use Ethernet."),
            ("02", "Launch app", "Open AIRBridge.exe on Windows 11. Allow Private network access if asked."),
            ("03", "Scan the QR", "Scan the code shown in AIRBridge using iPhone Camera; open Safari."),
            ("04", "Choose language", "Select English or Bahasa Melayu on either device."),
            ("05", "Select & send", "Choose photos, videos or files in Safari and tap Send to Windows."),
            ("06", "Accept & done", "Click Accept on your PC. Wait for the success notification."),
        ],
        "requirements": "REQUIREMENTS",
        "requirements_body": "Windows 11 (64-bit) · iPhone with Safari · Same local network",
        "package": "INSIDE THE ZIP",
        "package_body": "AIRBridge.exe · English guide · Optional Malay guide · No app source",
        "safety": "IMPORTANT",
        "safety_body": "Local HTTP transfers are not encrypted. Use a trusted private network only. This is not native Apple AirDrop.",
        "foot": "OFFICIAL DOWNLOAD · github.com/shahprotoss/AIRBridge/releases/latest",
        "marker": "Illustrative interface · Live QR appears in app",
    },
    "ms": {
        "caption": "DARIPADA IPHONE KE WINDOWS · PEMINDAHAN SETEMPAT",
        "name": "AIRBridge",
        "chip": "WINDOWS 11 + IPHONE",
        "eyebrow": "DWIBAHASA · ENGLISH / BAHASA MELAYU",
        "title1": "Fail anda.",
        "title2": "Terus sampai.",
        "summary": "Hantar gambar, video dan dokumen daripada iPhone ke Windows dengan mudah. Tanpa cloud. Tanpa kabel.",
        "feature1": "Pemindahan setempat pantas",
        "feature2": "Tiada had fail ditetapkan aplikasi",
        "feature3": "Kelulusan pada Windows",
        "demo": "AIRBRIDGE UNTUK WINDOWS",
        "ready": "Sedia menerima fail",
        "scan": "Imbas kod QR sebenar dalam AIRBridge",
        "network": "Rangkaian setempat peribadi",
        "incoming": "Permintaan masuk",
        "request": "iPhone ingin menghantar 3 fail",
        "accept": "Terima",
        "decline": "Tolak",
        "phone_head": "AIRBridge",
        "phone_text": "Pilih fail",
        "phone_btn": "Hantar ke Windows",
        "phone_url": "HALAMAN SAFARI SETEMPAT",
        "toast_title": "Pemindahan berjaya!",
        "toast_desc": "3 fail diterima",
        "steps_heading": "CARA MENGGUNAKAN AIRBRIDGE",
        "steps": [
            ("01", "Sambungkan", "Guna rangkaian setempat yang sama. Windows boleh guna kabel LAN."),
            ("02", "Buka aplikasi", "Jalankan AIRBridge.exe pada Windows 11. Benarkan rangkaian Private."),
            ("03", "Imbas kod QR", "Guna Kamera iPhone, imbas kod QR AIRBridge dan buka Safari."),
            ("04", "Pilih bahasa", "Pilih English atau Bahasa Melayu pada mana-mana peranti."),
            ("05", "Pilih & hantar", "Pilih gambar, video atau fail di Safari dan tekan Hantar ke Windows."),
            ("06", "Terima & siap", "Klik Terima pada PC. Tunggu notifikasi pemindahan berjaya."),
        ],
        "requirements": "KEPERLUAN",
        "requirements_body": "Windows 11 (64-bit) · iPhone dengan Safari · Rangkaian yang sama",
        "package": "KANDUNGAN ZIP",
        "package_body": "AIRBridge.exe · Panduan English · Pilihan BM · Tanpa kod sumber",
        "safety": "PENTING",
        "safety_body": "Pemindahan HTTP setempat tidak disulitkan. Guna rangkaian peribadi dipercayai. Bukan AirDrop rasmi Apple.",
        "foot": "MUAT TURUN RASMI · github.com/shahprotoss/AIRBridge/releases/latest",
        "marker": "Ilustrasi sahaja · Kod QR sebenar dalam aplikasi",
    },
}


TEMPLATE = r"""<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIRBridge {{VERSION}} · {{CAPTION}}</title>
<style>
*{box-sizing:border-box}
:root{font-family:"Segoe UI",Arial,sans-serif;color:#172234;background:#f6faff;font-synthesis:none}
body{margin:0}
.page{width:1600px;height:1100px;overflow:hidden;position:relative;
 background:radial-gradient(ellipse at 84% 4%,#b8dcff 0%,transparent 35%),
 radial-gradient(ellipse at 5% 57%,#e0edff 0%,transparent 39%),#f7faff;padding:39px 47px 26px}
.page::before{content:"";position:absolute;right:-110px;top:-200px;width:650px;height:660px;border:2px solid #ffffff62;border-radius:50%;pointer-events:none}
.head{position:relative;display:flex;align-items:center;justify-content:space-between;height:77px}
.brand{display:flex;align-items:center;gap:14px}
.brandicon{width:72px;height:72px;border-radius:21px;display:grid;place-items:center;color:#fff;
 background:linear-gradient(145deg,#66c3ff 0%,#007aff 70%,#0459d0 100%);
 box-shadow:0 12px 30px #007aff3d,inset 0 2px 3px #ffffff6c;font-size:51px;font-weight:600}
.brandtext{font-size:44px;font-weight:800;letter-spacing:-2.2px}
.brandtext span{color:#007aff}
.subtitle{font-size:14px;color:#62768f;letter-spacing:2.1px;font-weight:800}
.version{border-radius:30px;background:#fff;border:1px solid #dae7f6;padding:14px 21px;font-size:18px;font-weight:760;color:#1c4d82;box-shadow:0 6px 24px #4867890d}
.hero{display:grid;grid-template-columns:535px 1fr;gap:17px;height:424px;align-items:center}
.text-panel{padding:15px 0}
.eyebrow{font-size:14px;color:#007aff;font-weight:800;letter-spacing:2.4px}
.hero h1{font-size:70px;line-height:1.0;letter-spacing:-3.2px;margin:17px 0 17px;font-weight:820}
.hero h1 em{color:#007aff;font-style:normal}
.summary{font-size:21px;line-height:1.48;color:#536c89;max-width:495px;margin:0 0 20px}
.pills{display:flex;flex-direction:column;gap:8px}
.pill{display:flex;align-items:center;gap:11px;color:#1e3f5a;font-size:18px;font-weight:690}
.pill b{display:grid;place-items:center;border-radius:12px;background:#e6f3ff;color:#007aff;width:34px;height:34px;font-size:20px}
.mock{height:372px;display:flex;position:relative;align-items:center;padding-left:6px}
.computer{width:625px;height:347px;background:#1c2940;border-radius:20px;padding:12px;box-shadow:0 29px 55px #173b692b}
.monitor{height:100%;background:#f7faff;border-radius:11px;overflow:hidden}
.titlebar{height:42px;background:#fff;display:flex;align-items:center;gap:11px;padding:0 17px;border-bottom:1px solid #e8edf6}
.smallapp{display:grid;place-items:center;background:#007aff;color:#fff;border-radius:9px;width:25px;height:25px;font-size:18px}
.titlebar strong{font-size:17px}
.minipicker{margin-left:auto;border-radius:18px;background:#ebf4ff;padding:7px 12px;color:#007aff;font-size:12px;font-weight:800}
.monitorinner{display:grid;grid-template-columns: 47% 53%;gap:13px;padding:18px}
.paircard{background:#fff;border:1px solid #e8eef6;border-radius:17px;height:247px;padding:16px 16px}
.paircard h4{font-size:14px;margin:0 0 9px;color:#1d293e}
.qr-placeholder{height:124px;border-radius:13px;background:#f1f6ff;display:flex;align-items:center;justify-content:center;
 flex-direction:column;color:#007aff;border:2px dashed #b3cef2;gap:4px}
.qr-icon{font-size:52px;line-height:1;font-weight:500}
.qr-hint{color:#52718f;font-size:12px;max-width:235px;line-height:1.25;text-align:center}
.pairfoot{margin-top:11px;color:#31a86d;font-size:11px;font-weight:800}
.inbox{background:#fff;border:1px solid #e8eef6;border-radius:17px;height:247px;padding:17px 16px}
.inbox h4{font-size:15px;margin:0 0 12px}
.notifrow{border-radius:12px;background:#f3f7fd;padding:12px;font-size:12px;color:#34475c}
.notifs{display:flex;gap:6px;margin-top:11px}
.btn{font-size:12px;color:#fff;background:#007aff;border-radius:9px;padding:9px 19px;font-weight:800}
.btn.gray{color:#41566c;background:#e8eef6}
.phone{position:absolute;right:0;top:34px;width:200px;height:322px;border:9px solid #172435;border-radius:35px;
 background:#fdfefe;box-shadow:0 20px 44px #17324a35;padding:16px 9px 14px;display:flex;flex-direction:column;align-items:center}
.notch{position:absolute;top:0;left:48px;background:#172435;border-radius:0 0 16px 16px;width:85px;height:15px}
.address{margin-top:18px;padding:7px 5px;border-radius:9px;background:#edf1f6;width:100%;text-align:center;
 font-size:9px;font-weight:700;color:#617185}
.phone-logo{display:grid;place-items:center;margin:30px auto 8px;background:#007aff;color:#fff;width:57px;height:57px;border-radius:16px;font-size:40px}
.phone h4{margin:0;font-size:20px}
.phone .languages{background:#e5effc;color:#1c66b4;padding:6px 13px;border-radius:17px;font-size:11px;font-weight:780;margin:10px auto}
.phone-btn{background:#007aff;color:#fff;border-radius:11px;font-size:12px;text-align:center;font-weight:800;
 width:100%;padding:11px 3px;margin-top:8px}
.toast{position:absolute;right:115px;bottom:-2px;background:#fff;box-shadow:0 12px 38px #21456335;
 border-radius:19px;border:1px solid #dfe8f2;display:flex;align-items:center;gap:12px;padding:12px 16px;min-width:276px;z-index:2}
.success{display:grid;place-items:center;background:#e6f8ee;color:#20a963;border-radius:11px;width:42px;height:42px;font-size:26px}
.toast strong{font-size:15px}
.toast p{margin:3px 0 0;font-size:12px;color:#688096}
.caption{position:absolute;bottom:0;left:45px;font-size:12px;color:#8aa1b7;font-weight:650}
.bar-title{display:flex;gap:14px;align-items:center;margin:19px 0 16px}
.blue-rule{width:7px;height:38px;border-radius:12px;background:#007aff}
.bar-title h2{font-size:28px;margin:0;font-weight:830;color:#1c3456}
.steps{display:grid;grid-template-columns:repeat(6,1fr);gap:13px}
.step{background:#fff;border:1px solid #dfe9f6;min-height:192px;border-radius:21px;padding:17px 15px 13px;
 box-shadow:0 8px 24px #587ca80d}
.count{width:42px;height:42px;display:grid;place-items:center;border-radius:14px;background:#e1efff;
 color:#007aff;font-size:21px;font-weight:850}
.step h3{font-size:19px;font-weight:800;letter-spacing:-.5px;margin:12px 0 8px}
.step p{font-size:15px;line-height:1.36;color:#53677f;margin:0}
.meta{display:grid;grid-template-columns:1fr 1fr 1.3fr;gap:16px;margin-top:19px}
.box{border-radius:21px;border:1px solid #d7e9f7;background:#e9f5ff;padding:20px 21px;min-height:146px}
.box:nth-child(2){background:#edf8f6;border-color:#d3ece5}
.box:nth-child(3){background:#fff8e9;border-color:#f4e6bf}
.box h3{font-size:19px;font-weight:810;margin:0 0 12px}
.box h3 span{font-size:24px;margin-right:7px}
.box p{font-size:17px;line-height:1.4;color:#43566b;margin:0}
footer{margin-top:15px;display:flex;justify-content:space-between;align-items:center;color:#627e9d;font-size:15px;
 border-top:1px solid #d6e6f5;padding-top:12px}
footer b{color:#007aff}
</style>
</head>
<body><div class="page">
  <header class="head">
    <div class="brand"><div class="brandicon">↗</div><div><div class="brandtext"><span>AIR</span>Bridge</div><div class="subtitle">{{CAPTION}}</div></div></div>
    <div class="version">{{VERSION}} · {{CHIP}}</div>
  </header>
  <section class="hero">
    <div class="text-panel">
      <div class="eyebrow">{{EYEBROW}}</div>
      <h1>{{TITLE1}}<br><em>{{TITLE2}}</em></h1>
      <p class="summary">{{SUMMARY}}</p>
      <div class="pills">
        <div class="pill"><b>⚡</b>{{FEATURE1}}</div>
        <div class="pill"><b>∞</b>{{FEATURE2}}</div>
        <div class="pill"><b>✓</b>{{FEATURE3}}</div>
      </div>
    </div>
    <div class="mock">
      <div class="computer">
        <div class="monitor">
          <div class="titlebar"><div class="smallapp">↗</div><strong>AIRBridge</strong><div class="minipicker">English  |  Bahasa Melayu</div></div>
          <div class="monitorinner">
            <div class="paircard"><h4>{{READY}}</h4><div class="qr-placeholder"><div class="qr-icon">▦</div><div class="qr-hint">{{SCAN}}</div></div><div class="pairfoot">● {{NETWORK}}</div></div>
            <div class="inbox"><h4>{{INCOMING}}</h4><div class="notifrow">{{REQUEST}}</div><div class="notifs"><span class="btn">{{ACCEPT}}</span><span class="btn gray">{{DECLINE}}</span></div></div>
          </div>
        </div>
      </div>
      <div class="phone"><div class="notch"></div><div class="address">{{PHONE_URL}}</div>
        <div class="phone-logo">↗</div><h4>{{PHONE_HEAD}}</h4><div class="languages">EN &nbsp; | &nbsp; BM</div>
        <div class="phone-btn">+ {{PHONE_TEXT}}</div><div class="phone-btn">{{PHONE_BTN}}</div></div>
      <div class="toast"><div class="success">✓</div><div><strong>{{TOAST_TITLE}}</strong><p>{{TOAST_DESC}}</p></div></div>
      <div class="caption">{{MARKER}}</div>
    </div>
  </section>
  <div class="bar-title"><div class="blue-rule"></div><h2>{{STEPS_HEADING}}</h2></div>
  <section class="steps">{{STEPS_HTML}}</section>
  <section class="meta">
    <div class="box"><h3><span>⌘</span>{{REQUIREMENTS}}</h3><p>{{REQUIREMENTS_BODY}}</p></div>
    <div class="box"><h3><span>▣</span>{{PACKAGE}}</h3><p>{{PACKAGE_BODY}}</p></div>
    <div class="box"><h3><span>⚠</span>{{SAFETY}}</h3><p>{{SAFETY_BODY}}</p></div>
  </section>
  <footer><b>AIRBridge {{VERSION}}</b><span>{{FOOT}}</span></footer>
</div></body></html>"""


def find_edge() -> Path:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    edge = shutil.which("msedge")
    if edge:
        return Path(edge)
    raise FileNotFoundError("Microsoft Edge required for screenshot rendering")


def render(lang: str):
    data = CONTENT[lang]
    markup = TEMPLATE
    steps_html = "".join(
        '<article class="step"><div class="count">' + html.escape(number) +
        "</div><h3>" + html.escape(title) + "</h3><p>" +
        html.escape(description) + "</p></article>"
        for number, title, description in data["steps"]
    )
    replacements = {"lang": lang, "version": VERSION, **data, "steps_html": steps_html}
    for key, value in replacements.items():
        if key == "steps":
            continue
        if key != "steps_html":
            value = html.escape(value)
        markup = markup.replace("{{" + key.upper() + "}}", value)
    if "{{" in markup:
        raise ValueError("Unresolved infographic HTML variable")

    basename = f"AIRBridge-Guide-{'EN' if lang == 'en' else 'BM'}"
    html_path = ROOT / (basename + ".html")
    png_path = ROOT / (basename + ".png")
    html_path.write_text(markup, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="airbridge-infographic-") as temp_dir:
        subprocess.run(
            [
                str(find_edge()), "--headless=new", "--disable-gpu",
                "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
                "--force-device-scale-factor=1",
                f"--window-size={SIZE[0]},{SIZE[1]}",
                f"--user-data-dir={temp_dir}",
                f"--screenshot={png_path}",
                html_path.as_uri(),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=40,
        )
    with Image.open(png_path) as image:
        if image.size != SIZE:
            raise ValueError(f"Unexpected infographic size: {image.size}")
    if png_path.stat().st_size < 40_000:
        raise ValueError("Unexpectedly small infographic — rendering may have failed")
    print(f"{lang}: {png_path.name} — {SIZE[0]}×{SIZE[1]} / {png_path.stat().st_size:,} bytes")
    return png_path


if __name__ == "__main__":
    render("en")
    malay_infographic = render("ms")
    shutil.copy2(malay_infographic, ROOT / "INFOGRAFIK-CARA-GUNA-AIRBRIDGE.png")
