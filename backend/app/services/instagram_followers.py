from playwright.sync_api import sync_playwright
import re


def parse_followers(text: str) -> int:

    text = text.lower().replace(",", "").strip()

    if text.endswith("k"):
        return int(float(text[:-1]) * 1000)

    if text.endswith("m"):
        return int(float(text[:-1]) * 1000000)

    return int(float(text))


def get_instagram_followers(username: str) -> int:

    url = f"https://www.instagram.com/{username}/"

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        page.goto(
            url,
            wait_until="networkidle",
            timeout=30000
        )

        html = page.content()

        browser.close()

    patterns = [
        r'([\d.,]+[KMkm]?) Followers',
        r'"edge_followed_by"\:\{"count"\:(\d+)'
    ]

    for pattern in patterns:

        m = re.search(pattern, html)

        if m:

            value = m.group(1)

            try:
                return parse_followers(value)
            except:
                return int(value)

    return 0