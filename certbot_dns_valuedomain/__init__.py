import time
import subprocess
import logging
import certbot.interfaces, certbot.errors, certbot.plugins.dns_common
import zope.interface
import requests

logger = logging.getLogger(__name__)

class ValueDomain(object):

    def __init__(self):
        self.session = requests.Session()
        self.api_key = None

    def login(self, api_key):
        """Store the API key retrieved from the INI configuration file."""
        self.api_key = api_key
        if not self.api_key:
            raise certbot.errors.PluginError('API key is not configured.')

    def logout(self):
        """No logout operation is required for the API-based authentication."""
        pass

    def get_dns_records(self, domain):
        """Retrieve the current DNS records (ns information) via Value Domain API."""
        url = f'https://api.value-domain.com/v1/domains/{domain}/dns'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            res_json = response.json()
            return res_json.get('ns', '')
        except requests.exceptions.RequestException as e:
            raise certbot.errors.PluginError(f'Failed to get DNS records from Value Domain API: {e}')

    def set_dns_records(self, domain, records):
        """Update and overwrite the DNS records via Value Domain API."""
        url = f'https://api.value-domain.com/v1/domains/{domain}/dns'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {'ns': records}
        
        try:
            response = self.session.put(url, headers=headers, json=data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise certbot.errors.PluginError(f'Failed to update DNS records via Value Domain API: {e}')


@zope.interface.implementer(certbot.interfaces.IAuthenticator)
@zope.interface.provider(certbot.interfaces.IPluginFactory)
class Authenticator(certbot.plugins.dns_common.DNSAuthenticator):
    """DNS Authenticator for value-domain using official API.
    """

    description = 'Obtain certificates using a DNS TXT record (if you are using value-domain API for DNS).'

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None
        self.api = ValueDomain()

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add)
        add('credentials',
            metavar='PATH',
            default='/etc/letsencrypt/valuedomain.ini',
            help='Path to credentials INI file.')
        add('max-propagation-seconds',
            type=int,
            metavar='SECONDS',
            default=3600,
            help='The number of maximum seconds to watch for DNS to propagate before asking the ACME server '
                 'to verify the DNS record.')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
                'value-domain API.'

    def _setup_credentials(self):  # pylint: disable=missing-docstring
        self.credentials = self._configure_credentials(
            'credentials',
            'value-domain credentials INI file',
            {
                'api_key': 'API Key for the value-domain account.',
            }
        )

        self.api.login(self.credentials.conf('api_key'))

    def _perform(self, domain, validation_name, validation):  # pylint: disable=missing-docstring
        records = self.api.get_dns_records(domain)
        self.api.set_dns_records(
            domain, records.strip() + '\n' + self._build_record_string(domain, validation_name, validation))

        t = time.time()
        while (time.time() - t) < self.conf('max-propagation-seconds'):

            if validation in subprocess.run(['nslookup', '-type=txt', validation_name], stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, universal_newlines=True).stdout:
                break

            time.sleep(self.conf('propagation-seconds'))

        else:
            raise certbot.errors.PluginError('max-propagation-seconds is exceeded.')

    def _cleanup(self, domain, validation_name, validation):  # pylint: disable=missing-docstring
        records = self.api.get_dns_records(domain).splitlines()
        record = self._build_record_string(domain, validation_name, validation)

        try:
            if record in records:
                records.remove(record)
            else:
                # Handle potential formatting or whitespace discrepancies
                records = [line for line in records if record.strip() not in line.strip()]
                
            self.api.set_dns_records(domain, '\n'.join(records))
        except LookupError:
            logger.exception('Failed to cleanup, validation record (%s) is not found.', record)

    def _build_record_string(self, domain, validation_name, validation):  # pylint: disable=missing-docstring
        assert validation_name.endswith('.' + domain)
        subdomain = validation_name[:-(1 + len(domain))]

        return 'txt %s %s' % (subdomain, validation)
