"""
Tests for giving invalid JSON to endpoints.
"""

from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytest
import pytz
import requests
from freezegun import freeze_time
from requests import codes

from mock_vws._constants import ResultCodes
from tests.mock_vws.utils import (
    TargetAPIEndpoint,
    assert_json_separators,
    assert_valid_date_header,
    assert_valid_transaction_id,
    assert_vws_failure,
    assert_vwq_failure,
    authorization_header,
    rfc_1123_date,
)


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestInvalidJSON:
    """
    Tests for giving invalid JSON to endpoints.
    """

    @pytest.mark.parametrize('date_skew_minutes', [0, 10])
    def test_invalid_json(
        self,
        endpoint: TargetAPIEndpoint,
        date_skew_minutes: int,
    ) -> None:
        """
        Giving invalid JSON to endpoints returns error responses.
        """
        date_is_skewed = not date_skew_minutes == 0
        # This is an undocumented difference between `/summary` and other
        # endpoints.
        is_summary_endpoint = endpoint.prepared_request.path_url == '/summary'
        content = b'a'
        gmt = pytz.timezone('GMT')
        now = datetime.now(tz=gmt)
        time_to_freeze = now + timedelta(minutes=date_skew_minutes)
        with freeze_time(time_to_freeze):
            date = rfc_1123_date()

        endpoint_headers = dict(endpoint.prepared_request.headers)
        authorization_string = authorization_header(
            access_key=endpoint.access_key,
            secret_key=endpoint.secret_key,
            method=str(endpoint.prepared_request.method),
            content=content,
            content_type=endpoint.auth_header_content_type,
            date=date,
            request_path=endpoint.prepared_request.path_url,
        )

        headers = {
            **endpoint_headers,
            'Authorization': authorization_string,
            'Date': date,
        }

        endpoint.prepared_request.prepare_body(  # type: ignore
            data=content,
            files=None,
        )

        endpoint.prepared_request.prepare_headers(  # type: ignore
            headers=headers,
        )
        endpoint.prepared_request.prepare_content_length(  # type: ignore
            body=content,
        )
        session = requests.Session()
        response = session.send(  # type: ignore
            request=endpoint.prepared_request,
        )

        takes_json_data = (
            endpoint.auth_header_content_type == 'application/json'
        )

        if date_is_skewed and takes_json_data:
            # On the real implementation, we get `codes.FORBIDDEN` and
            # `REQUEST_TIME_TOO_SKEWED`.
            # See https://github.com/adamtheturtle/vws-python/issues/407 for
            # implementing this on them mock.
            return

        if not date_is_skewed and takes_json_data:
            assert_vws_failure(
                response=response,
                status_code=codes.BAD_REQUEST,
                result_code=ResultCodes.FAIL,
            )
            return

        if date_is_skewed and is_summary_endpoint:
            assert_vws_failure(
                response=response,
                status_code=codes.FORBIDDEN,
                result_code=ResultCodes.REQUEST_TIME_TOO_SKEWED,
            )
            return

        if not date_is_skewed and is_summary_endpoint:
            assert_vws_failure(
                response=response,
                status_code=codes.UNAUTHORIZED,
                result_code=ResultCodes.AUTHENTICATION_FAILURE,
            )
            return

        assert response.status_code == codes.BAD_REQUEST
        netloc = urlparse(endpoint.prepared_request.url).netloc
        if netloc == 'cloudreco.vuforia.com':
            assert_vwq_failure(
                response=response,
                status_code=codes.BAD_REQUEST,
                content_type='text/html',
            )
            expected_text = (
                'java.lang.RuntimeException: RESTEASY007500: '
                'Could find no Content-Disposition header within part'
            )
            assert response.text == expected_text
            return

        assert response.text == ''
        assert 'Content-Type' not in response.headers
