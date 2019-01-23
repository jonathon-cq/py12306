import requests
from requests.exceptions import *

from py12306.proxies.proxies import Proxy
from py12306.helpers.func import *
from requests_html import HTMLSession, HTMLResponse

requests.packages.urllib3.disable_warnings()


class Request(HTMLSession):
    """
    请求处理类
    """

    # session = {}

    def __init__(self, use_proxy=False):
        super().__init__()
        self.use_proxy = use_proxy

    def save_to_file(self, url, path):
        response = self.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        return response

    @staticmethod
    def _handle_response(response, **kwargs) -> HTMLResponse:
        """
        扩充 response
        :param response:
        :param kwargs:
        :return:
        """
        response = HTMLSession._handle_response(response, **kwargs)
        expand_class(response, 'json', Request.json)
        return response

    def add_response_hook(self, hook):
        exist_hooks = self.hooks['response']
        if not isinstance(exist_hooks, list): hooks = [exist_hooks]
        hooks.append(hook)
        self.hooks['response'] = hooks
        return self

    def json(self, default={}):
        """
        重写 json 方法，拦截错误
        :return:
        """
        from py12306.app import Dict
        try:
            result = self.old_json()
            return Dict(result)
        except:
            return Dict(default)

    def request(self, *args, **kwargs):  # 拦截所有错误
        try:
            proxies = None
            if self.use_proxy:
                proxies = Proxy.get_proxy()
                if kwargs.get('timeout') is None:
                    kwargs.setdefault('timeout', Proxy.get_timeout())
            response = super().request(proxies=proxies, *args, **kwargs)
            if self.use_proxy and response.status_code != 200:
                Proxy.update_proxy()
            return response
        except RequestException as e:
            from py12306.log.common_log import CommonLog
            if self.use_proxy:
                timeout = str(e).find('ConnectTimeoutError') > 0
                Proxy.update_proxy(timeout)
            if e.response:
                response = e.response
            else:
                response = HTMLResponse(HTMLSession)
                # response.status_code = 500
                expand_class(response, 'json', Request.json)
            response.reason = response.reason if response.reason else CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR
            return response

    def cdn_request(self, url: str, cdn=None, method='GET', **kwargs):
        from py12306.helpers.api import HOST_URL_OF_12306
        from py12306.helpers.cdn import Cdn
        if not cdn: cdn = Cdn.get_cdn()
        url = url.replace(HOST_URL_OF_12306, cdn)

        return self.request(method, url, headers={'Host': HOST_URL_OF_12306}, verify=False, **kwargs)
