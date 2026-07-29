"""release.py — Build, tag, and publish a new Gunpla Fabrication Suite release.

Run from the project root:
    python scripts/release.py

What it does:
    1. Asks for a version number
    2. Checks dependencies are installed
    3. Builds the app via PyInstaller
       - macOS   -> GunplaFabricationSuite.app + GunplaFabricationSuite.dmg
       - Windows -> GunplaFabricationSuite/ folder + GunplaFabricationSuite.zip
       - Linux   -> GunplaFabricationSuite/ folder + GunplaFabricationSuite.tar.gz
    4. Updates the version in src/gunpla_fabrication_suite/__init__.py,
       pyproject.toml, and gunpla_fabrication_suite.spec
    5. Commits any uncommitted changes
    6. Tags the release (vX.Y.Z)
    7. Pushes the commit + tag to GitHub
       -> GitHub Actions (once configured) picks up the tag and attaches the
          artifact to a GitHub Release

Known limitation: the frozen PyInstaller build does not yet resolve
`migrations/` the way a source checkout does — see the docstring in
gunpla_fabrication_suite.spec and docs/architecture.md. This tool exists so
versioning and release mechanics are in place ahead of that packaging work.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

APP_NAME = "GunplaFabricationSuite"
SPEC_FILE = "gunpla_fabrication_suite.spec"
INIT_FILE = Path("src") / "gunpla_fabrication_suite" / "__init__.py"
PYPROJECT_FILE = Path("pyproject.toml")

ROOT = Path(__file__).parent.parent

# Per-platform output artifact
if sys.platform == "darwin":
    ARTIFACT_NAME = f"{APP_NAME}.dmg"
elif sys.platform == "win32":
    ARTIFACT_NAME = f"{APP_NAME}.zip"
else:
    ARTIFACT_NAME = f"{APP_NAME}.tar.gz"

# ── Helpers ───────────────────────────────────────────────────────────────────


def success(msg: str) -> None:
    print(f"[ok]   {msg}")


def info(msg: str) -> None:
    print(f"[->]   {msg}")


def warn(msg: str) -> None:
    print(f"[!!]   {msg}")


def die(msg: str) -> None:
    print(f"\n[FAIL] {msg}\n")
    sys.exit(1)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=False)


def run_output(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip()


# ── Steps ─────────────────────────────────────────────────────────────────────


def ask_version() -> str:
    last_tag = run_output(["git", "describe", "--tags", "--abbrev=0"]) or "none"
    print(f"  Last release tag: {last_tag}")
    print()
    while True:
        version = input("  Enter version number (e.g. 0.2.0): ").strip().lstrip("v")
        if re.match(r"^\d+\.\d+\.\d+$", version):
            return version
        warn("Please use the format X.Y.Z  (e.g.  0.2.0)")


def check_tag(tag: str) -> None:
    result = subprocess.run(["git", "rev-parse", tag], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        die(f"Tag {tag} already exists. Choose a different version.")


def check_dependencies() -> None:
    info("Checking dependencies...")

    if not shutil.which("pyinstaller"):
        warn("PyInstaller not found - installing now...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    if not shutil.which("git"):
        die("git not found.")

    remote = run_output(["git", "remote", "get-url", "origin"])
    if not remote:
        die("No git remote 'origin' configured. Run: git remote add origin <url>")

    if sys.platform == "darwin" and not shutil.which("create-dmg"):
        warn(
            "create-dmg not found - will use hdiutil fallback. "
            "Install with: brew install create-dmg"
        )

    success("Dependencies OK")


def build_app() -> Path:
    info("Running PyInstaller (this takes a few minutes)...")

    shutil.rmtree(ROOT / "build", ignore_errors=True)
    shutil.rmtree(ROOT / "dist", ignore_errors=True)

    result = subprocess.run(["pyinstaller", SPEC_FILE, "--noconfirm"], cwd=ROOT)
    if result.returncode != 0:
        die("PyInstaller build failed.")

    if sys.platform == "darwin":
        app_path = ROOT / "dist" / f"{APP_NAME}.app"
        if not app_path.exists():
            die(f".app bundle not found at {app_path}")
        success("App bundle created")
        return app_path
    else:
        app_path = ROOT / "dist" / APP_NAME
        if not app_path.exists():
            die(f"Build output not found at {app_path}")
        success("App build created")
        return app_path


def package_macos(app_path: Path) -> Path:
    info("Creating DMG...")
    dmg_path = ROOT / "dist" / ARTIFACT_NAME

    if shutil.which("create-dmg"):
        result = subprocess.run(
            [
                "create-dmg",
                "--volname",
                APP_NAME,
                "--window-pos",
                "200",
                "140",
                "--window-size",
                "660",
                "400",
                "--icon-size",
                "120",
                "--icon",
                f"{APP_NAME}.app",
                "180",
                "170",
                "--hide-extension",
                f"{APP_NAME}.app",
                "--app-drop-link",
                "480",
                "170",
                "--no-internet-enable",
                str(dmg_path),
                str(app_path),
            ],
            cwd=ROOT,
        )
        if result.returncode != 0:
            warn("create-dmg reported an issue - falling back to hdiutil.")
            dmg_path.unlink(missing_ok=True)

    if not dmg_path.exists():
        run(
            [
                "hdiutil",
                "create",
                "-volname",
                APP_NAME,
                "-srcfolder",
                str(app_path),
                "-ov",
                "-format",
                "UDZO",
                str(dmg_path),
            ]
        )

    if not dmg_path.exists():
        die("DMG creation failed.")

    size_mb = dmg_path.stat().st_size / (1024 * 1024)
    success(f"DMG created  ({size_mb:.0f} MB)")
    return dmg_path


def package_windows(app_path: Path) -> Path:
    info("Creating ZIP...")
    zip_base = ROOT / "dist" / APP_NAME
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", str(app_path.parent), app_path.name))
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    success(f"ZIP created  ({size_mb:.0f} MB)")
    return zip_path


def package_linux(app_path: Path) -> Path:
    info("Creating tar.gz...")
    tar_base = ROOT / "dist" / APP_NAME
    tar_path = Path(
        shutil.make_archive(str(tar_base), "gztar", str(app_path.parent), app_path.name)
    )
    size_mb = tar_path.stat().st_size / (1024 * 1024)
    success(f"tar.gz created  ({size_mb:.0f} MB)")
    return tar_path


def package(app_path: Path) -> Path:
    if sys.platform == "darwin":
        return package_macos(app_path)
    elif sys.platform == "win32":
        return package_windows(app_path)
    else:
        return package_linux(app_path)


def update_version(version: str) -> None:
    """Update the version in every file that records it.

    ``src/gunpla_fabrication_suite/__init__.py`` is the canonical source;
    ``pyproject.toml`` and the PyInstaller spec are kept in sync with it.
    """
    info(f"Updating version to {version}...")

    init_path = ROOT / INIT_FILE
    init_text = init_path.read_text(encoding="utf-8")
    init_text = re.sub(r'__version__\s*=\s*"[^"]*"', f'__version__ = "{version}"', init_text)
    init_path.write_text(init_text, encoding="utf-8")

    pyproject_path = ROOT / PYPROJECT_FILE
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject_text = re.sub(
        r'(?m)^version = "[^"]*"', f'version = "{version}"', pyproject_text, count=1
    )
    pyproject_path.write_text(pyproject_text, encoding="utf-8")

    spec_path = ROOT / SPEC_FILE
    spec_text = spec_path.read_text(encoding="utf-8")
    spec_text = re.sub(
        r'"CFBundleShortVersionString":\s*"[^"]*"',
        f'"CFBundleShortVersionString": "{version}"',
        spec_text,
    )
    spec_text = re.sub(
        r'"CFBundleVersion":\s*"[^"]*"', f'"CFBundleVersion": "{version}"', spec_text
    )
    spec_path.write_text(spec_text, encoding="utf-8")

    success("Version updated in __init__.py, pyproject.toml, and the spec file")


_SENSITIVE_PATTERNS = (
    ".env",
    ".env.",
    "credentials",
    "secret",
    "keyring",
    "id_rsa",
    "id_ed25519",
    ".pem",
    ".p12",
    ".pfx",
)


def _check_staged_for_secrets() -> None:
    """Abort if any staged file looks like it might contain credentials."""
    staged = run_output(["git", "diff", "--cached", "--name-only"])
    if not staged:
        return
    flagged = [
        line
        for line in staged.splitlines()
        if any(pat in line.lower() for pat in _SENSITIVE_PATTERNS)
    ]
    if flagged:
        print()
        warn("Potentially sensitive files are staged:")
        for f in flagged:
            print(f"       {f}")
        answer = input("  Continue anyway? [y/N]: ").strip().lower()
        if answer != "y":
            die("Aborted by user.")


def commit_and_tag(version: str) -> str:
    tag = f"v{version}"

    info("Staging changes...")
    # Stage only files already tracked by git plus the specific paths we
    # expect to change. Deliberately avoid -A so stray build artefacts or
    # local data directories are never swept in.
    run(["git", "add", "--update"])
    run(["git", "add", "src/", "tests/", "migrations/", "docs/", "scripts/", "--"], check=False)
    run(
        [
            "git",
            "add",
            str(PYPROJECT_FILE),
            SPEC_FILE,
            "CHANGELOG.md",
            "README.md",
            "--",
        ],
        check=False,
    )

    _check_staged_for_secrets()

    status = run_output(["git", "diff", "--cached", "--name-only"])
    if status:
        info("Committing...")
        run(["git", "commit", "-m", f"chore: release {tag}"])
        success("Changes committed")
    else:
        info("Nothing new to commit - working tree already clean.")

    info(f"Creating tag {tag}...")
    run(["git", "tag", tag])
    success(f"Tag {tag} created")

    info("Pushing to GitHub...")
    # Regular push only - never force-push to main. If this fails because the
    # remote is ahead, the developer must pull and re-run rather than silently
    # overwriting upstream history.
    result = subprocess.run(
        ["git", "push", "origin", "main"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        subprocess.run(["git", "tag", "-d", tag], cwd=ROOT)
        print(result.stderr)
        die(
            "Push to origin/main failed.\n"
            "  -> Pull the latest changes (git pull --rebase origin main),\n"
            "     then re-run scripts/release.py.\n"
            f"  -> Local tag {tag} has been removed so you can retry."
        )
    run(["git", "push", "origin", tag])
    success("Pushed to GitHub")

    return tag


def print_summary(version: str, artifact_path: Path) -> None:
    tag = f"v{version}"
    remote_url = run_output(["git", "remote", "get-url", "origin"])
    remote_url = remote_url.replace("git@github.com:", "https://github.com/").removesuffix(".git")

    print()
    print("=" * 52)
    print(f"  Release {tag} published!")
    print("=" * 52)
    print()
    print(f"  Artifact:       dist/{artifact_path.name}")
    print(f"  Size:           {artifact_path.stat().st_size / (1024 * 1024):.0f} MB")
    print()
    print("  GitHub Actions (once configured) will pick up the tag.")
    print(f"  Repository:     {remote_url}")
    print(f"  Releases page:  {remote_url}/releases")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    platform_label = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, "Linux")

    print()
    print("=" * 52)
    print(f"  Gunpla Fabrication Suite - Release Publisher ({platform_label})")
    print("=" * 52)
    print()

    version = ask_version()
    tag = f"v{version}"

    print()
    info(f"Building release {tag}...")
    print()

    check_tag(tag)
    check_dependencies()

    app_path = build_app()
    artifact_path = package(app_path)

    update_version(version)
    commit_and_tag(version)
    print_summary(version, artifact_path)


if __name__ == "__main__":
    main()
