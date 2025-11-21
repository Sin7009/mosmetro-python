import asyncio
import logging
import sys
import warnings

import typer
from httpx import AsyncClient
from rich.console import Console
from rich.logging import RichHandler
from user_agent import generate_user_agent

from . import __version__
from .connect import connect
from .exceptions import MosMetroError
from .gen204 import Gen204
from .providers import AVAILABLE_PROVIDERS

# Suppress SSL Warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Initialize Typer app and Rich console
app = typer.Typer(help="Moscow Metro Wi-Fi CLI", add_completion=False)
console = Console()

# Configure logging to use Rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger("mosmetro")

async def do_login(debug: bool):
    if debug:
        logger.setLevel(logging.DEBUG)

    logger.info(f'Version: {__version__}')
    logger.info('Loaded providers: ' + ', '.join(p.__name__ for p in AVAILABLE_PROVIDERS))

    async with AsyncClient(verify=False) as client:
        client.headers['user-agent'] = generate_user_agent()

        logger.info('Checking connection...')
        try:
            res204 = await Gen204.check(client)
        except Exception as e:
             logger.error(f"Error checking connection: {e}")
             sys.exit(1)

        if res204.is_connected:
            logger.info('Already connected')
            return

        if not res204.response:
            logger.error('Error: Unable to get initial redirect')
            sys.exit(1)

        try:
            if await connect(client, res204.response):
                logger.info("Connected successfully! :3")
            else:
                logger.info("Connection failed :(")
                sys.exit(1)
        except MosMetroError as e:
             logger.error(f"Connection failed: {e}")
             sys.exit(1)
        except Exception as e:
             logger.exception(f"Unexpected error: {e}")
             sys.exit(1)

@app.command(name="login")
def login_cmd(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    """
    Attempt to log in to the Wi-Fi network.
    """
    asyncio.run(do_login(debug))

@app.command(name="status")
def status_cmd(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
):
    """
    Check the current connection status.
    """
    async def check_status():
         if debug:
            logger.setLevel(logging.DEBUG)
         async with AsyncClient(verify=False) as client:
             res = await Gen204.check(client)
             if res.is_connected:
                 console.print("[bold green]Connected[/bold green]")
             else:
                 console.print("[bold red]Disconnected[/bold red]")

    asyncio.run(check_status())

if __name__ == '__main__':
    app()
