"""
SKT-AI-LABS Browser Automation Tool
Live browser control with anti-bot evasion and intelligent scraping
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import structlog
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logger = structlog.get_logger("skt_ai_labs.tools.browser")


@dataclass
class BrowserAction:
    action: str  # "navigate", "click", "type", "scroll", "screenshot", "extract"
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ScrapedData:
    url: str
    title: str
    content: str
    links: List[Dict[str, str]]
    images: List[str]
    tables: List[List[List[str]]]
    metadata: Dict[str, Any]
    timestamp: float


class SKTBrowser:
    """
    Production-grade browser automation for SKT-AI-LABS agents.

    Features:
    - Headless/headed modes
    - Anti-bot detection evasion
    - JavaScript execution
    - Intelligent content extraction
    - Screenshot capture
    - Form interaction
    - Session persistence
    - Proxy support
    - Automatic retry on failure
    """

    def __init__(self, 
                 headless: bool = True,
                 timeout: int = 30000,
                 anti_bot: bool = True,
                 proxy: Optional[str] = None,
                 user_agent: Optional[str] = None):

        self.headless = headless
        self.timeout = timeout
        self.anti_bot = anti_bot
        self.proxy = proxy
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._logger = logger

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize browser with anti-detection"""
        self._playwright = await async_playwright().start()

        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=browser_args,
            proxy={"server": self.proxy} if self.proxy else None,
        )

        # Stealth context
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": self.user_agent,
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "color_scheme": "light",
        }

        if self.anti_bot:
            context_options["extra_http_headers"] = {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

        self._context = await self._browser.new_context(**context_options)

        # Inject stealth script to hide automation
        if self.anti_bot:
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

        self._logger.info("browser_started", headless=self.headless, anti_bot=self.anti_bot)

    async def close(self):
        """Clean shutdown"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._logger.info("browser_closed")

    async def navigate(self, url: str, wait_until: str = "networkidle") -> bool:
        """Navigate to URL with retry"""
        for attempt in range(3):
            try:
                response = await self._page.goto(url, wait_until=wait_until)
                self._logger.info("navigation_success", url=url, status=response.status if response else "unknown")
                return True
            except Exception as e:
                self._logger.warning("navigation_retry", attempt=attempt+1, error=str(e)[:100])
                await asyncio.sleep(2 ** attempt)

        return False

    async def extract_content(self, 
                              url: Optional[str] = None,
                              selectors: Optional[Dict[str, str]] = None) -> ScrapedData:
        """
        Intelligent content extraction.

        Extracts:
        - Clean text (removes ads, nav, scripts)
        - All links with text
        - Images
        - Tables
        - Metadata (title, description, author, date)
        """
        if url and url != self._page.url:
            success = await self.navigate(url)
            if not success:
                return ScrapedData(
                    url=url or "", title="", content="", 
                    links=[], images=[], tables=[], metadata={}, timestamp=time.time()
                )

        # Wait for content to stabilize
        await self._page.wait_for_load_state("networkidle")

        # Extract metadata
        metadata = await self._extract_metadata()

        # Extract clean text
        content = await self._extract_clean_text()

        # Extract links
        links = await self._extract_links()

        # Extract images
        images = await self._extract_images()

        # Extract tables
        tables = await self._extract_tables()

        # Custom selectors
        if selectors:
            for name, selector in selectors.items():
                try:
                    elements = await self._page.query_selector_all(selector)
                    metadata[f"custom_{name}"] = [await el.inner_text() for el in elements]
                except:
                    metadata[f"custom_{name}"] = []

        return ScrapedData(
            url=self._page.url,
            title=metadata.get("title", ""),
            content=content,
            links=links,
            images=images,
            tables=tables,
            metadata=metadata,
            timestamp=time.time(),
        )

    async def _extract_metadata(self) -> Dict[str, Any]:
        """Extract page metadata"""
        return await self._page.evaluate("""
            () => {
                const getMeta = (name) => {
                    const el = document.querySelector(`meta[name="${name}"], meta[property="og:${name}"]`);
                    return el ? el.content : "";
                };
                return {
                    title: document.title,
                    description: getMeta("description"),
                    author: getMeta("author"),
                    keywords: getMeta("keywords"),
                    canonical: document.querySelector('link[rel="canonical"]')?.href || "",
                    lang: document.documentElement.lang || "en",
                };
            }
        """)

    async def _extract_clean_text(self) -> str:
        """Extract clean article text, removing noise"""
        return await self._page.evaluate("""
            () => {
                // Remove noise elements
                const noise = document.querySelectorAll(
                    'nav, header, footer, aside, .advertisement, .ads, .social-share, 
                     script, style, noscript, iframe, [role="banner"], [role="navigation"]'
                );
                noise.forEach(el => el.remove());

                // Get main content areas
                const main = document.querySelector('main, article, [role="main"], .content, .post');
                if (main) return main.innerText;

                // Fallback to body
                return document.body.innerText;
            }
        """)

    async def _extract_links(self) -> List[Dict[str, str]]:
        """Extract all links with text"""
        links = await self._page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({
                    text: a.innerText.trim().substring(0, 100),
                    href: a.href,
                    title: a.title || ""
                }))
                .filter(a => a.href.startsWith('http'))
        """)
        return links

    async def _extract_images(self) -> List[str]:
        """Extract image URLs"""
        return await self._page.evaluate("""
            () => Array.from(document.querySelectorAll('img[src]'))
                .map(img => img.src)
                .filter(src => src.startsWith('http'))
        """)

    async def _extract_tables(self) -> List[List[List[str]]]:
        """Extract all tables as structured data"""
        return await self._page.evaluate("""
            () => Array.from(document.querySelectorAll('table')).map(table => {
                return Array.from(table.querySelectorAll('tr')).map(row => {
                    return Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim());
                });
            }).filter(t => t.length > 0 && t[0].length > 0)
        """)

    async def click(self, selector: str, wait_for_navigation: bool = False) -> bool:
        """Click element"""
        try:
            if wait_for_navigation:
                async with self._page.expect_navigation():
                    await self._page.click(selector)
            else:
                await self._page.click(selector)
            return True
        except Exception as e:
            self._logger.warning("click_failed", selector=selector, error=str(e)[:100])
            return False

    async def type_text(self, selector: str, text: str, submit: bool = False):
        """Type text into input"""
        await self._page.fill(selector, text)
        if submit:
            await self._page.press(selector, "Enter")

    async def scroll_to_bottom(self):
        """Scroll to bottom for lazy loading"""
        await self._page.evaluate("""
            async () => {
                await new Promise(resolve => {
                    let totalHeight = 0;
                    const distance = 300;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if (totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)

    async def screenshot(self, path: Optional[str] = None, full_page: bool = True) -> bytes:
        """Take screenshot"""
        if path:
            await self._page.screenshot(path=path, full_page=full_page)
            return b""
        else:
            return await self._page.screenshot(full_page=full_page)

    async def execute_actions(self, actions: List[BrowserAction]) -> List[Any]:
        """Execute a sequence of browser actions"""
        results = []
        for action in actions:
            try:
                if action.action == "navigate":
                    result = await self.navigate(action.url)
                elif action.action == "click":
                    result = await self.click(action.selector)
                elif action.action == "type":
                    result = await self.type_text(action.selector, action.value)
                elif action.action == "scroll":
                    result = await self.scroll_to_bottom()
                elif action.action == "screenshot":
                    result = await self.screenshot()
                elif action.action == "extract":
                    result = await self.extract_content()
                else:
                    result = None

                results.append(result)
                await asyncio.sleep(0.5)  # Rate limiting

            except Exception as e:
                self._logger.error("action_failed", action=action.action, error=str(e)[:100])
                results.append(None)

        return results

    async def search_and_browse(self, query: str, search_engine: str = "duckduckgo") -> List[ScrapedData]:
        """
        Search for query and browse top results automatically.

        Returns scraped content from top 3 results.
        """
        from ..search.web_search import SKTWebSearch

        searcher = SKTWebSearch()
        async with searcher:
            results = await searcher.search(query, num_results=3)

        scraped = []
        for result in results:
            try:
                data = await self.extract_content(result.url)
                scraped.append(data)
                self._logger.info("page_scraped", url=result.url, title=data.title[:50])
            except Exception as e:
                self._logger.warning("scrape_failed", url=result.url, error=str(e)[:100])

        return scraped
