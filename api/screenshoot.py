import asyncio
import os

from time import sleep
from typing import Optional
from cloakbrowser import launch_async as launch

async def take_screenshot(year: int, month: int) -> Optional[str]:
    """
    Take a screenshot of the fan progress report page for the specified month and save it as a PNG file.
    The function launches a headless browser, navigates to the local URL of the fan report, 
    and captures a screenshot of the relevant section of the page. 
    The screenshot is saved in the "Screenshots" directory with the filename format "YYYYMM.png".
    Args:
        year (int): The year for which to take the screenshot.
        month (int): The month for which to take the screenshot.
    Returns:
        Optional[str]: The path to the saved screenshot if successful, otherwise None.
    """
    url = f"localhost:5000/fans?year={year}&month={month}"
    try:
        browser = await launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await asyncio.sleep(2)
        os.makedirs("../Screenshots", exist_ok=True)
        # await page.screenshot(path=f"../Screenshots/{year}{month:02d}.png")
        await page.locator(".table-container.glass-panel").screenshot(path=f"../Screenshots/{year}{month:02d}.png")
        return f"../Screenshots/{year}{month:02d}.png"
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return None

if __name__ == "__main__":
    take_screenshot(2026, 8)
