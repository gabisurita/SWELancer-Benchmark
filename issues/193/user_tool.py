import os
import random
import string

import pytest
from playwright.async_api import Browser, Page, TimeoutError, async_playwright
from utils.trace_cleaner import trace_cleaner

WORKSPACE_NAME = "pyPtFh23"
EMAIL_USERNAME = "xecuycismfsga"
EMAIL_ALIAS = "kj56jrdw"
USER_EMAIL = f"{EMAIL_USERNAME}+{EMAIL_ALIAS}@gmail.com"
PASSWORD = ""
SLOW_MO: int | None = 500
PROXY_URL = os.getenv("PROXY_URL")


def generate_random_string(length=6):
    letters_and_digits = string.ascii_letters + string.digits
    return "".join(random.choice(letters_and_digits) for _ in range(length))


def generate_random_email(alias: str = generate_random_string()):
    return f"{EMAIL_USERNAME}+{alias}@gmail.com"


async def get_magic_code(page: Page, _user_email: str = USER_EMAIL, _password: str = PASSWORD):
    return "123456"


async def create_user(page: Page, firstname: str = "User", lastname: str = EMAIL_ALIAS):
    await page.get_by_role("button", name="Join").click()

    # Update profile
    await page.get_by_text("Track and budget expenses").click()
    await page.get_by_role("textbox", name="First name").fill(firstname)
    await page.get_by_role("textbox", name="Last name").fill(lastname)
    await page.get_by_role("button", name="Continue").click()


async def login(page: Page):
    # get current timestamp
    magic_code = await get_magic_code(page)

    if magic_code is None:
        raise ValueError("Failed to retrieve magic code")

    await page.get_by_role("textbox").fill(magic_code)


async def login_or_create_user(page: Page, last_name: str = EMAIL_ALIAS, user_email: str = USER_EMAIL):
    await page.goto("https://dev.new.expensify.com:8082/")
    await page.get_by_test_id("username").fill(user_email)
    await page.get_by_role("button", name="Continue").click()

    try:
        await page.get_by_role("button", name="Join").wait_for(state="visible", timeout=2000)
        await create_user(page, last_name)
    except TimeoutError:
        await login(page)

    await page.get_by_label("Inbox").wait_for(state="visible", timeout=10000)


async def create_workspace(page: Page, workspace_name: str = WORKSPACE_NAME):
    """
    Create a workspace if it does not already exist
    """
    await page.get_by_label("My Settings").click()
    await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").click()

    try:
        await (page.locator('button[aria-label="row"]').filter(has_text=workspace_name).last.click(timeout=3000))
    except TimeoutError:
        await page.get_by_label("New workspace").last.click()

        await page.get_by_text("Name", exact=True).click()
        name_input = page.get_by_role("textbox", name="Name")
        await name_input.clear()
        await name_input.type(workspace_name, delay=200)
        await page.get_by_role("button", name="Save").click()


async def setup_workspace(browser: Browser):
    admin_context = await browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    admin_page = await admin_context.new_page()

    await login_or_create_user(admin_page)

    await create_workspace(admin_page)

    await admin_page.get_by_role("button", name="Share").click()
    await admin_page.get_by_label("Copy URL").click()
    await admin_page.wait_for_timeout(1000)  # wait for clipboard to be populated
    workspace_url = await admin_page.evaluate("navigator.clipboard.readText()")
    return workspace_url


@pytest.mark.asyncio(scope="session")
async def test_workspace_access():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            proxy={"server": PROXY_URL} if PROXY_URL else None,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            slow_mo=SLOW_MO,
            channel="chromium",
        )

        # Create a new context for the main test and start tracing
        context = await browser.new_context()
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)

        try:
            workspace_url = await setup_workspace(browser)

            page = await context.new_page()

            restricted_user_alias = generate_random_string()
            restricted_user_email = generate_random_email(restricted_user_alias)

            await login_or_create_user(page, user_email=restricted_user_email, last_name=restricted_user_alias)

            await page.goto(workspace_url)

            await (page.locator('button[aria-label="row"]').filter(has_text=WORKSPACE_NAME).last.wait_for(state="visible", timeout=10000))

            await page.close()
            await context.close()
        finally:
            # Stop tracing and export the trace file
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            try:
                await context.tracing.stop(path=trace_path)
            except Exception as e:
                print(f"Error stopping tracing: {e}")

            try:
                trace_cleaner(trace_path)
            except Exception as e:
                print(f"Error cleaning trace: {e}")

            await browser.close()
