"""
Run this script to capture what network requests Impactpool makes.
python3 diagnose.py
"""
import asyncio
import json
from playwright.async_api import async_playwright

BASE_URL = "https://www.impactpool.org"

async def diagnose():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)   # visible so you can watch
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        all_requests = []

        async def on_request(req):
            if req.resource_type in ("xhr", "fetch", "document"):
                entry = {
                    "type":   req.resource_type,
                    "method": req.method,
                    "url":    req.url,
                    "body":   req.post_data or "",
                }
                all_requests.append(entry)

        async def on_response(res):
            # Only capture JSON responses from XHR/fetch
            if res.request.resource_type in ("xhr", "fetch"):
                ct = res.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        body = await res.json()
                        # Save to a file named after the URL slug
                        slug = res.url.split("/")[-1].split("?")[0][:40]
                        fname = f"/tmp/impactpool_response_{slug}.json"
                        with open(fname, "w") as f:
                            json.dump({"url": res.url, "status": res.status, "body": body}, f, indent=2)
                        print(f"[response] {res.status} {res.url[:100]}")
                        print(f"           → saved to {fname}")
                    except Exception as e:
                        print(f"[response-err] {e}")

        page.on("request", on_request)
        page.on("response", on_response)

        # ── Step 1: Load plain search ─────────────────────────────────────
        print("\n=== Step 1: Loading /search ===")
        await page.goto(f"{BASE_URL}/search", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Print the page URL and title
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Print all XHR/fetch so far
        print("\n--- XHR/Fetch requests so far ---")
        for r in all_requests:
            if r["type"] in ("xhr", "fetch"):
                print(f"  {r['method']} {r['url'][:120]}")
                if r["body"]:
                    print(f"    body: {r['body'][:200]}")

        all_requests.clear()

        # ── Step 2: Try clicking Seniority filter ────────────────────────
        print("\n=== Step 2: Clicking Seniority filter ===")

        # First, print all visible text on the page to find filter labels
        all_text = await page.locator("body").inner_text()
        lines = [l.strip() for l in all_text.splitlines() if l.strip()]
        # Find lines near "seniority"
        for i, line in enumerate(lines):
            if "seniority" in line.lower() or "intern" in line.lower():
                context_lines = lines[max(0,i-2):i+5]
                print(f"  Context around '{line}': {context_lines}")

        # Print all <a> and <button> elements text
        print("\n--- All buttons ---")
        buttons = await page.locator("button").all_text_contents()
        print([b.strip() for b in buttons if b.strip()])

        print("\n--- Filter-related links ---")
        links = await page.query_selector_all("a")
        for link in links:
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).strip()
            if any(k in (href+text).lower() for k in ("seniority","intern","filter","facet","level")):
                print(f"  [{text!r}] href={href!r}")

        # ── Step 3: Try to apply internship filter ───────────────────────
        print("\n=== Step 3: Applying Internship filter ===")

        # Try text-based click
        seniority_locators = [
            "text=Seniority",
            "text=Level",
            "text=Career Level",
            "text=Job Type",
        ]
        for sel in seniority_locators:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    print(f"  Found: {sel}")
                    await el.click(timeout=3000)
                    await page.wait_for_timeout(500)
                    break
            except Exception as e:
                print(f"  {sel} → {e}")

        # Look for Internship option
        intern_locators = [
            "text=Internship",
            "label:has-text('Internship')",
            "a:has-text('Internship')",
            "span:has-text('Internship')",
            "li:has-text('Internship')",
        ]
        for sel in intern_locators:
            try:
                el = page.locator(sel).first
                cnt = await el.count()
                print(f"  Internship locator '{sel}' count={cnt}")
                if cnt > 0:
                    # Get full HTML of the element
                    html = await el.evaluate("el => el.outerHTML")
                    print(f"    HTML: {html[:300]}")
                    await el.click(timeout=3000)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    print(f"    Clicked! New URL: {page.url}")

                    print("\n--- XHR/Fetch after filter click ---")
                    for r in all_requests:
                        if r["type"] in ("xhr", "fetch"):
                            print(f"  {r['method']} {r['url'][:120]}")
                            if r["body"]:
                                print(f"    body: {r['body'][:300]}")
                    break
            except Exception as e:
                print(f"  {sel} → {e}")

        # ── Step 4: Print current page URL and result count ─────────────
        print(f"\nFinal URL: {page.url}")
        count_el = await page.query_selector("h1, h2, [class*='result'], [class*='count']")
        if count_el:
            print(f"Count text: {await count_el.inner_text()}")

        # ── Step 5: Dump full list of links ─────────────────────────────
        job_links = await page.query_selector_all("a[href^='/jobs/']")
        print(f"\nJob cards on current page: {len(job_links)}")
        for lnk in job_links[:5]:
            href = await lnk.get_attribute("href")
            txt  = (await lnk.inner_text()).strip().splitlines()
            print(f"  {href} → {txt[:2]}")

        # ── Step 6: Print full page HTML (filter section only) ──────────
        print("\n=== Step 6: Filter section HTML ===")
        filter_selectors = [
            "[class*='filter']",
            "[class*='facet']",
            "[class*='sidebar']",
            "aside",
            "nav[class*='search']",
        ]
        for sel in filter_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    html = await el.evaluate("el => el.outerHTML")
                    print(f"\n--- {sel} HTML (first 2000 chars) ---")
                    print(html[:2000])
                    break
            except Exception:
                pass

        print("\n=== Done. Check /tmp/impactpool_response_*.json for API responses ===")
        await page.wait_for_timeout(3000)
        await browser.close()

asyncio.run(diagnose())
