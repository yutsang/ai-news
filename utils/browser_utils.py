#!/usr/bin/env python3
"""
Browser utility - creates the appropriate WebDriver based on the host OS.
  • Windows → Microsoft Edge  (managed by webdriver-manager → EdgeChromiumDriverManager)
  • macOS / Linux → Google Chrome (managed by webdriver-manager → ChromeDriverManager)

webdriver-manager automatically downloads the correct driver binary, so no manual
driver installation is required and cached/wrong drivers are never picked up.
"""

import platform
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def create_driver(
    args: Optional[List[str]] = None,
    experimental: Optional[Dict] = None,
    capabilities: Optional[Dict] = None,
):
    """
    Build and return a Selenium WebDriver suited to the current OS.
    The correct driver binary is auto-installed via webdriver-manager.

    Args:
        args:         List of browser arguments (e.g. ['--headless', '--no-sandbox'])
        experimental: Dict of experimental options (e.g. {'excludeSwitches': [...]})
        capabilities: Dict of driver capabilities (e.g. {'goog:loggingPrefs': ...})

    Returns:
        selenium.webdriver.Chrome or selenium.webdriver.Edge instance
    """
    on_windows = platform.system() == "Windows"

    def _build_options(OptionsClass):
        opts = OptionsClass()
        for arg in args or []:
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
        from webdriver_manager.microsoft import EdgeChromiumDriverManager

        logger.info("Windows detected — launching Microsoft Edge via EdgeChromiumDriverManager")
        options = _build_options(EdgeOptions)
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
