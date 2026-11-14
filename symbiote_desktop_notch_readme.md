# Symbiote Desktop Notch & HUD (Venom/Carnage Theme)

A lightweight, frameless, and highly optimized Python/PyQt6 desktop dynamic notch designed for Windows 11. Built with zero hardware processing pressure, it features a sci-fi Venom/Carnage symbiote aesthetic, dynamic RGB breathing borders, real-time audio visualization, modular sub-notch panels, and smart Microsoft Edge AI integrations.

## 🌟 Project Description

The Symbiote Desktop Notch transforms your Windows 11 desktop experience by introducing a sleek, centralized, and highly functional HUD (Heads-Up Display). Designed to be completely unobtrusive and resource-efficient, it resides at the top of your screen, ready to provide quick access to essential tools. With its cinematic intro animations, personalized user greeting, and modular panels controlled entirely via intuitive arrow key shortcuts, it bridges the gap between aesthetics and extreme productivity.

## ✨ Key Features

1. **Cinematic First-Time Setup & Intro:**
   * On the first launch, prompts the user to set a custom username (strictly validated up to **15 characters**).
   * Dynamically saves the username locally in a user-specific system directory (`os.path.expanduser('~')`), keeping user data decentralized and completely private.
   * Features a synced cinematic welcome message followed by a shattering transition into the Venom/Carnage symbiote border-crawl animation.
   * Your username seamlessly integrates into the main compact notch alongside a live IST clock.

2. **Dynamic RGB Breathing Border:**
   * A smooth, continuously moving neon RGB glow surrounding the notch frame. 
   * Can be toggled ON/OFF directly via the minimalist 3-dots menu for full visual control.

3. **Modular Sub-Notch Architecture:**
   * **Main Notch (`↑`):** Compact pill view displaying your custom username and live Indian Standard Time (IST).
   * **Smart Search Panel (`←`):** Features a search bar and a nested dropdown supporting normal and incognito/private modes across Brave, Edge, and Chrome. Includes automatic missing browser detection with a centered error popup (*"Please Install the Browser first"*).
   * **Dedicated AI Hub (`→`):** A spacious, wider panel containing quick-launch badges for Gemini, ChatGPT, and Claude. Configured to leverage smart Win32 window-focus logic, strictly launching and managing tabs within Microsoft Edge.
   * **Audio Visualizer Panel (`↓`):** Features audio-reactive semi-transparency (blends with your desktop when music plays) and a live dropdown selector to switch between multiple visualizer styles. Clean UI with no unnecessary status text or dots.

4. **Clean Navigation & HUD:**
   * Includes a sleek **3-dots menu icon (...)** on the main notch for quick access to the RGB toggle and other settings.
   * Right-click context options for quick settings access and the **'Replay Intro Animation'** feature.
   * Clutter-free design with all unnecessary status tags and indicator dots removed.

## ⌨️ Keyboard Shortcuts & Controls

The notch is fully optimized for lightning-fast keyboard navigation:

| Shortcut / Action | Function / Target Module | 
| :--- | :--- | 
| **Up Arrow (`↑`)** | Opens/Restores the main compact notch (Username & Live IST Clock). | 
| **Left Arrow (`←`)** | Opens the Smart Search sub-notch and browser/incognito selector. | 
| **Right Arrow (`→`)** | Opens the wider AI Hub sub-notch (Gemini, ChatGPT, Claude via Edge). | 
| **Down Arrow (`↓`)** | Opens the Audio Visualizer sub-notch with theme dropdown & audio transparency. | 
| **3-Dots Menu (`...`)**| Click to access app preferences, RGB breathing effect toggle, etc. | 
| **Right-Click** | Opens the context menu (`Replay Intro Animation`, `Exit`). | 
| **`Esc` Key** | Instantly force-closes the application. | 

## 🛡️ Privacy & Storage

* User data is stored locally in a decentralized user directory (e.g., `~/.venom_notch_user.txt`) and excluded via `.gitignore`. 
* The application runs locally with zero external telemetry, ensuring complete privacy and zero hardware bloat.