"""Tests for certbot_dns_valuedomain.dns_valuedomain"""
import unittest
from unittest import mock
import requests

from certbot import errors
from certbot.compat import os
from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN
from certbot.tests import util as test_util

API_KEY = 'test_api_key'
DOMAIN_NAME = 'example.com'


class AuthenticatorTest(test_util.TempDirTestCase, dns_test_common.BaseAuthenticatorTest):

    def setUp(self):
        super(AuthenticatorTest, self).setUp()

        from certbot_dns_valuedomain.dns_valuedomain import Authenticator

        path = os.path.join(self.tempdir, 'valuedomain.ini')
        dns_test_common.write(
            {"valuedomain_api_key": API_KEY, "valuedomain_domain": DOMAIN_NAME},
            path
        )

        self.config = mock.MagicMock(valuedomain_credentials=path,
                                     valuedomain_propagation_seconds=0)
        self.auth = Authenticator(self.config, "valuedomain")

        self.mock_client = mock.MagicMock()
        self.auth._get_valuedomain_client = mock.MagicMock(return_value=self.mock_client)

    def test_perform(self):
        self.auth.perform([self.achall])

        expected = [mock.call.add_txt_record('_acme-challenge.' + DOMAIN, mock.ANY, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)

    def test_cleanup(self):
        self.auth._attempt_cleanup = True
        self.auth.cleanup([self.achall])

        expected = [mock.call.del_txt_record('_acme-challenge.' + DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)


class ValueDomainClientTest(unittest.TestCase):

    def setUp(self):
        from certbot_dns_valuedomain.dns_valuedomain import ValueDomainClient

        self.client = ValueDomainClient(API_KEY, DOMAIN_NAME, timeout=10, retry_count=1)

    @mock.patch('requests.Session.request')
    def test_add_txt_record(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "a @ 192.0.2.1 300"
        mock_request.return_value = mock_response

        self.client.add_txt_record('_acme-challenge.example.com', 'test-validation', 60)

        self.assertEqual(2, mock_request.call_count)

    @mock.patch('requests.Session.request')
    def test_del_txt_record(self, mock_request):
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "txt _acme-challenge.example.com test-validation 60"
        mock_request.return_value = mock_response

        self.client.del_txt_record('_acme-challenge.example.com', 'test-validation')

        self.assertEqual(2, mock_request.call_count)

    @mock.patch('requests.Session.request')
    def test_api_error(self, mock_request):
        mock_request.side_effect = requests.RequestException("Connection error")

        with self.assertRaises(errors.PluginError):
            self.client._make_request('GET', 'http://test.example.com')

    @mock.patch('requests.Session.request')
    def test_rate_limit(self, mock_request):
        mock_response_429 = mock.MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '1'}
        
        mock_response_200 = mock.MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = "success"
        
        mock_request.side_effect = [mock_response_429, mock_response_200]

        response = self.client._make_request('GET', 'http://test.example.com')
        self.assertEqual(200, response.status_code)

    def test_mask_sensitive_data(self):
        data = {
            'apikey': 'secret123',
            'domain': 'example.com',
            'params': {'apikey': 'secret456'}
        }
        
        masked = self.client._mask_sensitive_data(data)
        
        self.assertEqual('***MASKED***', masked['apikey'])
        self.assertEqual('example.com', masked['domain'])
        self.assertEqual('***MASKED***', masked['params']['apikey'])


if __name__ == "__main__":
    unittest.main()
