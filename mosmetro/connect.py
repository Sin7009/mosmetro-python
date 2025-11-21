import logging

from httpx import AsyncClient, RequestError, Response
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import settings
from .gen204 import Gen204
from .providers import match as match_provider
from .providers.base import Redirect
from .utils import any_redirect, response_to_str


@retry(
    stop=stop_after_attempt(settings.retries),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(RequestError)
)
async def connect(client: AsyncClient, res: Response) -> bool:
    # We wrap the whole connection process in retry?
    # Or just individual requests?
    # The instructions say: "Mechanizm Retry (Povtornye popytki) i Backoff... v fayle mosmetro/connect.py logika lineyna... Vnedrit HTTPAdapter... ili ispolzovat vstroennye vozmozhnosti httpx. Detal: Ispolzovat Exponential Backoff."
    # Since the whole process depends on state, it might be tricky to retry the whole `connect` function if it's partially done.
    # However, `connect` takes an initial response `res`.
    # If `connect` fails (e.g. network error in the middle), we can retry.
    # But we need to be careful about side effects (posting forms).
    # Generally, retrying idempotent requests is safe. POST might not be.
    # But in this captive portal context, it's usually fine to retry the whole flow if it failed.

    while True:
        provider = match_provider(client, res)

        if not provider:
            redirect = any_redirect(res)

            if redirect:
                logging.info(f'Following unknown redirect: {redirect}')
                res = await client.get(redirect, follow_redirects=False, timeout=settings.timeout)
                continue
            else:
                logging.info('----')
                logging.info(response_to_str(res))
                logging.info('----')
                logging.info('No more redirects')
                break

        logging.info(f'Provider: {provider.__class__.__name__}')
        result = await provider.run()

        if isinstance(result, Redirect):
            logging.info(f'Following post-auth redirect: {result.url}')
            res = await client.get(result.url, follow_redirects=False, timeout=settings.timeout)
            continue

        if not result.success:
            return False

        break

    logging.info('Checking connection...')
    res204 = await Gen204.check(client)
    return res204.is_connected
