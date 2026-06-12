"""DNS Authenticator for ValueDomain."""

import logging
import time
import requests
from typing import Optional, Callable

from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

logger = logging.getLogger(__name__)

DEFAULT_PROPAGATION_SECONDS = 60
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for ValueDomain

    This Authenticator uses the ValueDomain API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using ValueDomain for DNS)."
    ttl = 60

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials: Optional[CredentialsConfiguration] = None
        self._client: Optional[ValueDomainClient] = None

    @classmethod
    def add_parser_arguments(
        cls,
        add: Callable,
        default_propagation_seconds: int = DEFAULT_PROPAGATION_SECONDS,
    ) -> None:
        super(Authenticator, cls).add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="ValueDomain credentials INI file.", default=None)
        add(
            "propagation-seconds",
            help=f"The number of seconds to wait for DNS to propagate before asking the ACME server to verify the DNS record. (default: {default_propagation_seconds})",
            default=default_propagation_seconds,
            type=int,
        )

    def more_info(self) -> str:
        return "This plugin configures a DNS TXT record to respond to a dns-01 challenge using the ValueDomain API."

    def _setup_credentials(self) -> None:
        """Setup ValueDomain credentials."""
        credentials_path = self.conf("credentials")
        if not credentials_path:
            raise errors.PluginError("--dns-valuedomain-credentials is required")

        self.credentials = self._configure_credentials(
            "credentials",
            "ValueDomain credentials INI file",
            {
                "api_key": "API key for ValueDomain account",
                "domain": "Domain name managed by ValueDomain",
            },
        )

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        """Add TXT record using the ValueDomain API."""
        self._get_valuedomain_client().add_txt_record(
            validation_name, validation, self.ttl
        )

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        """Delete TXT record using the ValueDomain API."""
        try:
            self._get_valuedomain_client().del_txt_record(validation_name, validation)
        except Exception as e:
            logger.warning(f"Failed to cleanup TXT record: {e}")

    def _get_valuedomain_client(self) -> "ValueDomainClient":
        """Get or create ValueDomain API client."""
        if not self._client:
            # credentials が None でないことを確認
            if not self.credentials:
                raise errors.PluginError("Credentials not configured")

            api_key = self.credentials.conf("api_key")
            domain = self.credentials.conf("domain")

            if not api_key:
                raise errors.PluginError("API key is required")
            if not domain:
                raise errors.PluginError("Domain is required")

            self._client = ValueDomainClient(
                api_key=api_key,
                domain=domain,
                timeout=DEFAULT_TIMEOUT,
                retry_count=DEFAULT_RETRY_COUNT,
            )
        return self._client


class ValueDomainClient:
    """Client for ValueDomain API"""

    API_BASE_URL = "https://api.value-domain.com"

    def __init__(
        self,
        api_key: str,
        domain: str,
        timeout: int = DEFAULT_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ):
        """Initialize ValueDomain API client.

        Args:
            api_key: ValueDomain API key
            domain: Domain name to manage
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        self.api_key = api_key
        self.domain = domain
        self.timeout = timeout
        self.retry_count = retry_count
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"certbot-dns-valuedomain/1.0.0"})

    def add_txt_record(
        self, record_name: str, record_content: str, record_ttl: int = 60
    ) -> None:
        """Add TXT record.

        Args:
            record_name: DNS record name
            record_content: TXT record content
            record_ttl: TTL value

        Raises:
            errors.PluginError: If API request fails
        """
        logger.info(f"Adding TXT record for {record_name}")

        # 既存のDNSレコードを取得
        current_records = self._get_dns_records()

        # 新しいTXTレコードを追加
        txt_record = f"txt {record_name} {record_content} {record_ttl}"
        updated_records = current_records + [txt_record]

        # DNSレコードを更新
        self._set_dns_records(updated_records)

        logger.info(f"Successfully added TXT record for {record_name}")

    def del_txt_record(self, record_name: str, record_content: str) -> None:
        """Delete TXT record.

        Args:
            record_name: DNS record name
            record_content: TXT record content to delete

        Raises:
            errors.PluginError: If API request fails
        """
        logger.info(f"Deleting TXT record for {record_name}")

        # 既存のDNSレコードを取得
        current_records = self._get_dns_records()

        # 該当するTXTレコードを削除
        updated_records = [
            record
            for record in current_records
            if not (
                record.startswith("txt")
                and record_name in record
                and record_content in record
            )
        ]

        # DNSレコードを更新
        self._set_dns_records(updated_records)

        logger.info(f"Successfully deleted TXT record for {record_name}")

    def _get_dns_records(self) -> list:
        """Get current DNS records.

        Returns:
            List of DNS records

        Raises:
            errors.PluginError: If API request fails
        """
        url = f"{self.API_BASE_URL}/v1/getdns"
        params = {"domain": self.domain, "apikey": self.api_key}

        response = self._make_request("GET", url, params=params)

        # レスポンスからDNSレコードを解析
        dns_data = response.text.strip()
        if not dns_data:
            return []

        return [line.strip() for line in dns_data.split("\n") if line.strip()]

    def _set_dns_records(self, records: list) -> None:
        """Set DNS records.

        Args:
            records: List of DNS records to set

        Raises:
            errors.PluginError: If API request fails
        """
        url = f"{self.API_BASE_URL}/v1/setdns"
        data = {
            "domain": self.domain,
            "apikey": self.api_key,
            "record": "\n".join(records),
        }

        self._make_request("POST", url, data=data)

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            errors.PluginError: If all retries fail
        """
        kwargs.setdefault("timeout", self.timeout)

        for attempt in range(self.retry_count):
            try:
                # APIキーをログに出力しないようマスク
                safe_kwargs = self._mask_sensitive_data(kwargs)
                logger.debug(
                    f"API Request (attempt {attempt + 1}): {method} {url} {safe_kwargs}"
                )

                response = self.session.request(method, url, **kwargs)

                # レート制限チェック
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                # ValueDomain APIのエラーチェック
                if "error" in response.text.lower():
                    raise errors.PluginError(f"ValueDomain API error: {response.text}")

                return response

            except requests.RequestException as e:
                if attempt == self.retry_count - 1:
                    raise errors.PluginError(
                        f"API request failed after {self.retry_count} attempts: {e}"
                    )

                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"Request failed (attempt {attempt + 1}): {e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

        raise errors.PluginError(
            f"API request failed after {self.retry_count} attempts"
        )

    @staticmethod
    def _mask_sensitive_data(data: dict) -> dict:
        """Mask sensitive information for logging.

        Args:
            data: Dictionary that may contain sensitive data

        Returns:
            Dictionary with masked sensitive data
        """
        safe_data = data.copy()

        # マスクするキーのリスト
        sensitive_keys = ["apikey", "api_key", "password", "token"]

        for key in sensitive_keys:
            if key in safe_data:
                safe_data[key] = "***MASKED***"

            # paramsやdataの中もチェック
            if "params" in safe_data and isinstance(safe_data["params"], dict):
                if key in safe_data["params"]:
                    safe_data["params"] = safe_data["params"].copy()
                    safe_data["params"][key] = "***MASKED***"

            if "data" in safe_data and isinstance(safe_data["data"], dict):
                if key in safe_data["data"]:
                    safe_data["data"] = safe_data["data"].copy()
                    safe_data["data"][key] = "***MASKED***"

        return safe_data
