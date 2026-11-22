# AIRBridge v1.3 — Windows release

A lightweight iPhone-to-Windows local transfer utility with an Apple-inspired
interface, QR pairing, transfer approval, and success notifications.

### Download

- **AIRBridge-v1.3-Pakej-Lengkap.zip** — recommended. Contains the Windows
  executable, illustrated Malay-language usage guide, and optional source code.
- **AIRBridge.exe** — standalone Windows application.
- **INFOGRAFIK-CARA-GUNA-AIRBRIDGE.png** — seven illustrated setup steps.

### Highlights

- Modern rounded Windows interface and matching iPhone Safari sender page.
- Displays an in-app completion popup and attempts a native Windows notification.
- Files transfer in 16 MiB chunks; up to three different files in parallel.
- No user-facing limit on file count, file size or batch size.
- Windows must approve each incoming batch before the browser can upload.
- All traffic stays on the local network (no cloud).
- Settings from earlier DropBridge installs are read automatically.

### Requirements and limitations

- Windows 11 (x64); iPhone with a supported version of Safari.
- Both devices must be reachable on the same private local network.
- Transfers are plain HTTP and are **not encrypted**. Avoid public Wi-Fi.
- This is **not native AirDrop** and does not appear in Apple's AirDrop menu.
- Network speed, battery, storage, operating system and browser restrictions
  still apply. Native notifications can be blocked by Windows settings.
- AIRBridge is not affiliated with Apple.
- The distributed executable is not code-signed. Windows SmartScreen or
  security software may present a warning.
