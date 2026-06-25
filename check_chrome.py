"""Diagnostic script to find Chrome on this system."""
import shutil
import subprocess
import os
from pathlib import Path

paths = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/nix/var/nix/profiles/default/bin/chromium",
    "/root/.nix-profile/bin/chromium",
]

print("=== PATH ===")
print(os.environ.get("PATH", "not set"))

print("\n=== Checking hardcoded paths ===")
for p in paths:
    exists = Path(p).exists()
    print(f"{p}: {'EXISTS' if exists else 'missing'}")

print("\n=== shutil.which ===")
for name in ["chromium", "chromium-browser", "google-chrome", "chromedriver"]:
    result = shutil.which(name)
    print(f"{name}: {result}")

print("\n=== find chromium in /nix ===")
try:
    result = subprocess.run(
        ["find", "/nix", "-name", "chromium", "-type", "f"],
        capture_output=True, text=True, timeout=10
    )
    print(result.stdout[:2000])
except Exception as e:
    print(f"find failed: {e}")

print("\n=== find chromedriver in /nix ===")
try:
    result = subprocess.run(
        ["find", "/nix", "-name", "chromedriver", "-type", "f"],
        capture_output=True, text=True, timeout=10
    )
    print(result.stdout[:2000])
except Exception as e:
    print(f"find failed: {e}")
