# Symbiote Desktop Notch & HUD (Venom/Carnage Theme)

A lightweight, frameless, and highly optimized Python/PyQt6 desktop dynamic notch designed for Windows 11 (with cross-platform Linux support). Built with zero hardware processing pressure, it features a sci-fi Venom/Carnage symbiote aesthetic, dynamic RGB breathing borders, real-time audio visualization, modular sub-notch panels, smart Microsoft Edge AI integrations, and automated startup scheduling.

## 🌟 Project Description

The Symbiote Desktop Notch transforms your desktop experience by introducing a sleek, centralized, and highly functional HUD (Heads-Up Display). Designed to be completely unobtrusive and resource-efficient, it resides at the top of your screen, ready to provide quick access to essential tools. With its cinematic intro animations, personalized user greeting, customizable dimensions, and conflict-free modular panels controlled via smart `Alt + Arrow` key combinations, it bridges the gap between aesthetics and extreme productivity.

## ✨ Key Features

1. **Cinematic First-Time Setup & Intro:**
   * On the first launch, prompts the user to set a custom username (strictly validated up to **15 characters**).
   * Dynamically saves the username and preferences locally in a user-specific system directory (`os.path.expanduser('~')`), keeping user data decentralized and completely private.
   * Features a synced cinematic welcome message followed by a shattering transition into the Venom/Carnage symbiote border-crawl animation.
   * Your username seamlessly integrates into the main compact notch alongside a live IST clock.

2. **Dynamic RGB Breathing Border & Dark Glassmorphism UI:**
   * **Pure Layered Glassmorphism Rendering:** Renders high-performance anti-aliased frosted glass directly in `paintEvent` on the top Smart Notch using `QPainterPath` and smooth alpha layers, eliminating broken DWM composition artifacts and black rectangular corner clipping on Windows 11.
   * **Smoked Glass Base & Specular Sheen:** The top notch features a semi-transparent smoked glass fill (`QColor(18, 22, 32, 145)` — ~57% opacity) so wallpapers and background windows subtly shine through, an inner top-to-bottom white glass sheen gradient (`QColor(255, 255, 255, 38)` to `QColor(255, 255, 255, 6)`), and a crisp 1.2px inner glass rim (`QColor(255, 255, 255, 75)`).
   * **Smooth Stadium-Pill Geometry:** Rendered using circular rounded corners (`border-radius: height / 2.0`, e.g. 16px radius for a 32px tall notch) forming a complete stadium-pill shape with semi-circular left and right ends and zero sharp 90-degree corners.
   * **Solid Dark Slate Pop-ups & Menus (Zero Background Bleed-Through):** UI Settings, Features & Shortcuts guide, Username prompt, and the 3-dots `QMenu` use a rich, solid dark slate card (`#12151E` / `border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.18)`) so text never blends or bleeds into desktop windows behind them.
   * **Automatic Pop-up Overlap Prevention:** Opening UI Settings or Features & Shortcuts automatically closes any other open pop-up so dialogs never stack or overlap.
   * **Crampless Features & Shortcuts Layout:** 520px wide card with `#1A1F2E` container cards, `#38BDF8` shortcut key badges, `#FFFFFF` headers, `#CBD5E1` descriptions with full word wrapping, and dynamic height adjustment with zero text clipping.
   * **Safe Commit/Rollback Controls:** Clicking **Done** permanently saves your customized settings and creates/removes the startup task, while clicking the close button (**X**) or pressing `Esc` safely discards unsaved changes and reverts to your previous snapshot.

3. **Smart Auto-Start (1-Minute Boot Delay):**
   * Managed directly inside the **UI Settings** dialog (**`Auto-Start (1m Delay)`**).
   * Automatically launches the notch **60 seconds after PC/laptop boot** (via Windows Task Scheduler on Windows and `.desktop` autostart delay on Linux) so your system startup remains fast and smooth.

4. **Modular Sub-Notch Architecture (Conflict-Free Hotkeys):**
   * **Main Notch (`Alt + ↑`):** Compact 190x32 view displaying your custom username and live Indian Standard Time (IST).
   * **Smart Search Panel (`Alt + ←`):** Features a search bar and a nested dropdown supporting normal and incognito/private modes across Brave, Edge, and Chrome. Includes automatic missing browser detection with a centered error popup (*"Please Install the Browser first"*).
   * **Dedicated AI Hub (`Alt + →`):** A spacious, wider panel containing quick-launch badges for Gemini, ChatGPT, and Claude. Configured to leverage smart window-focus logic, strictly launching and managing tabs within Microsoft Edge.
   * **Audio Visualizer Panel (`Alt + ↓`):** Features audio-reactive semi-transparency (blends with your desktop when music plays) and a live dropdown selector to switch between multiple visualizer styles.

5. **Built-in Guide & Clutter-Free Navigation:**
   * Minimalist **3-dots menu icon (...)** on the main notch keeping things clean with only: **UI Settings**, **Replay Intro Animation**, and **Exit**.
   * Built-in dark-themed **Features & Shortcuts** pop-up guide accessible directly inside the UI Settings dialog so users can view controls anytime without leaving the desktop.

## ⌨️ Keyboard Shortcuts & Controls

The notch uses `Alt + Arrow` combinations so it never interferes with browser scrolling or YouTube video playback:

| Shortcut / Action | Function / Target Module |
| :--- | :--- |
| **`Alt + ↑` (Up Arrow)** | Opens/Restores the main compact notch (Username & Live IST Clock). |
| **`Alt + ←` (Left Arrow)** | Opens the Smart Search sub-notch and browser/incognito selector. |
| **`Alt + →` (Right Arrow)** | Opens the wider AI Hub sub-notch (Gemini, ChatGPT, Claude via Edge). |
| **`Alt + ↓` (Down Arrow)** | Opens the Audio Visualizer sub-notch with theme dropdown & audio transparency. |
| **3-Dots Menu (`...`)** | Access **UI Settings**, **Replay Intro Animation**, and **Exit**. |
| **Right-Click** | Opens the quick context menu (`Replay Intro Animation`, `Exit`). |
| **`Esc` Key** | Closes active pop-up dialogs (discarding unsaved changes) or exits the notch when focused. |


<img width="545" height="137" alt="Screenshot 2026-11-14 140145" src="https://github.com/user-attachments/assets/17a37ed1-00d1-481d-ba95-d16b34f78474" />


## 🛡️ Privacy & Storage

* User data and UI configurations are stored locally in a decentralized user directory (`os.path.expanduser('~')`) and excluded from version control via `.gitignore`.
* The application runs 100% locally with zero external telemetry, ensuring complete privacy and zero hardware bloat.
