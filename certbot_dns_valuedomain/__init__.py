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
        self.root_domain = None
        self.ns_type = 'valuedomain1'
        self.ttl = '1200'

    def login(self, api_key, root_domain):
        self.api_key = api_key
        self.root_domain = root_domain
        if not self.api_key or not self.root_domain:
            raise certbot.errors.PluginError('API key or Root Domain is not configured.')

    def get_dns_records(self):
        url = f'https://api.value-domain.com/v1/domains/{self.root_domain}/dns'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        try:
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            res_json = response.json()
            
            results = res_json.get('results', {})
            self.ns_type = results.get('ns_type', 'valuedomain1')
            self.ttl = results.get('ttl', '1200')
            
            return results.get('records', '')
        except requests.exceptions.RequestException as e:
            raise certbot.errors.PluginError(f'Failed to get DNS records from Value Domain API: {e}')

    def set_dns_records(self, records):
        url = f'https://api.value-domain.com/v1/domains/{self.root_domain}/dns'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'ns_type': self.ns_type,
            'records': records,
            'ttl': self.ttl
        }
        try:
            response = self.session.put(url, headers=headers, json=data)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise certbot.errors.PluginError(f'Failed to update DNS records via Value Domain API: {e}')


@zope.interface.implementer(certbot.interfaces.IAuthenticator)
@zope.interface.provider(certbot.interfaces.IPluginFactory)
class Authenticator(certbot.plugins.dns_common.DNSAuthenticator):

    description = 'Obtain certificates using a DNS TXT record (if you are using value-domain API for DNS).'

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None
        self.api = ValueDomain()

    @classmethod
    def add_parser_arguments(cls, add):
        super(Authenticator, cls).add_parser_arguments(add)
        add('credentials',
            metavar='PATH',
            default='/etc/letsencrypt/valuedomain.ini',
            help='Path to credentials INI file.')
        add('max-propagation-seconds',
            type=int,
            metavar='SECONDS',
            default=120,
            help='The number of maximum seconds to watch for DNS to propagate before asking the ACME server '
                 'to verify the DNS record.')

    def more_info(self):
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using value-domain API.'

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'value-domain credentials INI file',
            {
                'api_key': 'API Key for the value-domain account.',
                'root_domain': 'Your registered root domain in Value Domain.'
            }
        )
        self.api.login(self.credentials.conf('api_key'), self.credentials.conf('root_domain'))

    def _perform(self, domain, validation_name, validation):
        records = self.api.get_dns_records()

        record_line = f'txt {validation_name} {validation}'

        self.api.set_dns_records(records.strip() + '\n' + record_line)

        logger.info("Waiting for DNS records to propagate to Value Domain nameservers...")
        time.sleep(self.conf('max-propagation-seconds'))

    def _cleanup(self, domain, validation_name, validation):
        records = self.api.get_dns_records().splitlines()
        record = f'txt {validation_name} {validation}'

        try:
            if record in records:
                records.remove(record)
            else:
                records = [line for line in records if record.strip() not in line.strip()]

            self.api.set_dns_records('\n'.join(records))
        except LookupError:
            logger.exception('Failed to cleanup, validation record (%s) is not found.', record)
