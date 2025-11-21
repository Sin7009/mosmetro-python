import logging
from furl import furl
from httpx import Response
from pydantic import BaseModel, Field
from .base import Provider, Result, Redirect
from ..utils import any_redirect, merge_urls
from ..config import settings


class AuthStartData(BaseModel):
    class SegmentParams(BaseModel):
        class Common(BaseModel):
            class RedirectUrl(BaseModel):
                after_auth: str | None = Field(None, alias='afterAuth')

            redirect_url: RedirectUrl | None = Field(None, alias='redirectUrl')

        common: Common | None = None

    segment_params: SegmentParams | None = Field(None, alias='segmentParams')


class AuthCheckData(BaseModel):
    auth_error_code: str | None = None


class AuthWifiRu(Provider):
    @staticmethod
    def match(response: Response):
        url = furl(any_redirect(response))
        return url.host == 'auth.wi-fi.ru' and url.path == '/auth'


class AuthWifiRuMsk(Provider):
    PATHS = {
        'start': '/gapi/auth/start',
        'init': '/gapi/auth/init',
        'check': '/gapi/auth/check'
    }

    @staticmethod
    def match(response: Response):
        url = furl(any_redirect(response))
        return url.host == 'auth.wi-fi.ru' and url.path in ['', '/', '/new']

    async def run(self) -> Result:
        url = furl(any_redirect(self.response))

        segment = url.args.get('segment') or 'metro'
        # client_mac has higher priority
        mac = url.args.get('client_mac') or url.args.get('mac')

        # Follow first redirect
        logging.info('Opening auth page')
        # self.client is available now
        res = await self.client.get(str(url), timeout=settings.timeout)
        self.client.headers['referer'] = str(url)

        # Get auth page
        logging.info('Starting session')
        url.args.clear()
        url.args['segment'] = segment
        if mac:
            url.args['clientMac'] = mac
        url.path = self.PATHS['start']

        res = await self.client.get(str(url), timeout=settings.timeout)

        # Validation with Pydantic
        try:
            json_data = res.json()
            # The structure wraps actual data in "data" key based on previous safeget usage
            # safeget(res.json(), 'data', 'segmentParams', ...)
            # So the root response has 'data'.

            # Let's assume the response is { "data": ... }
            # I will define a wrapper model or just parse manually if it's simple.
            # The safeget usage: safeget(res.json(), 'data', 'segmentParams', 'common', 'redirectUrl', 'afterAuth')

            class ResponseWrapper(BaseModel):
                data: AuthStartData | None = None

            parsed = ResponseWrapper.model_validate(json_data)

            after_auth = None
            if parsed.data and parsed.data.segment_params and parsed.data.segment_params.common and parsed.data.segment_params.common.redirect_url:
                after_auth = parsed.data.segment_params.common.redirect_url.after_auth

        except Exception as e:
            logging.error(f"Failed to parse auth start response: {e}")
            after_auth = None

        if after_auth:
            logging.info(f'Post-auth redirect: {after_auth}')
            after_auth = merge_urls(str(self.response.request.url), after_auth)

        # Send login form
        logging.info('Initializing connection')
        url.path = self.PATHS['init']
        url.args.clear()
        res = await self.client.post(str(url), data={'mode': 0, 'segment': segment}, timeout=settings.timeout)
        res_data = res.json()
        logging.debug(res_data)

        # safeget(res_data, 'auth_error_code', default='')
        # Let's use Pydantic for this too.
        try:
            check_data = AuthCheckData.model_validate(res_data)
            error_code = check_data.auth_error_code or ''
        except Exception:
            error_code = ''

        if error_code.startswith('err_device_not_identified'):
            logging.error('Error: Device is not registered. Please go to https://wi-fi.ru')
            return Result(False)

        # Checking auth state
        logging.info('Checking connection')
        url.path = self.PATHS['check']
        res = await self.client.get(str(url), timeout=settings.timeout)
        res_data = res.json()
        logging.debug(res_data)

        if after_auth:
            return Redirect(url=after_auth)
        else:
            return Result(True)


class AuthWifiRuSpb(AuthWifiRuMsk):
    PATHS = {
        'start': '/spb/gapi/auth/start',
        'init': '/spb/gapi/auth/init',
        'check': '/spb/gapi/auth/check'
    }

    @staticmethod
    def match(response: Response):
        url = furl(any_redirect(response))
        return url.host == 'auth.wi-fi.ru' and url.path == '/spb/'
