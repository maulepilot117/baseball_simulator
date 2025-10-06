#!/usr/bin/env python3
"""
Debug script to find the season selector on umpscorecards.com
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_season_selector():
    """Inspect the page to find season selector"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()

        print("Navigating to umpscorecards.com/umpires...")
        await page.goto('https://umpscorecards.com/umpires', wait_until='domcontentloaded', timeout=60000)

        # Wait for page to load
        await page.wait_for_timeout(5000)

        # Take screenshot
        await page.screenshot(path='/tmp/umpires_debug.png')
        print("Screenshot saved to /tmp/umpires_debug.png")

        # Get page HTML
        html = await page.content()

        # Look for select elements
        selects = await page.query_selector_all('select')
        print(f"\nFound {len(selects)} select elements:")
        for i, select in enumerate(selects):
            name = await select.get_attribute('name')
            id_attr = await select.get_attribute('id')
            aria_label = await select.get_attribute('aria-label')
            class_attr = await select.get_attribute('class')

            print(f"\n  Select {i+1}:")
            print(f"    name: {name}")
            print(f"    id: {id_attr}")
            print(f"    aria-label: {aria_label}")
            print(f"    class: {class_attr}")

            # Get options
            options = await select.query_selector_all('option')
            print(f"    options ({len(options)}):")
            for opt in options[:10]:  # First 10 options
                text = await opt.inner_text()
                value = await opt.get_attribute('value')
                print(f"      - {text} (value={value})")

        # Look for buttons with year/season text
        print("\n\nLooking for year/season buttons...")
        for year in [2024, 2023, 2022, 2021, 2020]:
            buttons = await page.query_selector_all(f'button:has-text("{year}")')
            if buttons:
                print(f"  Found {len(buttons)} buttons with text '{year}'")
                for btn in buttons:
                    text = await btn.inner_text()
                    classes = await btn.get_attribute('class')
                    print(f"    - Text: {text}, Classes: {classes}")

        # Get body text to see layout
        body_text = await page.locator('body').inner_text()
        lines = body_text.split('\n')[:50]  # First 50 lines
        print("\n\nFirst 50 lines of page text:")
        for i, line in enumerate(lines):
            print(f"{i+1:3}: {line[:100]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_season_selector())
