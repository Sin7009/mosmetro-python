import pytest
import respx
from httpx import AsyncClient, Response, ConnectError
from mosmetro.gen204 import Gen204

@pytest.mark.asyncio
async def test_gen204_connected():
    # We disable assert_all_called because Gen204 makes random requests and we use broad regex mocks
    async with respx.mock(assert_all_called=False) as respx_mock:
        # Mock all http requests to generate_204
        respx_mock.route(method="GET", path__regex=r".*/generate_204").mock(return_value=Response(204))
        # Mock all https requests to generate_204 (and gen_204)
        respx_mock.route(method="GET", path__regex=r".*/gen_204").mock(return_value=Response(204))

        async with AsyncClient() as client:
            res = await Gen204.check(client)
            assert res.is_connected

@pytest.mark.asyncio
async def test_gen204_captive_portal():
    async with respx.mock(assert_all_called=False) as respx_mock:
        # Unreliable returns 200 (captive portal page) or redirect
        # We match any http request
        respx_mock.route(method="GET", scheme="http", path__regex=r".*/generate_204").mock(return_value=Response(200))

        # Reliable https fails
        # We must use a proper httpx exception so Gen204 catches it
        respx_mock.route(method="GET", scheme="https", path__regex=r".*/gen(erate)?_204").mock(side_effect=ConnectError("Network unreachable"))

        async with AsyncClient() as client:
            res = await Gen204.check(client)
            # If unreliable returns 200 and reliable fails, it should be considered NOT connected but with a response (captive portal)
            assert not res.is_connected
            assert res.response is not None
            assert res.response.status_code == 200
