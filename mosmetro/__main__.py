import sys
import logging
import asyncio
import warnings
from httpx import AsyncClient
from user_agent import generate_user_agent

from . import __version__
from .gen204 import Gen204
from .providers import AVAILABLE_PROVIDERS
from .connect import connect
from .config import settings


async def main():
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO
    )

    # Suppress InsecureRequestWarning
    warnings.filterwarnings("ignore", message=".*InsecureRequestWarning.*")

    logging.info(f'Version: {__version__}')

    logging.info('Loaded providers: ' +
          ', '.join(p.__name__ for p in AVAILABLE_PROVIDERS))

    # Use AsyncClient
    async with AsyncClient(verify=False) as client:
        client.headers['user-agent'] = generate_user_agent()

        # Optional: User-Agent rotation logic could be added here or in a loop if we had a daemon mode.
        # For a single run, one UA is fine, but the instructions said: "Rotate User-Agent... if session lives long".
        # Since this script seems to run once and exit, generating one at start is fine.
        # But if we want to be robust, we can regenerate it if we retry?
        # The retry logic is in `connect`.
        # To implement UA rotation on retry, we would need to hook into the retry mechanism or just regenerate it before `connect`.

        logging.info('Checking connection...')
        res204 = await Gen204.check(client)

        if res204.is_connected:
            logging.info('Already connected')
            sys.exit(0)

        if not res204.response:
            logging.error('Error: Unable to get initial redirect')
            sys.exit(1)

        try:
            if await connect(client, res204.response):
                logging.info("Connected successfully! :3")
                sys.exit(0)
            else:
                logging.info("Connection failed :(")
                sys.exit(1)
        except Exception as e:
             logging.error(f"Connection process failed with error: {e}")
             sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
