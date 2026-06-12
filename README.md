# certbot-dns-valuedomain

[![CI](https://github.com/stz2012/certbot-dns-valuedomain/workflows/CI/badge.svg)](https://github.com/stz2012/certbot-dns-valuedomain/actions)
[![PyPI version](https://badge.fury.io/py/certbot-dns-valuedomain.svg)](https://badge.fury.io/py/certbot-dns-valuedomain)
[![Python Versions](https://img.shields.io/pypi/pyversions/certbot-dns-valuedomain.svg)](https://pypi.org/project/certbot-dns-valuedomain/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

ValueDomain DNS Authenticator plugin for Certbot.

This plugin automates the process of completing a `dns-01` challenge by creating, and subsequently removing, TXT records using the ValueDomain API.

[日本語ドキュメント](README_ja.md)

## Features

- ✅ Automatic DNS-01 challenge completion
- ✅ Support for wildcard certificates
- ✅ Automatic TXT record cleanup
- ✅ Retry logic with exponential backoff
- ✅ Rate limit handling
- ✅ Comprehensive error handling
- ✅ Secure credential management

## Installation

### From PyPI (Recommended)

```bash
pip install certbot-dns-valuedomain
```

### From Source

```bash
git clone https://github.com/stz2012/certbot-dns-valuedomain.git
cd certbot-dns-valuedomain
pip install -e .
```

## Prerequisites

- Python 3.6 or higher
- Certbot 1.1.0 or higher
- ValueDomain account with API access
- Domain managed by ValueDomain

## Configuration

### Named Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--dns-valuedomain-credentials` | ValueDomain credentials INI file (Required) | None |
| `--dns-valuedomain-propagation-seconds` | Seconds to wait for DNS propagation | 60 |

### Credentials File

Create a credentials file with your ValueDomain API information:

```ini
# ValueDomain API credentials
dns_valuedomain_api_key = your_api_key_here
dns_valuedomain_domain = example.com
```

The path to this file can be provided using the `--dns-valuedomain-credentials` command-line argument.

#### Security Best Practices

**Important:** Protect your credentials file with appropriate permissions:

```bash
chmod 600 /path/to/valuedomain.ini
```

Recommended location: `~/.secrets/certbot/valuedomain.ini`

## Usage Examples

### Obtain a Certificate

```bash
certbot certonly 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com
```

### Obtain a Wildcard Certificate

```bash
certbot certonly 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com 
  -d '*.example.com'
```

### Obtain a Certificate with Custom Propagation Time

If you experience DNS propagation issues, increase the wait time:

```bash
certbot certonly 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  --dns-valuedomain-propagation-seconds 120 
  -d example.com
```

### Renew Certificates

```bash
certbot renew 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini
```

### Automatic Renewal with Cron

Add to your crontab (`crontab -e`):

```cron
# Renew certificates daily at midnight
0 0 * * * certbot renew --authenticator dns-valuedomain --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini --quiet
```

Or use systemd timer (recommended for modern systems):

```bash
# Enable certbot timer
systemctl enable --now certbot-renew.timer
```

### Test Certificate Issuance (Dry Run)

```bash
certbot certonly --dry-run 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com
```

## Getting ValueDomain API Key

1. Log in to [ValueDomain](https://www.value-domain.com/)
2. Navigate to your account settings
3. Go to API settings section
4. Generate a new API key
5. Copy the API key to your credentials file
6. Ensure your domain is properly configured in ValueDomain

## Troubleshooting

### DNS Propagation Errors

If you encounter DNS propagation timeout errors:

```bash
# Increase propagation wait time
--dns-valuedomain-propagation-seconds 120
```

### API Authentication Errors

**Error:** `API authentication failed`

**Solutions:**
- Verify your API key is correct and active
- Check that the domain is managed by your ValueDomain account
- Ensure the credentials file has correct permissions (`chmod 600`)
- Verify the credentials file path is correct

### Permission Denied Errors

**Error:** `Permission denied` when reading credentials

**Solution:**
```bash
chmod 600 ~/.secrets/certbot/valuedomain.ini
```

### Rate Limit Errors

The plugin automatically handles rate limits with exponential backoff. If you consistently hit rate limits, consider:
- Reducing the frequency of certificate requests
- Contacting ValueDomain support to increase your API limits

### Debug Mode

For detailed error information, use the `--debug` flag:

```bash
certbot certonly --debug 
  --authenticator dns-valuedomain 
  --dns-valuedomain-credentials ~/.secrets/certbot/valuedomain.ini 
  -d example.com
```

### Common Issues

#### Issue: "Plugin not found"

```bash
# Reinstall the plugin
pip uninstall certbot-dns-valuedomain
pip install certbot-dns-valuedomain
```

#### Issue: "Invalid credentials format"

Ensure your credentials file follows this format:
```ini
dns_valuedomain_api_key = your_key
dns_valuedomain_domain = example.com
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/stz2012/certbot-dns-valuedomain.git
cd certbot-dns-valuedomain

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venvScriptsactivate

# Install development dependencies
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=certbot_dns_valuedomain --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
black certbot_dns_valuedomain tests

# Lint code
flake8 certbot_dns_valuedomain tests

# Type checking
mypy certbot_dns_valuedomain --ignore-missing-imports
```

### Running Tests Before Commit

```bash
# Run all checks
black certbot_dns_valuedomain tests && 
flake8 certbot_dns_valuedomain tests && 
pytest tests/ --cov=certbot_dns_valuedomain
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Contribution Guidelines

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/`)
6. Format your code (`black .`)
7. Commit your changes (`git commit -m 'Add some amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting
- Add type hints where applicable
- Write comprehensive docstrings
- Include unit tests for new features

## Security

### Reporting Security Issues

If you discover a security vulnerability, please email the maintainer directly instead of using the issue tracker.

### Security Best Practices

- Never commit credentials to version control
- Use strict file permissions (600) for credentials files
- Rotate API keys regularly
- Use environment-specific credentials
- Review logs for sensitive information leakage

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues:** [GitHub Issues](https://github.com/stz2012/certbot-dns-valuedomain/issues)
- **Documentation:** [GitHub Wiki](https://github.com/stz2012/certbot-dns-valuedomain/wiki)
- **Discussions:** [GitHub Discussions](https://github.com/stz2012/certbot-dns-valuedomain/discussions)

## Acknowledgments

- [Certbot](https://github.com/certbot/certbot) - The Let's Encrypt client
- [ValueDomain](https://www.value-domain.com/) - DNS provider
- All contributors to this project

## Related Projects

- [Certbot](https://github.com/certbot/certbot) - Official Certbot client
- [certbot-dns-cloudflare](https://github.com/certbot/certbot/tree/master/certbot-dns-cloudflare) - Cloudflare DNS plugin
- [certbot-dns-route53](https://github.com/certbot/certbot/tree/master/certbot-dns-route53) - Route53 DNS plugin

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each version.

## Roadmap

- [ ] Support for multiple domains in single credentials file
- [ ] Enhanced logging options
- [ ] Docker container support
- [ ] Integration tests with ValueDomain API sandbox
- [ ] Performance optimizations

## Author

**stz2012**

## Project Status

This project is actively maintained. Issues and pull requests are regularly reviewed.

---

**Note:** This plugin is not officially affiliated with ValueDomain or Let's Encrypt.