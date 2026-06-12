"""DNS Authenticator for ValueDomain."""

import logging
import time
import requests
from typing import Optional, Callable, List, Dict, Any

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
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "certbot-dns-valuedomain/1.0.0",
            }
        )

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

        # 新しいTXTレコードを作成
        # record_nameからドメイン部分を削除してホスト名のみにする
        host = record_name.replace(f".{self.domain}", "").replace(self.domain, "")
        if host == "":
            host = "@"

        new_record = {
            "type": "TXT",
            "name": host,
            "value": record_content,
            "ttl": record_ttl,
        }

        # 既存のレコードに追加（重複チェック）
        records = current_records.copy()
        # 同じTXTレコードが既にある場合は追加しない
        if not any(
            r.get("type") == "TXT"
            and r.get("name") == host
            and r.get("value") == record_content
            for r in records
        ):
            records.append(new_record)

        # DNSレコードを更新
        self._set_dns_records(records)

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

        # record_nameからドメイン部分を削除してホスト名のみにする
        host = record_name.replace(f".{self.domain}", "").replace(self.domain, "")
        if host == "":
            host = "@"

        # 該当するTXTレコードを削除
        updated_records = [
            record
            for record in current_records
            if not (
                record.get("type") == "TXT"
                and record.get("name") == host
                and record.get("value") == record_content
            )
        ]

        # DNSレコードを更新
        self._set_dns_records(updated_records)

        logger.info(f"Successfully deleted TXT record for {record_name}")

    def _get_dns_records(self) -> List[Dict[str, Any]]:
        """Get current DNS records.

        Returns:
            List of DNS records

        Raises:
            errors.PluginError: If API request fails
        """
        url = f"{self.API_BASE_URL}/domains/{self.domain}/dns"

        response = self._make_request("GET", url)

        try:
            data = response.json()
            # APIレスポンスの形式に応じて調整
            # 例: {"records": [...]} の場合
            if isinstance(data, dict) and "records" in data:
                return data["records"]
            # 例: [...] の場合
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"Unexpected API response format: {data}")
                return []
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise errors.PluginError(f"Invalid JSON response from API: {e}")

    def _set_dns_records(self, records: List[Dict[str, Any]]) -> None:
        """Set DNS records.

        Args:
            records: List of DNS records to set

        Raises:
            errors.PluginError: If API request fails
        """
        url = f"{self.API_BASE_URL}/domains/{self.domain}/dns"

        # APIに送信するデータ形式
        # ドキュメントに応じて調整が必要
        payload = {"records": records}

        self._make_request("PUT", url, json=payload)

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

                # ステータスコードチェック
                if response.status_code >= 400:
                    error_msg = f"API request failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict) and "message" in error_data:
                            error_msg += f": {error_data['message']}"
                        else:
                            error_msg += f": {error_data}"
                    except ValueError:
                        error_msg += f": {response.text}"

                    logger.error(error_msg)
                    raise errors.PluginError(error_msg)

                response.raise_for_status()

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
        sensitive_keys = ["apikey", "api_key", "password", "token", "authorization"]

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

            if "json" in safe_data and isinstance(safe_data["json"], dict):
                if key in safe_data["json"]:
                    safe_data["json"] = safe_data["json"].copy()
                    safe_data["json"][key] = "***MASKED***"

        return safe_data
