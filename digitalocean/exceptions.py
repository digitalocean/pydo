from azure.core.exceptions import HttpResponseError


class BaseHTTPException(HttpResponseError):
    def __str__(self):
        return f"[BaseHTTPException] message={self.message} response={self.response}"


class APIError(Exception):
    def __init__(self, id_, message, request_id):
        self.id = id_
        self.message = message
        self.request_id = request_id
        super(APIError, self).__init__()

    def __str__(self):
        return f"[APIError] id={self.id} message={self.message} request_id={self.request_id}"


class Unprocessable(Exception):
    pass


class InvalidModelException(Exception):
    """Exception raised when a value does not match the expected model

    Attributes:
        value: The invalid object value
    """

    def __init__(self, value):
        self.value = value
        super(InvalidModelException, self).__init__()

    def __str__(self):
        return f"[InvalidModelException] {type(self.value)}"


class ModelValidationException(Exception):
    """Exception raised when a model validation fails

    Attributes:
        errors: List of validation errors
    """

    def __init__(self, errors: list):
        self.errors = errors
        super(ModelValidationException, self).__init__()

    def __str__(self):
        return f"[ModelValidationException] {self.errors}"
