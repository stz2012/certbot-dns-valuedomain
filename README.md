# How to install

```sh
$ sudo pip install certbot-dns-valuedomain

...

$ certbot plugins

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
* dns-valuedomain
Description: Obtain certificates using a DNS TXT record (if you are using
value-domain API for DNS).
Interfaces: IAuthenticator, IPlugin
Entry point: EntryPoint(name='dns-valuedomain',
value='certbot_dns_valuedomain:Authenticator', group='certbot.plugins')

...

```


# How to use

```sh
$ cat << EOF | sudo tee /etc/letsencrypt/valuedomain.ini
dns_valuedomain_api_key = YOUR_VALUEDOMAIN_API_KEY
dns_valuedomain_root_domain = YOUR_ROOT_DOMAIN
EOF

...

$ sudo chmod 600 /etc/letsencrypt/valuedomain.ini

...

$ sudo certbot certonly --authenticator dns-valuedomain --domain example.com --domain *.example.com --preferred-challenges dns

...
```


# Options

```sh
$ certbot --help dns-valuedomain
usage:
  certbot [SUBCOMMAND] [options] [-d DOMAIN] [-d DOMAIN] ...

Certbot can obtain and install HTTPS/TLS/SSL certificates.  By default,
it will attempt to use a webserver both for obtaining and installing the
certificate.

options:
  -h, --help            show this help message and exit
  -c, --config CONFIG_FILE
                        path to config file (default: /etc/letsencrypt/cli.ini
                        and ~/.config/letsencrypt/cli.ini)

dns-valuedomain:
  Obtain certificates using a DNS TXT record (if you are using value-domain
  API for DNS).

  --dns-valuedomain-propagation-seconds DNS_VALUEDOMAIN_PROPAGATION_SECONDS
                        The number of seconds to wait for DNS to propagate
                        before asking the ACME server to verify the DNS
                        record. (default: 10)
  --dns-valuedomain-credentials PATH
                        Path to credentials INI file. (default:
                        /etc/letsencrypt/valuedomain.ini)
  --dns-valuedomain-max-propagation-seconds SECONDS
                        The number of maximum seconds to watch for DNS to
                        propagate before asking the ACME server to verify the
                        DNS record. (default: 1200)
```

# Links
 * https://certbot.eff.org/docs/using.html#certbot-command-line-options
 * https://github.com/certbot/certbot/tree/master/certbot-dns-sakuracloud
 * https://github.com/free2er/certbot-regru/
