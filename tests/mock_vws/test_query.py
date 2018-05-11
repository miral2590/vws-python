"""
Tests for the mock of the query endpoint.

https://library.vuforia.com/articles/Solution/How-To-Perform-an-Image-Recognition-Query.
"""

import io
from urllib.parse import urljoin

import pytest
import requests
from requests_mock import POST
from urllib3.filepost import encode_multipart_formdata

from tests.mock_vws.utils import (
    TargetAPIEndpoint,
    VuforiaDatabaseKeys,
    assert_query_success,
    authorization_header,
    rfc_1123_date,
)


@pytest.mark.usefixtures('verify_mock_vuforia')
class TestQuery:
    """
    Tests for the query endpoint.
    """

    def test_no_results(
        self,
        query_endpoint: TargetAPIEndpoint,
    ) -> None:
        """
        When there are no matching images in the database, an empty list of
        results is returned.
        """
        session = requests.Session()
        response = session.send(  # type: ignore
            request=query_endpoint.prepared_request,
        )
        assert_query_success(response=response)
        assert response.json()['results'] == []
