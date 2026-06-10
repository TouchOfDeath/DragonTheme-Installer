# DragonTheme Installer: Official User Guide

Welcome to the **DragonTheme Installer**! This app was designed to completely overhaul a default Linux desktop and transform it into a stunning, dark, cinematic workspace with just a single click.

---

## 💻 System Requirements

Before running the installer, ensure your system meets these requirements:

### Supported Operating Systems
* **Kubuntu** (Recommended)
* **Manjaro KDE**
* **Arch Linux** (with KDE)
* **Fedora KDE Spin**
* Any other Linux distribution running **KDE Plasma 5**.

### ⚠️ Important Note for Ubuntu Users
Standard Ubuntu uses the **GNOME** desktop by default. This application **will not work** on standard Ubuntu unless you install KDE Plasma first. 

If you are on standard Ubuntu, open your terminal and run this command before using the app:
```bash
sudo apt update
sudo apt install kde-plasma-desktop
```
*(Once installed, log out, select "Plasma" from the login screen menu, and log back in).*

---

## 🚀 How to Install the Theme

1. **Download the App**
   Download the latest `DragonTheme_Installer` file from the [Releases page](https://github.com/TouchOfDeath/DragonTheme-Installer/releases).

2. **Make the App Executable**
   Linux requires you to give permission to run downloaded apps. 
   * **Graphical method:** Right-click the downloaded `DragonTheme_Installer` file -> Properties -> Permissions -> Check "Is executable" -> Click OK.
   * **Terminal method:** Open your terminal in the Downloads folder and run:
     ```bash
     chmod +x DragonTheme_Installer
     ```

3. **Run the App**
   Double-click the `DragonTheme_Installer` file, or run `./DragonTheme_Installer` in your terminal.

4. **Customize Your Options**
   The app will open and show you a preview of the desktop. Click **Customise Options →**.
   Here, you can toggle exactly what you want the app to change:
   * **Global Theme:** Window decorations, dark colours, panel styles.
   * **Icon Pack:** Circular, colourful Tela icons.
   * **Cursor Theme:** Smooth, elegant mouse pointers.
   * **Wallpaper:** The cinematic dragon background.
   * **Desktop Effects:** Frosted glass blur, transparency, and smooth animations.
   * **Backup current theme:** *Leave this checked!* It saves your current setup in case you want to revert later.

5. **Install**
   Click **Continue to Install**, then click the **⚡ Install Now** button. Wait for the progress bar to finish. Your screen may flash or restart briefly as the new theme is applied.

---

## 🔙 How to Revert to Your Old Theme

If you left the "Backup current theme" switch enabled during installation, reverting is incredibly easy!

1. Open your terminal.
2. The app saved a backup script in your home folder. Run it by typing:
   ```bash
   bash ~/ThemeBackup_*/restore.sh
   ```
   *(If you have multiple backups, it will restore the most recent one).*
3. Your screen will refresh, and your old layout, wallpaper, and icons will be instantly restored!

---

## 🛠️ Troubleshooting

**Problem: The app opens, but nothing changes when I click Install.**
* **Solution:** You are likely running a desktop environment that is not KDE Plasma (such as GNOME or XFCE). See the requirements section to install Plasma.

**Problem: The app won't open when I double-click it.**
* **Solution:** The file hasn't been marked as executable. Right-click the file, go to Properties, and ensure the "Is executable" box is checked.

**Problem: Some windows don't have the blur effect.**
* **Solution:** Blur effects require hardware acceleration. Go to your KDE Settings -> Display and Monitor -> Compositor, and ensure "Enable compositor on startup" is checked and working.
