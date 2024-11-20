import asyncio
import re
import traceback
from typing import Dict
import aiohttp
from bs4 import BeautifulSoup
from bot.utils.logger import logger, dev_logger


class NotPXAPIChecker:
    RETRY_DELAY = 5
    BASE_URL = "https://app.notpx.app"

    async def check_api(
        self,
        session: aiohttp.ClientSession,
        notpx_headers: Dict[str, str],
        attempts: int = 1,
    ) -> bool:
        """
        Checks the NotPX API for the correct URL.

        Args:
            session (aiohttp.ClientSession): The aiohttp session to use for requests.
            notpx_headers (Dict[str, str]): The headers to use for the request.
            attempts (int, optional): The number of attempts to make. Defaults to 1.

        Returns:
            bool: True if the API URL is correct, False otherwise.
        """
        try:
            response = await session.get(self.BASE_URL, headers=notpx_headers)
            response.raise_for_status()
            html_content = await response.text()

            soup = BeautifulSoup(html_content, "html.parser")

            script_tags = soup.find_all("script")

            pattern = re.compile(r"/assets/index-[a-zA-Z0-9]+\.js")
            result = None

            for tag in script_tags:
                src = tag.get("src")
                if src and pattern.match(src):
                    result = src
                    break

            if not result:
                return False

            js_url = f"{self.BASE_URL}{result}"

            response = await session.get(js_url, headers=notpx_headers)
            response.raise_for_status()
            js_content = await response.text()

            match = re.search(r'VITE_API_URL:\s*"([^"]+)"', js_content)

            if not match:
                return False

            api_url = match.group(1)

            if api_url != "https://notpx.app/api/v1/":
                return False

            return True

        except Exception:
            if attempts <= 3:
                logger.warning(
                    f"API Checker | Failed to check NotPX API, retrying in {self.RETRY_DELAY} seconds | Attempts: {attempts}"
                )
                dev_logger.warning(f"API Checker | {traceback.format_exc()}")
                await asyncio.sleep(self.RETRY_DELAY)
                return await self.check_api(
                    session=session, notpx_headers=notpx_headers, attempts=attempts + 1
                )
            raise Exception("Error while checking NotPX API")
