import sys
import os
import tarfile
import tempfile
import subprocess
import shutil
import time

# ─────────────────────────────────────────────────────────────────────────────
def get_resource_path(relative_path):
    """Resolves paths whether running from source or as a PyInstaller bundle."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ─────────────────────────────────────────────────────────────────────────────
def _run(cmd, cwd=None):
    """Run a shell command; raise on non-zero exit."""
    result = subprocess.run(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {cmd}")
    return result.stdout.strip()

# ─────────────────────────────────────────────────────────────────────────────
def backup_current_theme(backup_dir):
    """Snapshot current KDE config files to backup_dir."""
    os.makedirs(backup_dir, exist_ok=True)
    config_home = os.path.expanduser("~/.config")
    local_share = os.path.expanduser("~/.local/share")

    for fname in ["kdeglobals", "kwinrc", "plasmashellrc",
                  "plasma-org.kde.plasma.desktop-appletsrc"]:
        src = os.path.join(config_home, fname)
        if os.path.exists(src):
            shutil.copy2(src, backup_dir)

    for dirname in ["plasma", "aurorae"]:
        src = os.path.join(local_share, dirname)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, dirname)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

# ─────────────────────────────────────────────────────────────────────────────
def apply_theme(callback=None, options=None):
    """
    Extract the bundled theme archive and apply selected components.

    Parameters
    ----------
    callback : callable(str) | None
        Called with progress messages to display in the UI log.
    options  : dict | None
        Keys: theme, icons, cursor, wallpaper, effects, backup (all bool).
        Defaults all to True when None.
    """
    if options is None:
        options = {k: True for k in
                   ("theme", "icons", "cursor", "wallpaper", "effects", "backup")}

    def log(msg):
        if callback:
            callback(msg)

    theme_archive = get_resource_path("theme.tar.gz")
    if not os.path.exists(theme_archive):
        raise FileNotFoundError(f"Theme package not found at: {theme_archive}")

    with tempfile.TemporaryDirectory() as tmp:

        # 1. Extract ────────────────────────────────────────────────────────
        log("Extracting theme package…")
        with tarfile.open(theme_archive, "r:gz") as tar:
            tar.extractall(path=tmp)
        extracted = os.path.join(tmp, "ubuntu-theme-installer")

        home        = os.path.expanduser("~")
        config_home = os.path.join(home, ".config")
        local_share = os.path.join(home, ".local", "share")

        # 2. Backup ─────────────────────────────────────────────────────────
        if options.get("backup"):
            backup_path = os.path.join(home, ".kde_backup")
            log(f"Backing up current theme → {backup_path}")
            backup_current_theme(backup_path)
            log("Backup complete.")

        # 3. Global theme / window decorations ──────────────────────────────
        if options.get("theme"):
            log("Applying global theme (Layan)…")
            src_plasma = os.path.join(extracted, "local_share", "plasma")
            dst_plasma = os.path.join(local_share, "plasma")
            if os.path.exists(src_plasma):
                os.makedirs(dst_plasma, exist_ok=True)
                _merge_dirs(src_plasma, dst_plasma)

            src_aurorae = os.path.join(extracted, "local_share", "aurorae")
            dst_aurorae = os.path.join(local_share, "aurorae")
            if os.path.exists(src_aurorae):
                os.makedirs(dst_aurorae, exist_ok=True)
                _merge_dirs(src_aurorae, dst_aurorae)

            for fname in ["kdeglobals", "plasmashellrc",
                          "plasma-org.kde.plasma.desktop-appletsrc"]:
                src = os.path.join(extracted, "config", fname)
                if os.path.exists(src):
                    _place_config(src, config_home, fname)

            log("Global theme applied.")

        # 4. Icons ──────────────────────────────────────────────────────────
        if options.get("icons"):
            log("Installing icon pack (Tela Circle)…")
            src_icons = os.path.join(extracted, "local_share", "icons")
            dst_icons = os.path.join(local_share, "icons")
            if os.path.exists(src_icons):
                os.makedirs(dst_icons, exist_ok=True)
                _merge_dirs(src_icons, dst_icons)
            log("Icons installed.")

        # 5. Cursor ─────────────────────────────────────────────────────────
        if options.get("cursor"):
            log("Setting cursor theme…")
            cursor_src = os.path.join(extracted, "local_share", "icons")
            cursor_dst = os.path.join(local_share, "icons")
            if os.path.exists(cursor_src):
                os.makedirs(cursor_dst, exist_ok=True)
                for name in os.listdir(cursor_src):
                    if "cursor" in name.lower():
                        s = os.path.join(cursor_src, name)
                        d = os.path.join(cursor_dst, name)
                        if os.path.isdir(s):
                            if os.path.exists(d):
                                shutil.rmtree(d)
                            shutil.copytree(s, d)
            log("Cursor theme set.")

        # 6. Wallpaper ──────────────────────────────────────────────────────
        if options.get("wallpaper"):
            log("Applying wallpaper…")
            wp_src = os.path.join(extracted, "wallpaper")
            wp_dst = os.path.join(home, "Pictures", "Wallpapers")
            os.makedirs(wp_dst, exist_ok=True)
            wp_file = None
            if os.path.exists(wp_src):
                for f in os.listdir(wp_src):
                    shutil.copy2(os.path.join(wp_src, f), os.path.join(wp_dst, f))
                    wp_file = os.path.join(wp_dst, f)
            if wp_file:
                _set_kde_wallpaper(wp_file)
            log(f"Wallpaper applied: {wp_file}")

        # 7. Effects ────────────────────────────────────────────────────────
        if options.get("effects"):
            log("Enabling desktop effects (blur, glide, wobbly windows)…")
            kwinrc_src = os.path.join(extracted, "config", "kwinrc")
            if os.path.exists(kwinrc_src):
                _place_config(kwinrc_src, config_home, "kwinrc")
            log("Effects applied.")

        # 8. Restart Plasma ─────────────────────────────────────────────────
        log("Restarting Plasma shell… (your screen will flicker briefly)")
        try:
            subprocess.Popen(
                ["/bin/bash", "-c",
                 "kquitapp5 plasmashell || killall plasmashell; "
                 "sleep 1; kstart5 plasmashell"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass  # Non-fatal; the config changes persist

        log("All done! Welcome to DragonTheme. 🐉")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _merge_dirs(src, dst):
    """Recursively copy src into dst, overwriting existing files."""
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            os.makedirs(d, exist_ok=True)
            _merge_dirs(s, d)
        else:
            shutil.copy2(s, d)


def _place_config(src_file, config_dir, dst_name):
    """Copy a config file into config_dir, creating it if needed."""
    os.makedirs(config_dir, exist_ok=True)
    shutil.copy2(src_file, os.path.join(config_dir, dst_name))


def _set_kde_wallpaper(wp_path):
    """Use qdbus to set the desktop wallpaper live."""
    script = (
        'var all = desktops();'
        'for (var i = 0; i < all.length; i++) {'
        '  var d = all[i];'
        '  d.wallpaperPlugin = "org.kde.image";'
        '  d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];'
        f'  d.writeConfig("Image", "file://{wp_path}");'
        '}'
    )
    try:
        subprocess.run(
            ["qdbus", "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", script],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        )
    except Exception:
        pass  # Non-fatal if qdbus is unavailable
