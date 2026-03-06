#!/usr/bin/env python3
"""
Browser utility - creates the appropriate WebDriver based on the host OS.
  • Windows → Microsoft Edge (EdgeDriver)
  • macOS / Linux → Google Chrome (ChromeDriver)
"""

import platform
from typing import Dict, List, Optional


def create_driver(
    args: Optional[List[str]] = None,
    experimental: Optional[Dict] = None,
    capabilities: Optional[Dict] = None,
):
    """
    Build and return a Selenium WebDriver suited to the current OS.

    Args:
        args:         List of browser arguments (e.g. ['--headless', '--no-sandbox'])
        experimental: Dict of experimental options (e.g. {'excludeSwitches': [...]})
        capabilities: Dict of driver capabilities (e.g. {'goog:loggingPrefs': ...})

    Returns:
        selenium.webdriver.Chrome or selenium.webdriver.Edge instance
    """
    on_windows = platform.system() == "Windows"

    if on_windows:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    else:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

    options = Options()
    for arg in args or []:
        options.add_argument(arg)
    for key, value in (experimental or {}).items():
        options.add_experimental_option(key, value)
    for key, value in (capabilities or {}).items():
        options.set_capability(key, value)

    return webdriver.Edge(options=options) if on_windows else webdriver.Chrome(options=options)
