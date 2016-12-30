"""
Tests for passing invalid endpoints which require a target ID to be given.
"""

import uuid
from urllib.parse import urljoin

import pytest
import requests
from requests import codes
from requests_mock import GET

from common.constants import ResultCodes
from tests.conftest import VuforiaServerCredentials
from tests.mock_vws.utils import assert_vws_failure
from vws._request_utils import authorization_header, rfc_1123_date


class Endpoint:
    """
    XXX
    """

    def __init__(self, path: str, method: int) -> None:
        """
        """
        self.path = path
        self.method = method


ENDPOINTS = [
    Endpoint(path='/targets', method=GET),
    Endpoint(path='/duplicates', method=GET),
]


@pytest.mark.usefixtures('verify_mock_vuforia')
@pytest.mark.parametrize('endpoint', ENDPOINTS)
class TestInvalidGivenID:
    """
    Tests for giving an invalid ID to endpoints which require a target ID to
    be given.
    """

    def test_not_real_id(self, endpoint: Endpoint,
                         vuforia_server_credentials: VuforiaServerCredentials,
                         ) -> None:
        """
        A `NOT_FOUND` error is returned when an endpoint is given a target ID
        of a target which does not exist.
        """
        request_path = endpoint.path + '/' + uuid.uuid4().hex
        date = rfc_1123_date()

        authorization_string = authorization_header(
            access_key=vuforia_server_credentials.access_key,
            secret_key=vuforia_server_credentials.secret_key,
            method=GET,
            content=b'',
            content_type='',
            date=date,
            request_path=request_path,
        )

        headers = {
            "Authorization": authorization_string,
            "Date": date,
        }

        url = urljoin('https://vws.vuforia.com/', request_path)
        response = requests.request(
            method=GET,
            url=url,
            headers=headers,
            data=b'',
        )

        assert_vws_failure(
            response=response,
            status_code=codes.NOT_FOUND,
            result_code=ResultCodes.UNKNOWN_TARGET,
        )
