from dataclasses import dataclass

from httpx import AsyncClient, Response


@dataclass
class Result:
    success: bool = False


@dataclass
class Redirect(Result):
    url: str = ""
    success: bool = True


class Provider:
    def __init__(self, client: AsyncClient, response: Response):
        self.client = client
        self.response = response

    async def run(self) -> Result:
        raise NotImplementedError()

    @staticmethod
    def match(response: Response):
        raise NotImplementedError()
