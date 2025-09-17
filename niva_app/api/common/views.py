"""
Module: niva_app.api.common.views

Common views for API

This module contains common views for API

Classes:
    - ResponseMessageMixin: Mixin class to set and get response message
    - BaseAPI: Base API class for all APIs
    - OpenAPI: Open API class for APIs that do not require authentication

"""
import json
import urllib
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Type

from google.cloud import storage
from google.oauth2 import service_account
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from rest_framework.authentication import TokenAuthentication, get_authorization_header, BaseAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer, CharField, BooleanField

from niva_app.models import User


class ResponseMessageMixin:
    _response_message = None

    def set_response_message(self, message):
        self._response_message = message

    def get_response_message(self):
        return self._response_message


class BaseAPI(GenericAPIView, ResponseMessageMixin):
    """
    Base API class for all APIs

    This class is the base class for all APIs. It provides common methods and properties for all APIs.
    This class can be used to created protected APIs.

    Properties:
        - input_serializer_class: Serializer
        - authentication_classes: List[Type[BaseAuthentication]]
        - permission_classes: List[Type[BasePermission]]

    Methods:
        - validate_data: Validate the given data using the given serializer class
        - validate_input_data: Validate the input data using the input serializer class
        - get_user: Get the current user
        - get_response_400: Get the response with status 400
        - get_response_200: Get the response with status 200
    """

    input_serializer_class = None
    query_params_serializer_class = None
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print("--->", request.headers)  # Debugging

    def validate_data(
            self, serializer_class: Type[Serializer], data: Dict[str, Any], *args, **kwargs
    ) -> Dict[str, Any]:
        serializer = serializer_class(data=data, *args, **kwargs)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def validate_input_data(self, *args, **kwargs) -> Dict[str, Any]:
        return self.validate_data(self.input_serializer_class, self.request.data, *args, **kwargs)  # type: ignore

    def validate_query_params(self, *args, **kwargs) -> Dict[str, Any]:
        return self.validate_data(self.query_params_serializer_class, self.request.query_params, *args,
                                  **kwargs)  # type: ignore

    def get_user(self) -> User:
        return self.request.user  # type: ignore

    def get_response_400(self, message=None):
        if message is not None:
            self.set_response_message(message)
        return Response(
            status=HTTP_400_BAD_REQUEST,
            data={"message": message} if message else {}
        )

    def get_response_200(self, **kwargs):
        return Response(
            status=HTTP_200_OK,
            data=kwargs
        )

class OpenAPI(BaseAPI):
    """
    Open API class for APIs that do not require authentication

    This class is used for APIs that do not require authentication. It is a subclass of BaseAPI.
    It does not require authentication and permission.

    Properties:
        - authentication_classes: List[Type[BaseAuthentication]]
        - permission_classes: List[Type[BasePermission]]

    """

    authentication_classes = ()
    permission_classes = ()
