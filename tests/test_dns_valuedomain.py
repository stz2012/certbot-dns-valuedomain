"""Tests for certbot_dns_valuedomain.dns_valuedomain"""

import unittest
from unittest import mock
import requests

from certbot import errors
from certbot.compat import os
from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN
from certbot.tests import util as test_util

API_KEY = "test_api_key"
DOMAIN_NAME = "example.com"


class AuthenticatorTest(
    test_util.TempDirTestCase, dns_test_common.BaseAuthenticatorTest
):

    def setUp(self):
        super(AuthenticatorTest, self).setUp()

        from certbot_dns_valuedomain.dns_valuedomain import Authenticator

        path = os.path.join(self.tempdir, "valuedomain.ini")
        dns_test_common.write(
            {"valuedomain_api_key": API_KEY, "valuedomain_domain": DOMAIN_NAME}, path
        )

        self.config = mock.MagicMock(
            valuedomain_credentials=path,
            valuedomain_propagation_seconds=0,  # テスト用に0秒に設定
        )
        self.auth = Authenticator(self.config, "valuedomain")

        self.mock_client = mock.MagicMock()
        self.auth._get_valuedomain_client = mock.MagicMock(
            return_value=self.mock_client
        )

    @mock.patch("certbot.plugins.dns_common.DNSAuthenticator._setup_credentials")
    def test_perform(self, mock_setup):
        # display utilityのモック
        with mock.patch("certbot.display.util.notify"):
            self.auth.perform([self.achall])

        expected = [
            mock.call.add_txt_record("_acme-challenge." + DOMAIN, mock.ANY, mock.ANY)
        ]
        self.assertEqual(expected, self.mock_client.mock_calls)

    @mock.patch("certbot.plugins.dns_common.DNSAuthenticator._setup_credentials")
    def test_cleanup(self, mock_setup):
        self.auth._attempt_cleanup = True

        # display utilityのモック
        with mock.patch("certbot.display.util.notify"):
            self.auth.cleanup([self.achall])

        expected = [mock.call.del_txt_record("_acme-challenge." + DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)


class ValueDomainClientTest(unittest.TestCase):

    def setUp(self):
        from certbot_dns_valuedomain.dns_valuedomain import ValueDomainClient

        self.client = ValueDomainClient(API_KEY, DOMAIN_NAME, timeout=10, retry_count=3)

    @mock.patch("requests.Session.request")
    def test_add_txt_record(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "a @ 192.0.2.1 300"
        mock_request.return_value = mock_response

        self.client.add_txt_record("_acme-challenge.example.com", "test-validation", 60)

        self.assertEqual(2, mock_request.call_count)

    @mock.patch("requests.Session.request")
    def test_del_txt_record(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "txt _acme-challenge.example.com test-validation 60"
        mock_request.return_value = mock_response

        self.client.del_txt_record("_acme-challenge.example.com", "test-validation")

        self.assertEqual(2, mock_request.call_count)

    @mock.patch("requests.Session.request")
    def test_api_error(self, mock_request):
        mock_request.side_effect = requests.RequestException("Connection error")

        with self.assertRaises(errors.PluginError):
            self.client._make_request("GET", "http://test.example.com")

    @mock.patch("time.sleep", return_value=None)  # sleep をスキップ
    @mock.patch("requests.Session.request")
    def test_rate_limit(self, mock_request, mock_sleep):
        # 429レスポンスの作成
        mock_response_429 = mock.MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        # 200レスポンスの作成
        mock_response_200 = mock.MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = "success"

        # 最初は429、次は200を返す
        mock_request.side_effect = [mock_response_429, mock_response_200]

        # リクエスト実行
        response = self.client._make_request("GET", "http://test.example.com")

        # 検証
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, mock_request.call_count)
        mock_sleep.assert_called_once_with(1)

    def test_mask_sensitive_data(self):
        data = {
            "apikey": "secret123",
            "domain": "example.com",
            "params": {"apikey": "secret456"},
        }

        masked = self.client._mask_sensitive_data(data)

        self.assertEqual("***MASKED***", masked["apikey"])
        self.assertEqual("example.com", masked["domain"])
        self.assertEqual("***MASKED***", masked["params"]["apikey"])

    @mock.patch("requests.Session.request")
    def test_get_dns_records_empty(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_request.return_value = mock_response

        records = self.client._get_dns_records()

        self.assertEqual([], records)

    @mock.patch("requests.Session.request")
    def test_get_dns_records_multiple(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "a @ 192.0.2.1 300\ntxt test validation 60"
        mock_request.return_value = mock_response

        records = self.client._get_dns_records()

        self.assertEqual(2, len(records))
        self.assertIn("a @ 192.0.2.1 300", records)
        self.assertIn("txt test validation 60", records)

    @mock.patch("time.sleep", return_value=None)
    @mock.patch("requests.Session.request")
    def test_retry_on_connection_error(self, mock_request, mock_sleep):
        # 最初の2回は失敗、3回目は成功
        mock_request.side_effect = [
            requests.ConnectionError("Connection failed"),
            requests.ConnectionError("Connection failed"),
            mock.MagicMock(status_code=200, text="success"),
        ]

        response = self.client._make_request("GET", "http://test.example.com")

        self.assertEqual(200, response.status_code)
        self.assertEqual(3, mock_request.call_count)
        # Exponential backoff: 2^0=1, 2^1=2
        self.assertEqual(2, mock_sleep.call_count)

    @mock.patch("requests.Session.request")
    def test_api_error_response(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Error: Invalid API key"
        mock_request.return_value = mock_response

        with self.assertRaises(errors.PluginError) as ctx:
            self.client._make_request("GET", "http://test.example.com")

        self.assertIn("ValueDomain API error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
