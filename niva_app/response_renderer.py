"""
Module: niva_app.response_renderer

This module contains a custom JSON response renderer for Django REST framework.
It extends the default JSONRenderer to provide a standardized response format
for API responses, including custom handling for success, error messages, and
HTTP status codes.

Classes:
    JSONResponseRenderer: A custom renderer that formats the JSON response
    with additional fields such as code, message, success, data, and errors.
"""

from rest_framework.renderers import JSONRenderer


class JSONResponseRenderer(JSONRenderer):
    """
    Custom JSON response renderer for Django REST framework.

    This renderer formats the JSON response with additional fields such as
    code, message, success, data, and errors. This is referenced in the settings.py

    Attributes:
        None

    Methods:
        get_default_message: Get the default message based on the HTTP status code.
        render: Render the response data with the custom format.
    """

    @staticmethod
    def get_default_message(http_code):
        # TODO: define custom default messages here
        return ""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            # to handle response with no data
            data = {}
        response_data = {}
        status_code = renderer_context["response"].status_code
        response_data["code"] = (
            data.pop("error_code")
            if (isinstance(data, dict) and "error_code" in data)
            else status_code
        )
        response_data["message"] = (
            data.pop("message")
            if (isinstance(data, dict) and "message" in data)
            else self.get_default_message(status_code)
        )
        response_data["success"] = False
        response_data["data"] = None
        response_data["errors"] = None
        if 200 <= status_code < 300:
            response_data["success"] = True
            response_data["data"] = data if data else None
            if data == []:
                response_data["data"] = data
        else:
            if isinstance(data, dict) and "detail" in data:
                response_data["message"] = data.pop("detail")
            response_data["errors"] = (
                data["errors"] if isinstance(data, dict) and "errors" in data else data
            )
        if response_data.get("errors", None) and isinstance(
            response_data.get("errors", None), dict
        ):
            for key, value in response_data.get("errors").items():
                if isinstance(value, str):
                    response_data["errors"][key] = [value]
        if (
            status_code < 500
            and renderer_context.get("view", None)
            and hasattr(renderer_context["view"], "get_response_message")
            and renderer_context["view"].get_response_message()
        ):
            response_data["message"] = renderer_context["view"].get_response_message()
        response = super(JSONResponseRenderer, self).render(
            response_data, accepted_media_type, renderer_context
        )
        return response