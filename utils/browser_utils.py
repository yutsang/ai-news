#!/usr/bin/env python3
"""
Browser utility — creates a Chrome WebDriver instance.
The correct ChromeDriver binary is downloaded automatically via webdriver-manager.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def create_driver(
    args: Optional[List[str]] = None,
    experimental: Optional[Dict] = None,
    capabilities: Optional[Dict] = None,
):
    """
    Build and return a Selenium Chrome WebDriver.

    Args:
        args:         Browser arguments  (e.g. ['--headless', '--no-sandbox'])
        experimental: Experimental options (e.g. {'excludeSwitches': [...]})
        capabilities: Driver capabilities (e.g. {'goog:loggingPrefs': ...})

    Returns:
        selenium.webdriver.Chrome instance
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    for arg in args or []:
        options.add_argument(arg)
    for key, value in (experimental or {}).items():
        options.add_experimental_option(key, value)
    for key, value in (capabilities or {}).items():
        options.set_capability(key, value)

    service = Service(ChromeDriverManager().install())
    logger.info("Launching Chrome via ChromeDriverManager")
    return webdriver.Chrome(service=service, options=options)
