

import pytest
import random
import string
from playwright.sync_api import sync_playwright, Page, expect


def generate_random_email():
    """Generates a random email address with a Gmail domain."""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{random_string}@gmail.com"


@pytest.fixture
def browser_context(playwright):
    """Setup browser context for tests."""
    browser = playwright.chromium.launch(headless=False, slow_mo=2000, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins, site-per-process"
    ])
    context = browser.new_context(viewport={"width": 1000, "height": 550})
    yield context
    context.close()
    browser.close()


def test_run(browser_context: Page):
    """Test Expensify sign-up process."""
    page = browser_context.new_page()
    random_email = '3u2jmfupwit8@gmail.com'

    page.goto("https://dev.new.expensify.com:8082/")
    page.get_by_test_id("username").fill(random_email)
    page.get_by_test_id("username").press("Enter")
    page.get_by_role("button", name="Join").click()

    # Check if "Track and budget expenses" is visible
    try:
        expect(page.locator("text=What do you want to do today?")).to_be_visible()
        page.get_by_text("Track and budget expenses").click()
        page.get_by_role("textbox", name="First name").fill("A")
        page.get_by_role("textbox", name="Last name").click()
        page.get_by_role("textbox", name="Last name").fill("User")
        page.get_by_role("button", name="Continue").click()
    except:
        pass

    page.get_by_label("My settings").click()
    page.get_by_text("Workspaces").first.click()
    page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
    page.get_by_label("New workspace").click()

    page.get_by_label("Back").click()
    page.get_by_label("Inbox").click()

    page.get_by_text("Concierge").nth(1).click()


    page.get_by_text("#admin").first.click()
    expect(page.get_by_text("Schedule a demo")).to_be_visible()
