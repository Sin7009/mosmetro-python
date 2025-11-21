import sys
import logging
import asyncio
import warnings
import typer
from httpx import AsyncClient
from user_agent import generate_user_agent

from . import __version__
from .gen204 import Gen204
from .providers import AVAILABLE_PROVIDERS
from .connect import connect
from .config import settings

# Создаем приложение
app = typer.Typer(add_completion=False)

# Настройка логов
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

async def login_logic(force: bool):
    """Основная логика подключения (вынесена в функцию)"""
    logging.info(f'Version: {__version__}')
    logging.info('Loaded providers: ' + ', '.join(p.__name__ for p in AVAILABLE_PROVIDERS))

    async with AsyncClient(verify=False, timeout=settings.timeout) as client:
        client.headers['user-agent'] = generate_user_agent()

        if not force:
            logging.info('Checking connection...')
            try:
                res204 = await Gen204.check(client)
                if res204.is_connected:
                    logging.info('Already connected')
                    return
            except Exception as e:
                logging.warning(f"Connection check failed: {e}")
                # Если проверка упала, но мы не форсим, попробуем продолжить,
                # но скорее всего нужен редирект.
                # В старой логике мы просто падали или шли дальше.
                pass
        
        # Если мы здесь, значит либо нет инета, либо --force
        # Нам нужен res204.response для начала авторизации. 
        # Если force=True, мы можем не иметь res204. 
        # Но connect() требует Response объекта для начала.
        
        # ПОВТОРЯЕМ ЛОГИКУ ПОЛУЧЕНИЯ РЕДИРЕКТА (если чека не было или он провалился)
        # Для упрощения используем тот же Gen204.check, так как он возвращает response.
        if 'res204' not in locals():
             res204 = await Gen204.check(client)

        if not res204.response:
             logging.error('Error: Unable to get initial redirect (Captive Portal not found)')
             sys.exit(1)

        try:
            if await connect(client, res204.response):
                logging.info("Connected successfully! :3")
            else:
                logging.info("Connection failed :(")
                sys.exit(1)
        except Exception as e:
             logging.error(f"Connection process failed with error: {e}")
             sys.exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Force login attempt even if connected"),
):
    """
    Moscow Metro Wi-Fi CLI.
    Автоматически подключается к сети, если не передана другая команда.
    """
    # Если пользователь не ввел подкоманду (например, status), запускаем логин
    if ctx.invoked_subcommand is None:
        asyncio.run(login_logic(force))


@app.command()
def status():
    """Проверить статус подключения (пример подкоманды)"""
    async def check_status():
        async with AsyncClient(verify=False, timeout=5.0) as client:
            client.headers['user-agent'] = generate_user_agent()
            res = await Gen204.check(client)
            if res.is_connected:
                typer.secho("Online 🟢", fg=typer.colors.GREEN, bold=True)
            else:
                typer.secho("Offline 🔴", fg=typer.colors.RED, bold=True)
    
    asyncio.run(check_status())


if __name__ == '__main__':
    app()