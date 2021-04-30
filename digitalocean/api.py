from azure.core.credentials import AccessToken


class TokenCredential:
    def __init__(self, api_token, expires_on):
        self._token = api_token
        self._expires_on = expires_on

    def get_token(self, *args, **kwargs) -> AccessToken:
        # token = environ.get("DO_TOKEN")
        at = AccessToken(self._token, expires_on=self._expires_on)
        return at
