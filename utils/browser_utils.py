#!/usr/bin/env python3
"""
Browser utility - creates the appropriate WebDriver based on the host OS.
  • Windows → Microsoft Edge
      Priority 1: msedgedriver.exe bundled inside the Edge installation folder
                  (no internet access required — works on corporate networks)
      Priority 2: webdriver-manager download (fallback when bundled driver not found)
  • macOS / Linux → Google Chrome via webdriver-manager (ChromeDriverManager)
"""

import os
import glob
import platform
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _find_bundled_msedgedriver() -> Optional[str]:
    """
    Locate msedgedriver.exe that ships inside the Microsoft Edge installation.
    Edge has bundled its own WebDriver since version 79, so no download is needed.
    Returns the path to the executable, or None if not found.
    """
    search_roots = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application",
        r"C:\Program Files\Microsoft\Edge\Application",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application"),
    ]
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        # Versioned subdirectory: e.g. 145.0.3800.16\msedgedriver.exe
        matches = glob.glob(os.path.join(root, "*", "msedgedriver.exe"))
        if matches:
            latest = sorted(matches)[-1]
            logger.info(f"Found bundled msedgedriver: {latest}")
            return latest
        # Some builds place it directly in the Application folder
        direct = os.path.join(root, "msedgedriver.exe")
        if os.path.isfile(direct):
            logger.info(f"Found bundled msedgedriver: {direct}")
            return direct
    return None


def create_driver(
    args: Optional[List[str]] = None,
    experimental: Optional[Dict] = None,
    capabilities: Optional[Dict] = None,
):
    """
    Build and return a Selenium WebDriver suited to the current OS.

    On Windows the bundled msedgedriver is used first (no internet required).
    On macOS/Linux ChromeDriverManager handles the download automatically.

    Args:
        args:         List of browser arguments (e.g. ['--headless', '--no-sandbox'])
        experimental: Dict of experimental options (e.g. {'excludeSwitches': [...]})
        capabilities: Dict of driver capabilities (e.g. {'goog:loggingPrefs': ...})

    Returns:
        selenium.webdriver.Chrome or selenium.webdriver.Edge instance
    """
    on_windows = platform.system() == "Windows"

    def _build_options(OptionsClass, translate_incognito: bool = False):
        opts = OptionsClass()
        for arg in args or []:
            # --incognito is Chrome-only; Edge uses --inprivate
            if translate_incognito and arg == "--incognito":
                arg = "--inprivate"
            opts.add_argument(arg)
        for key, value in (experimental or {}).items():
            opts.add_experimental_option(key, value)
        for key, value in (capabilities or {}).items():
            opts.set_capability(key, value)
        return opts

    if on_windows:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.edge.service import Service as EdgeService

        options = _build_options(EdgeOptions, translate_incognito=True)

        # Try the bundled driver first — no network call needed
        bundled = _find_bundled_msedgedriver()
        if bundled:
            logger.info("Windows/Edge: using bundled msedgedriver (no internet download)")
            service = EdgeService(bundled)
        else:
            # Bundled driver not found — try webdriver-manager (needs internet)
            logger.info("Bundled msedgedriver not found — falling back to webdriver-manager download")
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            service = EdgeService(EdgeChromiumDriverManager().install())

        return webdriver.Edge(service=service, options=options)

    else:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager

        logger.info("macOS/Linux detected — launching Chrome via ChromeDriverManager")
        options = _build_options(ChromeOptions)
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
