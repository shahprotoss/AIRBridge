# AIRBridge — iPhone to Windows

**Muat turun dari [GitHub Releases](../../releases/latest)** apabila release
diterbitkan. Untuk pengguna biasa, pilih fail
**AIRBridge-v1.5-Pakej-Lengkap.zip**, ekstrak dan klik **AIRBridge.exe**.
Python tidak diperlukan pada komputer pengguna.

## English — How to use AIRBridge

![AIRBridge English quick-start infographic](AIRBridge-Guide-EN.png)

1. Download the latest **AIRBridge ZIP** or standalone `AIRBridge.exe` from
   [GitHub Releases](../../releases/latest).
2. Extract the ZIP (if downloaded) and open **AIRBridge.exe** on Windows 11.
3. Connect your iPhone and PC to the **same trusted local network** (Ethernet
   is fine for the PC). Allow Windows Firewall on **Private networks only**.
4. Scan the QR code in AIRBridge with your iPhone Camera, then open in Safari.
5. Choose **English** or **Bahasa Melayu** on Windows or iPhone Safari.
6. Tap **Choose files** and **Send to Windows**. Then click **Accept** on the PC.
7. Wait for the success notification; click **Open received files** to see them.

Read the [full English user guide](GUIDE_EN.md) for troubleshooting, save
locations, and security information.

## Bahasa Melayu — Cara guna AIRBridge

![Infografik Bahasa Melayu](AIRBridge-Guide-BM.png)

## Cara guna (Bahasa Melayu)

1. Sambungkan iPhone dan Windows pada rangkaian setempat yang sama.
2. Buka **AIRBridge.exe** pada Windows 11.
   Pilih **English** atau **Bahasa Melayu** pada bahagian atas aplikasi.
3. Imbas kod QR AIRBridge menggunakan Camera iPhone, kemudian buka Safari.
4. Pilih bahasa pada Safari, kemudian pilih foto, video atau dokumen
   dan ketik **Hantar ke Windows**.
5. Klik **Terima** pada aplikasi AIRBridge di Windows.
6. Tunggu sehingga selesai, kemudian buka folder melalui **Buka fail diterima**.

**Pilihan bahasa diingati:** tetapan Windows disimpan pada PC dan pilihan
Safari disimpan pada iPhone. Apabila menggunakan QR buat kali pertama,
Safari mengikut pilihan bahasa Windows melainkan iPhone sudah memilih sendiri.

Panduan bergambar boleh dibuka dalam
[PANDUAN-INFOGRAFIK.html](PANDUAN-INFOGRAFIK.html).

Rujuk juga [Panduan Bahasa Melayu](GUIDE_BM.md) untuk maklumat lanjut.

> **Penting:** AIRBridge bukan AirDrop rasmi Apple. Pemindahan HTTP setempat
> tidak disulitkan; gunakan hanya rangkaian peribadi yang dipercayai.
> Fail tidak dihantar ke cloud.

---

# English instructions

1. Connect your iPhone and Windows PC to the same private local network.
2. Open **AIRBridge.exe** and select **English** or **Bahasa Melayu**.
3. Scan the QR with iPhone Camera and open the page in Safari.
4. Select your preferred language on Safari, choose files, then tap **Send to Windows**.
5. Click **Accept** on Windows; wait for the transfer-complete notification.
6. Use **Open received files** to open the destination or **Change** to select
   another folder.

Language preferences are saved separately on Windows and Safari. The iPhone
page uses the Windows language as its initial setting unless already customized.

---

# Technical information

AIRBridge is a Windows 11 desktop receiver for transferring photos, videos,
and files from an iPhone using Safari, a QR code, and the same local network.
**It is not native Apple AirDrop and does not appear in iPhone's AirDrop list.**

## Launch

Double-click `dist\AIRBridge.exe` after building or use `start.bat` for development.
For a new executable, run `build.bat` (Python 3.13 required).

1. Connect the iPhone and Windows computer to the same LAN/Wi-Fi network.
   Windows can use Ethernet if it is on the same reachable network as the iPhone.
2. Start AIRBridge on Windows and allow access on **Private networks only** if
   Windows Defender Firewall prompts for permission.
3. Scan the QR code with the iPhone camera. Safari opens the secure-by-token
   local file transfer page.
4. Select files and press **Send to Windows**.
5. Press **Accept** on the Windows application and wait until transfer completes.
6. Files save to `Downloads\AIRBridge` by default (configurable); existing
   DropBridge settings and the previous received-files directory are preserved
   automatically, so existing files are not moved or deleted.

## Premium UI and notifications

- Light macOS-inspired interface, custom AIRBridge icon and modern rounded cards.
- English and Bahasa Melayu language switches on Windows and Safari, with
  saved preferences, localized transfer statuses and completion notifications.
- Matching iPhone transfer web page in a clean white-and-blue style.
- Receives up to three files concurrently using 16 MiB chunks.
- Shows a floating AIRBridge success popup when an entire batch is received.
- Also attempts to display a native Windows notification. Notification permission,
  Focus Assist or the Windows runtime can prevent the native toast; the floating
  AIRBridge success popup works independently.
- Unchanged transfer approval and token validation model. No cloud storage.

## Security and limitations

- HTTP traffic is **not encrypted**. Use a trusted, isolated home/office LAN.
  Do not use public Wi-Fi and don't forward the receiver port to the Internet.
- The one-time random *per-launch* token in the QR code grants access to offer files;
  the Windows operator must still approve each batch. Do not share the URL publicly.
- There is **no configured limit** on the number of selected files, individual
  file size, or batch size. Fast mode uploads each file in 16 MiB chunks, so
  large files do not have to be read into memory all at once. Successful HTTP
  connections stay open for subsequent chunks, and up to three distinct files
  are transferred concurrently. The iPhone screen shows live and average
  transfer speeds. Server requests validate chunk boundaries (32 MiB maximum
  per upload request) and maintain per-file ordering. The file-list metadata
  request is limited to 32 MiB for safety.
- Practical limits still apply, including available disk space, browser/OS
  file support, the file system, battery, and network reliability. A transfer
  interrupted for too long may need to be started again.
- The server uses safe filenames and never deliberately overwrites existing files.
- Transfers are not encrypted end-to-end; no cloud storage is used.
- Native iOS AirDrop uses Apple Wireless Direct Link (AWDL) and does not work
  with a stock Windows Wi-Fi driver. This is a local-network alternative.
- If a QR link fails, verify IP connectivity and Windows Firewall Private access.
  Corporate guest network client isolation or VPN routing can block transfers.
- Files must stay selected and Safari kept active while uploading.
