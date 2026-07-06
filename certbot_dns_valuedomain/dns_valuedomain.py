"""DNS Authenticator for ValueDomain."""

import logging
import time
import requests
from typing import Optional, Callable, List, Dict, Any

import zope.interface

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

logger = logging.getLogger(__name__)

DEFAULT_PROPAGATION_SECONDS = 60
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
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
        add("credentials", help="ValueDomain credentials INI file.")

    def more_info(self) -> str:
        return "This plugin configures a DNS TXT record to respond to a dns-01 challenge using the ValueDomain API."

    def _setup_credentials(self) -> None:
        """Setup ValueDomain credentials."""
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

    API_BASE_URL = "https://api.value-domain.com/v1"

    def __init__(
        self,
        api_key: str,
        domain: str,
        timeout: int = DEFAULT_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ):
        self.api_key = api_key
        self.domain = domain
        self.timeout = timeout
        self.retry_count = retry_count
        # GET で取得した値を PUT 時に維持するため保持
        self._ns_type: Optional[int] = None
        self._ttl: Optional[int] = None
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
        """Add TXT record."""
        logger.info(f"Adding TXT record for {record_name}")

        current_records = self._get_dns_records()

        host = self._to_host(record_name)

        new_record = {
            "type": "txt",
            "name": host,
            "value": record_content,
        }

        records = current_records.copy()
        if not any(
            r.get("type") == "txt"
            and r.get("name") == host
            and r.get("value") == record_content
            for r in records
        ):
            records.append(new_record)

        self._set_dns_records(records)
        logger.info(f"Successfully added TXT record for {record_name}")

    def del_txt_record(self, record_name: str, record_content: str) -> None:
        """Delete TXT record."""
        logger.info(f"Deleting TXT record for {record_name}")

        current_records = self._get_dns_records()
        host = self._to_host(record_name)

        updated_records = [
            record
            for record in current_records
            if not (
                record.get("type") == "txt"
                and record.get("name") == host
                and record.get("value") == record_content
            )
        ]

        self._set_dns_records(updated_records)
        logger.info(f"Successfully deleted TXT record for {record_name}")

    def _to_host(self, record_name: str) -> str:
        """FQDN からホスト名部分のみを取り出す。"""
        host = record_name.replace(f".{self.domain}", "").replace(self.domain, "")
        if host == "":
            host = "@"
        return host

    def _get_dns_records(self) -> List[Dict[str, Any]]:
        """Get current DNS records.

        API は results.records を「改行区切りの文字列」で返す。
        """
        url = f"{self.API_BASE_URL}/domains/{self.domain}/dns"
        response = self._make_request("GET", url)

        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise errors.PluginError(f"Invalid JSON response from API: {e}")

        results = data.get("results", {}) if isinstance(data, dict) else {}

        # PUT 時に維持するため ns_type / ttl を保存
        self._ns_type = results.get("ns_type")
        self._ttl = results.get("ttl")

        records_str = results.get("records") or ""
        return self._parse_records(records_str)

    def _set_dns_records(self, records: List[Dict[str, Any]]) -> None:
        """Set DNS records.

        records は「改行区切りの文字列」に変換し、ns_type / ttl と共に送信する。
        """
        url = f"{self.API_BASE_URL}/domains/{self.domain}/dns"

        payload: Dict[str, Any] = {
            "records": self._format_records(records),
        }
        # GET で取得できていれば維持する
        if self._ns_type is not None:
            payload["ns_type"] = self._ns_type
        if self._ttl is not None:
            payload["ttl"] = self._ttl

        self._make_request("PUT", url, json=payload)

    @staticmethod
    def _parse_records(records_str: str) -> List[Dict[str, Any]]:
        """「種別 ホスト名 値」形式の文字列をパースする。"""
        records: List[Dict[str, Any]] = []
        for line in records_str.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 最大3分割: 種別 / ホスト名 / 値（値中の空白を保持）
            parts = line.split(None, 2)
            if len(parts) < 3:
                logger.debug(f"Skipping unrecognized record line: {line!r}")
                continue
            rtype, host, value = parts[0].lower(), parts[1], parts[2]
            records.append({"type": rtype, "name": host, "value": value})
        return records

    @staticmethod
    def _format_records(records: List[Dict[str, Any]]) -> str:
        """パース済みレコードを API 形式の文字列へ戻す。"""
        lines = []
        for r in records:
            lines.append(f"{r['type']} {r['name']} {r['value']}")
        return "\n".join(lines)

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
