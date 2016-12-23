"""
Tools for using a fake implementation of Vuforia.
"""

import os
import re
from contextlib import ContextDecorator
from urllib.parse import urljoin

from typing import Optional  # noqa: F401 This is used in a type hint.
from typing import Pattern, Tuple, TypeVar

from requests_mock.mocker import Mocker
from requests_mock.response import _Context
from requests_mock.request import _RequestObjectProxy
from requests_mock import GET

from requests import codes


def _target_endpoint_pattern(path_pattern: str) -> Pattern[str]:
    """
    Given a path pattern, return a regex which will match URLs to
    patch for the Target API.

    Args:
        path_pattern: A part of the url which can be matched for endpoints.
            For example `https://vws.vuforia.com/<this-part>`. This is
            compiled to be a regular expression, so it may be `/foo` or
            `/foo/.+` for example.
    """
    base = 'https://vws.vuforia.com/'  # type: str
    joined = urljoin(base=base, url=path_pattern)
    return re.compile(joined)


class FakeVuforiaTargetAPI:  # pylint: disable=no-self-use
    """
    A fake implementation of the Vuforia Target API.

    This implementation is tied to the implementation of `requests_mock`.
    """

    DATABASE_SUMMARY_URL = _target_endpoint_pattern(path_pattern='summary')  # noqa type: Pattern[str]

    def __init__(self, access_key: str, secret_key: str) -> None:
        """
        Args:
            access_key: A VWS access key.
            secret_key: A VWS secret key.

        Attributes:
            access_key: A VWS access key.
            secret_key: A VWS secret key.
        """
        self.access_key = access_key  # type: str
        self.secret_key = secret_key  # type: str

    def database_summary(self,
                         request: _RequestObjectProxy,  # noqa: E501 pylint: disable=unused-argument
                         context: _Context) -> str:
        """
        Fake implementation of
        https://library.vuforia.com/articles/Solution/How-To-Get-a-Database-Summary-Report-Using-the-VWS-API  # noqa
        """
        context.status_code = codes.OK  # pylint: disable=no-member
        return '{}'


_MockVWSType = TypeVar('_MockVWSType', bound='MockVWS')  # noqa: E501 pylint: disable=invalid-name


class MockVWS(ContextDecorator):
    """
    Route requests to Vuforia's Web Service APIs to fakes of those APIs.

    This creates a mock which uses access keys from the environment.
    See the README to find which secrets to set.

    This can be used as a context manager or as a decorator.

    Examples:

        >>> @mock_vuforia
        ... def test_vuforia_example():
        ...     pass

        or

        >>> def test_vuforia_example():
        ...     with mock_vuforia():
        ...         pass
    """

    def __init__(self, real_http: bool=False) -> None:
        """
        Args:
            real_http: Whether or not to forward requests to the real server if
            they are not handled by the mock.
            See
            http://requests-mock.readthedocs.io/en/latest/mocker.html#real-http-requests  # noqa

        Attributes:
            real_http (bool): Whether or not to forward requests to the real
            server if they are not handled by the mock.
            See
            http://requests-mock.readthedocs.io/en/latest/mocker.html#real-http-requests  # noqa
            req: None or an `requests_mock` object used for mocking Vuforia.
        """
        super().__init__()
        self.real_http = real_http
        self.req = None  # type: Optional[Mocker]

    def __enter__(self: _MockVWSType) -> _MockVWSType:
        """
        Start an instance of a Vuforia mock with access keys set from
        environment variables.

        Returns:
            ``self``.
        """
        fake_target_api = FakeVuforiaTargetAPI(
            access_key=os.environ['VUFORIA_SERVER_ACCESS_KEY'],
            secret_key=os.environ['VUFORIA_SERVER_SECRET_KEY'],
        )
        with Mocker(real_http=self.real_http) as req:
            req.register_uri(
                method=GET,
                url=fake_target_api.DATABASE_SUMMARY_URL,
                text=fake_target_api.database_summary,
            )
        self.req = req
        self.req.start()
        return self

    def __exit__(self, *exc: Tuple[None, None, None]) -> bool:
        """
        Stop the Vuforia mock.

        Returns:
            False
        """
        self.req.stop()
        return False