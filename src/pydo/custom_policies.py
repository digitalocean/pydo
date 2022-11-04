from azure.core.pipeline.policies import HttpLoggingPolicy


class CustomHttpLoggingPolicy(HttpLoggingPolicy):

    # ALLOWED_HEADERS lists headers that will not be redacted when logging
    ALLOWED_HEADERS = set(
        [
            "x-request-id",
            "ratelimit-limit",
            "ratelimit-remaining",
            "ratelimit-reset",
            "x-gateway",
            "x-request-id",
            "x-response-from",
            "CF-Cache-Status",
            "Expect-CT",
            "Server",
            "CF-RAY",
            "Content-Encoding",
        ]
    )

    def __init__(self, logger=None, **kwargs):
        super().__init__(logger, **kwargs)
        self.allowed_header_names.update(self.ALLOWED_HEADERS)
