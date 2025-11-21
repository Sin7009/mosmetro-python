import random
import logging
import asyncio
from dataclasses import dataclass
from httpx import AsyncClient, Response, RequestError, ConnectError, TimeoutException
from .config import settings


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

        # We try 3 random URLs in parallel to speed up
        selected_urls = random.choices(urls, k=3)
        tasks = []

        for base_url in selected_urls:
            url = f'{schema}://{base_url}'
            tasks.append(Gen204._fetch(client, url))

        # Wait for the first successful response
        # This is slightly complex because we want the first *success*, not just first completed.
        # But asyncio.as_completed yields futures as they complete.

        for task in asyncio.as_completed(tasks):
            try:
                res = await task
                if res.status_code == 204 or res.is_redirect:
                    # If we get a 204 or a redirect (which means captive portal), we are good.
                    # But wait, gen204 checks specifically for 204 to confirm connection.
                    # If it's captive portal, it might return 204? No, it redirects or returns 200.
                    # Actually, Google gen204 returns 204 if connected.
                    return res

                # If we got a response but not 204/redirect, maybe just return it?
                # If we are looking for connection check, we want to know if it returns 204.
                # If it returns something else, it might be the captive portal page.
                return res

            except RequestError as ex:
                last_ex = ex
                continue

        if last_ex:
            raise last_ex

        # If no exception but no result (shouldn't happen if list is not empty and we wait for all), raise generic
        raise RequestError("All requests failed")

    @staticmethod
    async def _fetch(client: AsyncClient, url: str) -> Response:
        logging.debug(f'Gen204 requesting {url}')
        try:
            res = await client.get(url, follow_redirects=False, timeout=settings.timeout)
            logging.debug(f'Gen204 | {url} | {res.status_code}')
            return res
        except Exception as e:
            logging.debug(f'Gen204 | {url} | {e}')
            raise e

    @staticmethod
    async def check(client: AsyncClient) -> Gen204Res:
        """Returns gen204 response and false negative (if exists)."""
        # Unreliable HTTP check (needs to be verified by HTTPS)
        try:
            unrel = await Gen204.request(client, "http", settings.gen204.default_urls)
        except RequestError:
            # network is most probably unreachable
            return Gen204Res()

        # Reliable HTTPS check
        try:
            rel_https = await Gen204.request(client, "https", settings.gen204.reliable_urls)
        except RequestError:
            rel_https = None

        if unrel.status_code == 204:
            if not rel_https or rel_https.status_code != 204:
                # Reliable HTTP check
                try:
                    rel_http = await Gen204.request(client, "http", settings.gen204.reliable_urls)
                except RequestError:
                    rel_http = None

                if rel_http and rel_http.status_code != 204:
                    return Gen204Res(rel_http)  # false positive
            else:
                return Gen204Res(rel_https)  # confirmed positive
        else:
            if not rel_https:
                return Gen204Res(unrel)  # confirmed negative
            elif rel_https.status_code == 204:
                return Gen204Res(rel_https, unrel)  # false negative

        logging.warning('Gen204 | Unexpected state')
        return Gen204Res()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    async def main():
        async with AsyncClient() as client:
            res_204 = await Gen204.check(client)
            logging.info(f'Connected: {res_204.is_connected}')
            logging.info(f'False negative: {res_204.false_negative is not None}')

    asyncio.run(main())
