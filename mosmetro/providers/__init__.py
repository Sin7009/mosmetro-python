from httpx import Response, AsyncClient
from .base import Provider
from .mosmetro import AuthWifiRu, AuthWifiRuMsk, AuthWifiRuSpb

AVAILABLE_PROVIDERS = [AuthWifiRu, AuthWifiRuMsk, AuthWifiRuSpb]


def match(client: AsyncClient, response: Response) -> Provider | None:
    for subcls in AVAILABLE_PROVIDERS:
        try:
            if subcls.match(response):
                return subcls(client, response)
        except Exception:
            pass

    return None
