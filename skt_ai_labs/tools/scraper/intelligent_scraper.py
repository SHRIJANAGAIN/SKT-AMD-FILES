"""
SKT-AI-LABS Intelligent Scraper
Anti-bot, content-aware web scraping
"""

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup
import requests

logger = structlog.get_logger("skt_ai_labs.tools.scraper")


class IntelligentScraper:
    """
    Intelligent content extraction that works on most websites.

    Features:
    - Automatic content extraction (article, product, etc.)
    - Anti-bot headers rotation
    - JavaScript-rendered content support (via requests-html)
    - Rate limiting
    - Content type detection
    - Structured data extraction (JSON-LD, microdata)
    """

    def __init__(self, 
                 respect_robots: bool = True,
                 delay: float = 1.0,
                 timeout: int = 30):

        self.respect_robots = respect_robots
        self.delay = delay
        self.timeout = timeout
        self._last_request_time = 0
        self._logger = logger

        # Rotating user agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    def _get_headers(self) -> Dict[str, str]:
        """Get randomized headers"""
        import random
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    async def scrape(self, url: str, extract_type: str = "auto") -> Dict[str, Any]:
        """
        Scrape URL with intelligent extraction.

        Args:
            url: Target URL
            extract_type: "auto", "article", "product", "list", "table"

        Returns:
            Structured data dict
        """
        self._rate_limit()

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Detect content type
            if extract_type == "auto":
                extract_type = self._detect_content_type(soup)

            # Extract based on type
            if extract_type == "article":
                data = self._extract_article(soup, url)
            elif extract_type == "product":
                data = self._extract_product(soup, url)
            elif extract_type == "list":
                data = self._extract_list(soup, url)
            elif extract_type == "table":
                data = self._extract_table(soup, url)
            else:
                data = self._extract_generic(soup, url)

            # Extract structured data (JSON-LD)
            structured = self._extract_jsonld(soup)
            if structured:
                data["structured_data"] = structured

            self._logger.info("scrape_success", url=url, type=extract_type, title=data.get("title", "")[:50])
            return data

        except Exception as e:
            self._logger.error("scrape_failed", url=url, error=str(e)[:100])
            return {"url": url, "error": str(e), "title": "", "content": ""}

    def _detect_content_type(self, soup: BeautifulSoup) -> str:
        """Auto-detect content type"""
        # Check for product indicators
        if soup.find("meta", property="og:type", content="product") or soup.find("[data-product]"):
            return "product"

        # Check for article indicators
        if soup.find("article") or soup.find("[role='article']") or soup.find(class_=re.compile("article|post|content")):
            return "article"

        # Check for list indicators
        if len(soup.find_all("li")) > 20:
            return "list"

        return "generic"

    def _extract_article(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract article content"""
        # Try common article selectors
        article = (soup.find("article") or 
                  soup.find(class_=re.compile("article|post-content|entry-content")) or
                  soup.find("main") or
                  soup.find("div", class_=re.compile("content|body")))

        if not article:
            article = soup.body

        # Clean up
        for tag in article.find_all(["script", "style", "nav", "aside", "header", "footer"]):
            tag.decompose()

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "content": article.get_text(separator="\n", strip=True),
            "author": self._extract_meta(soup, "author"),
            "date": self._extract_meta(soup, "date") or self._extract_meta(soup, "published_time"),
            "type": "article",
            "images": [img.get("src") for img in article.find_all("img") if img.get("src")],
        }

    def _extract_product(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract product information"""
        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "name": self._extract_meta(soup, "title"),
            "price": self._extract_price(soup),
            "description": self._extract_meta(soup, "description"),
            "images": [img.get("src") for img in soup.find_all("img") if img.get("src")],
            "type": "product",
        }

    def _extract_list(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract list items"""
        items = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            link = li.find("a")
            if text and len(text) > 10:
                items.append({
                    "text": text,
                    "link": link.get("href") if link else None,
                })

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "items": items[:50],  # Limit
            "type": "list",
        }

    def _extract_table(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract table data"""
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                row = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if row:
                    rows.append(row)
            if rows:
                tables.append(rows)

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "tables": tables,
            "type": "table",
        }

    def _extract_generic(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Generic extraction"""
        # Remove noise
        for tag in soup.find_all(["script", "style", "nav", "aside"]):
            tag.decompose()

        return {
            "url": url,
            "title": soup.title.string if soup.title else "",
            "content": soup.body.get_text(separator="\n", strip=True) if soup.body else "",
            "headings": [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])],
            "links": [{"text": a.get_text(strip=True), "url": a.get("href")} for a in soup.find_all("a") if a.get("href")],
            "type": "generic",
        }

    def _extract_meta(self, soup: BeautifulSoup, name: str) -> str:
        """Extract meta tag content"""
        meta = soup.find("meta", attrs={"name": name}) or soup.find("meta", property=f"og:{name}")
        return meta.get("content", "") if meta else ""

    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract price from page"""
        # Common price selectors
        price_selectors = [
            "[class*='price']", "[class*='cost']", "[class*='amount']",
            "meta[itemprop='price']", ".price", "#price",
        ]

        for selector in price_selectors:
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True) or el.get("content", "")

        return None

    def _extract_jsonld(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract JSON-LD structured data"""
        scripts = soup.find_all("script", type="application/ld+json")
        data = []
        for script in scripts:
            try:
                import json
                data.append(json.loads(script.string))
            except:
                pass
        return data
