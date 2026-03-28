"""
Impactpool Internship Crawler
──────────────────────────────
- URL filter : ?s%5B%5D=13  → Seniority = Internship (356 results)
- Recency    : only cards with <span class="ip-badge-text">New</span>
               (Impactpool shows "New" badge for recently posted jobs)
- Stops      : when a full page has zero "New" cards (we've passed the fresh content)
"""

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE_URL      = "https://www.impactpool.org"
INTERN_URL    = f"{BASE_URL}/search?s%5B%5D=13"   # Internship seniority filter
_INTERN_RE    = re.compile(r"intern", re.IGNORECASE)


async def scrape_internships() -> list[dict]:
    jobs: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        page_num = 1
        while True:
            url = INTERN_URL if page_num == 1 else f"{INTERN_URL}&page={page_num}"
            print(f"[crawler] Fetching page {page_num}: {url}")

            await page.goto(url, wait_until="networkidle", timeout=30_000)

            # Wait for job cards to appear
            try:
                await page.wait_for_selector("div.job", timeout=15_000)
            except PWTimeout:
                print(f"[crawler] No job cards on page {page_num}, stopping.")
                break

            # Extract all job containers on this page
            cards_data = await page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('div.job').forEach(div => {
                    // Is this card marked "New"?
                    const badge = div.querySelector('.ip-badge-text');
                    const isNew = badge && badge.innerText.trim() === 'New';

                    const link = div.querySelector('a[href^="/jobs/"]');
                    if (!link) return;

                    const href  = link.getAttribute('href') || '';
                    const title = (div.querySelector('[type="cardTitle"]') || {}).innerText?.trim() || '';
                    const org   = (div.querySelector('[type="bodyEmphasis"]') || {}).innerText?.trim() || '';

                    // Location and seniority are in the second bodyEmphasis children
                    const emphasisEls = div.querySelectorAll('[type="bodyEmphasis"]');
                    const loc         = emphasisEls[1]?.innerText?.trim() || '';
                    const seniority   = emphasisEls[2]?.innerText?.trim() || '';

                    const match = href.match(/\\/jobs\\/(\\d+)/);
                    if (match && title) {
                        results.push({
                            id:           match[1],
                            title:        title,
                            organization: org,
                            location:     loc,
                            job_type:     seniority,
                            url:          href,
                            is_new:       isNew,
                        });
                    }
                });
                return results;
            }""")

            new_on_page   = [c for c in cards_data if c["is_new"]]
            total_on_page = len(cards_data)

            print(f"[crawler] Page {page_num}: {total_on_page} cards total, {len(new_on_page)} marked 'New'")

            # Only keep "New" cards
            for job in new_on_page:
                job["url"] = f"{BASE_URL}{job['url']}"
                jobs.append(job)

            # Stop when no "New" cards on this page — we've passed the recent content
            if len(new_on_page) == 0:
                print("[crawler] No 'New' cards on this page — stopping pagination.")
                break

            # Check if there's a next page
            has_more = await page.evaluate("""() => {
                const showMore = document.querySelector('a[href*="page="]');
                return !!showMore;
            }""")
            if not has_more:
                print("[crawler] No more pages.")
                break

            page_num += 1

        await browser.close()

    # Deduplicate by job ID
    seen, unique = set(), []
    for j in jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            unique.append(j)

    print(f"[crawler] Done: {len(unique)} new internship(s) found.")
    return unique


if __name__ == "__main__":
    results = asyncio.run(scrape_internships())
    print(f"\n{'='*60}")
    print(f"Total: {len(results)} new internships (last 48h)")
    for j in results[:20]:
        print(f"  [{j['job_type']}] {j['title']}")
        print(f"    {j['organization']} | {j['location']}")
        print(f"    {j['url']}")
