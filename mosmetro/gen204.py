import asyncio
import logging
import random
from dataclasses import dataclass

from httpx import AsyncClient, RequestError, Response, TimeoutException

from .config import settings
from .exceptions import NetworkError, NetworkTimeoutError


@dataclass
class Gen204Res:
    response: Response | None = None
    false_negative: Response | None = None

    @property
    def is_connected(self) -> bool:
        if not self.response:
            return False

        return self.response.status_code == 204


class Gen204:
    @staticmethod
    async def request(client: AsyncClient, schema: str, urls: list[str]) -> Response:
        last_ex = None

        selected_urls = random.choices(urls, k=3)
        tasks = []

        for base_url in selected_urls:
            url = f'{schema}://{base_url}'
            tasks.append(asyncio.create_task(Gen204._fetch(client, url)))

        for task in asyncio.as_completed(tasks):
            try:
                res = await task
                if res.status_code == 204 or res.is_redirect:
                    return res
                return res

            except (RequestError, NetworkError) as ex:
                last_ex = ex
                continue

        if last_ex:
            raise last_ex

        raise NetworkError("All Gen204 requests failed")

    @staticmethod
    async def _fetch(client: AsyncClient, url: str) -> Response:
        logging.debug(f'Gen204 requesting {url}')
        try:
            res = await client.get(url, follow_redirects=False, timeout=settings.timeout)
            logging.debug(f'Gen204 | {url} | {res.status_code}')
            return res
        except TimeoutException as e:
            logging.debug(f'Gen204 | {url} | Timeout: {e}')
            raise NetworkTimeoutError(f"Timeout connecting to {url}") from e
        except RequestError as e:
            logging.debug(f'Gen204 | {url} | {e}')
            raise NetworkError(f"Failed to connect to {url}") from e

    @staticmethod
    async def check(client: AsyncClient) -> Gen204Res:
        """Returns gen204 response and false negative (if exists)."""
        try:
            unrel = await Gen204.request(client, "http", settings.gen204.default_urls)
        except (RequestError, NetworkError):
            return Gen204Res()

        try:
            rel_https = await Gen204.request(client, "https", settings.gen204.reliable_urls)
        except (RequestError, NetworkError):
            rel_https = None

        if unrel.status_code == 204:
            if not rel_https or rel_https.status_code != 204:
                try:
                    rel_http = await Gen204.request(client, "http", settings.gen204.reliable_urls)
                except (RequestError, NetworkError):
                    rel_http = None

                if rel_http and rel_http.status_code != 204:
                    return Gen204Res(rel_http)
            else:
                return Gen204Res(rel_https)
        else:
            if not rel_https:
                return Gen204Res(unrel)
            elif rel_https.status_code == 204:
                return Gen204Res(rel_https, unrel)

        logging.warning('Gen204 | Unexpected state')
        return Gen204Res()
