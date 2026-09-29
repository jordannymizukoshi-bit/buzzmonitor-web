"""Inicialização do Playwright (versões síncrona e assíncrona)."""

from contextlib import asynccontextmanager, contextmanager

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import async_playwright
from playwright.sync_api import Browser as SyncBrowser
from playwright.sync_api import sync_playwright

DEFAULT_HEADLESS = True


@contextmanager
def get_browser(headless: bool = DEFAULT_HEADLESS):
    """Context manager síncrono que entrega um browser Playwright pronto para uso.

    Uso:
        with get_browser(headless=False) as browser:
            page = browser.new_page()
            page.goto("https://example.com")
    """
    with sync_playwright() as playwright:
        browser: SyncBrowser = playwright.chromium.launch(headless=headless)
        try:
            yield browser
        finally:
            browser.close()


@asynccontextmanager
async def get_async_browser(headless: bool = DEFAULT_HEADLESS):
    """Context manager assíncrono equivalente ao get_browser.

    Uso:
        async with get_async_browser(headless=False) as browser:
            page = await browser.new_page()
            await page.goto("https://example.com")
    """
    async with async_playwright() as playwright:
        browser: AsyncBrowser = await playwright.chromium.launch(headless=headless)
        try:
            yield browser
        finally:
            await browser.close()
