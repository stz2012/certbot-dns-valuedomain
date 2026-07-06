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
            valuedomain_credentials=path, valuedomain_propagation_seconds=0
        )
        self.auth = Authenticator(self.config, "valuedomain")

        self.mock_client = mock.MagicMock()
        self.auth._get_valuedomain_client = mock.MagicMock(
            return_value=self.mock_client
        )

    @mock.patch("certbot.plugins.dns_common.DNSAuthenticator._setup_credentials")
    def test_perform(self, mock_setup):
        with mock.patch("certbot.display.util.notify"):
            self.auth.perform([self.achall])

        expected = [
            mock.call.add_txt_record("_acme-challenge." + DOMAIN, mock.ANY, mock.ANY)
        ]
        self.assertEqual(expected, self.mock_client.mock_calls)

    @mock.patch("certbot.plugins.dns_common.DNSAuthenticator._setup_credentials")
    def test_cleanup(self, mock_setup):
        self.auth._attempt_cleanup = True

        with mock.patch("certbot.display.util.notify"):
            self.auth.cleanup([self.achall])

        expected = [mock.call.del_txt_record("_acme-challenge." + DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)


class ValueDomainClientTest(unittest.TestCase):
    def setUp(self):
        from certbot_dns_valuedomain.dns_valuedomain import ValueDomainClient

        self.client = ValueDomainClient(API_KEY, DOMAIN_NAME, timeout=10, retry_count=3)

    def _make_get_response(self, records_str, ns_type=1, ttl=3600):
        """results 形式の GET レスポンスを生成する。"""
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "results": {
                "domainname": DOMAIN_NAME,
                "ns_type": ns_type,
                "records": records_str,
                "ttl": ttl,
            }
        }
        return resp

    @mock.patch("requests.Session.request")
    def test_add_txt_record(self, mock_request):
        # GETレスポンス（既存のレコード：改行区切り文字列）
        mock_get_response = self._make_get_response("a @ 192.0.2.1")

        # PUTレスポンス（更新成功）
        mock_put_response = mock.MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {"message": "success"}

        mock_request.side_effect = [mock_get_response, mock_put_response]

        self.client.add_txt_record("_acme-challenge.example.com", "test-validation", 60)

        self.assertEqual(2, mock_request.call_count)
        # GET
        self.assertEqual("GET", mock_request.call_args_list[0][0][0])
        # PUT
        self.assertEqual("PUT", mock_request.call_args_list[1][0][0])

        # PUT のボディを検証（records は文字列で、ns_type / ttl が維持される）
        put_kwargs = mock_request.call_args_list[1][1]
        payload = put_kwargs["json"]
        self.assertIn("records", payload)
        self.assertIsInstance(payload["records"], str)
        # 既存の A レコードと新規 TXT レコードが含まれること
        self.assertIn("a @ 192.0.2.1", payload["records"])
        self.assertIn("txt _acme-challenge test-validation", payload["records"])
        # GET で取得した ns_type / ttl が維持されること
        self.assertEqual(1, payload["ns_type"])
        self.assertEqual(3600, payload["ttl"])

    @mock.patch("requests.Session.request")
    def test_del_txt_record(self, mock_request):
        # GETレスポンス（TXTレコードを含む）
        mock_get_response = self._make_get_response(
            "a @ 192.0.2.1\ntxt _acme-challenge test-validation"
        )

        # PUTレスポンス（削除成功）
        mock_put_response = mock.MagicMock()
        mock_put_response.status_code = 200
        mock_put_response.json.return_value = {"message": "success"}

        mock_request.side_effect = [mock_get_response, mock_put_response]

        self.client.del_txt_record("_acme-challenge.example.com", "test-validation")

        self.assertEqual(2, mock_request.call_count)

        # PUT のボディを検証（TXT レコードが削除されていること）
        put_kwargs = mock_request.call_args_list[1][1]
        payload = put_kwargs["json"]
        self.assertIn("a @ 192.0.2.1", payload["records"])
        self.assertNotIn("txt _acme-challenge test-validation", payload["records"])

    @mock.patch("requests.Session.request")
    def test_api_error(self, mock_request):
        mock_request.side_effect = requests.RequestException("Connection error")

        with self.assertRaises(errors.PluginError):
            self.client._make_request("GET", "http://test.example.com")

    @mock.patch("time.sleep", return_value=None)
    @mock.patch("requests.Session.request")
    def test_rate_limit(self, mock_request, mock_sleep):
        mock_response_429 = mock.MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        mock_response_200 = mock.MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"results": {"records": ""}}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        response = self.client._make_request("GET", "http://test.example.com")

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, mock_request.call_count)
        mock_sleep.assert_called_once_with(1)

    def test_mask_sensitive_data(self):
        data = {
            "authorization": "Bearer secret123",
            "domain": "example.com",
            "json": {"api_key": "secret456"},
        }

        masked = self.client._mask_sensitive_data(data)

        self.assertEqual("***MASKED***", masked["authorization"])
        self.assertEqual("example.com", masked["domain"])
        self.assertEqual("***MASKED***", masked["json"]["api_key"])

    @mock.patch("requests.Session.request")
    def test_get_dns_records_empty(self, mock_request):
        mock_request.return_value = self._make_get_response("")

        records = self.client._get_dns_records()

        self.assertEqual([], records)

    @mock.patch("requests.Session.request")
    def test_get_dns_records_multiple(self, mock_request):
        mock_request.return_value = self._make_get_response(
            "a @ 192.0.2.1\ntxt test validation"
        )

        records = self.client._get_dns_records()

        self.assertEqual(2, len(records))
        self.assertEqual("a", records[0]["type"])
        self.assertEqual("@", records[0]["name"])
        self.assertEqual("192.0.2.1", records[0]["value"])
        self.assertEqual("txt", records[1]["type"])
        self.assertEqual("test", records[1]["name"])
        self.assertEqual("validation", records[1]["value"])

    # --- パース / フォーマットの単体テストを追加 ---

    def test_parse_records(self):
        records_str = "a @ 192.0.2.1\ntxt _acme-challenge hello world\n\n# comment"
        records = self.client._parse_records(records_str)

        self.assertEqual(2, len(records))
        self.assertEqual(
            {"type": "a", "name": "@", "value": "192.0.2.1"}, records[0]
        )
        # 値に空白が含まれる場合も保持されること
        self.assertEqual(
            {"type": "txt", "name": "_acme-challenge", "value": "hello world"},
            records[1],
        )

    def test_format_records(self):
        records = [
            {"type": "a", "name": "@", "value": "192.0.2.1"},
            {"type": "txt", "name": "_acme-challenge", "value": "validation"},
        ]
        formatted = self.client._format_records(records)

        self.assertEqual(
            "a @ 192.0.2.1\ntxt _acme-challenge validation", formatted
        )

    def test_to_host(self):
        self.assertEqual(
            "_acme-challenge",
            self.client._to_host("_acme-challenge.example.com"),
        )
        self.assertEqual("@", self.client._to_host("example.com"))
        self.assertEqual("www", self.client._to_host("www.example.com"))


if __name__ == "__main__":
    unittest.main()
