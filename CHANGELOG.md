# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-06-12

### Added
- DNS-01 challenge support for ValueDomain
- API key authentication with ValueDomain API
- Automatic TXT record creation for ACME challenges
- Automatic TXT record cleanup after validation
- Retry logic with exponential backoff (up to 3 attempts)
- HTTP 429 rate limit handling with automatic retry
- Comprehensive error handling and validation
- Sensitive data masking in logs (API keys, passwords)
- Configurable DNS propagation wait time
- Configurable request timeout
- Unit tests with pytest
- Code coverage reporting
- CI/CD pipeline with GitHub Actions
- Automated testing for Python 3.9-3.12
- Code quality checks (Black, Flake8, MyPy)
- Comprehensive documentation in English
- Comprehensive documentation in Japanese
- Example credentials file
- Installation instructions for PyPI and source
- Usage examples for common scenarios
- Troubleshooting guide
- Security best practices documentation

### Security
- Credential masking in all log outputs
- Secure credential file handling recommendations
- File permission validation (600 recommended)
- API key protection in HTTP requests
- No credentials stored in code or version control

### Documentation
- README.md with full English documentation
- README_ja.md with full Japanese documentation
- CHANGELOG.md for version tracking
- valuedomain.ini.example for credential setup
- Inline code documentation and docstrings
- Type hints for better code clarity
- Contributing guidelines
- Security reporting guidelines

### Development
- Development environment setup instructions
- pytest test suite with mocking
- Code coverage configuration
- Black code formatter configuration
- Flake8 linter configuration
- MyPy type checker configuration
- GitHub Actions CI workflow
- Automated package building and validation

### Infrastructure
- PyPI package configuration
- setuptools-based packaging
- Entry point configuration for Certbot
- Python 3.6+ compatibility
- Cross-platform support (Linux, macOS, Windows)

## [1.1.0] - 2026-06-08

### Changed
- Official API v1 Integration
- Dynamic Root Domain Routing
- Robust Propagation Delay

## [1.0.0] - 2019-03-30

### Added
- Initial release of certbot-dns-valuedomain

---

## Release Notes

### Version 1.2.0

This is the first stable release of certbot-dns-valuedomain. It provides a production-ready plugin for Certbot to automate DNS-01 challenges using ValueDomain's DNS service.

#### Key Features:
- ✅ Full DNS-01 challenge automation
- ✅ Wildcard certificate support
- ✅ Robust error handling
- ✅ Production-ready security
- ✅ Comprehensive testing
- ✅ Bilingual documentation

#### Breaking Changes:
None (initial release)

#### Migration Guide:
Not applicable (initial release)

#### Known Issues:
- None at this time

#### Upgrade Instructions:
```bash
pip install --upgrade certbot-dns-valuedomain
```

#### Compatibility:
- Python: 3.9, 3.10, 3.11, 3.12
- Certbot: >= 1.1.0
- OS: Linux, macOS, Windows

#### Contributors:
- chrono-meter - Initial development
- stz2012 - development and maintenance

---

## Version History Summary

| Version | Release Date | Status | Major Changes |
|---------|--------------|--------|---------------|
| 1.2.0 | 2026-06-12 | Stable | Refactor: CI/CD pipeline with GitHub Actions |
| 1.1.0 | 2026-06-08 | Stable | Refactor: Official DNS API Support |
| 1.0.0 | 2019-03-30 | Stable | Initial stable release |

---

## Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

---

## How to Report Issues

If you encounter any issues or have suggestions for improvements:

1. Check the [existing issues](https://github.com/chrono-meter/certbot-dns-valuedomain/issues)
2. If not found, [create a new issue](https://github.com/chrono-meter/certbot-dns-valuedomain/issues/new)
3. Include:
   - Plugin version (`pip show certbot-dns-valuedomain`)
   - Python version (`python --version`)
   - Certbot version (`certbot --version`)
   - Operating system
   - Error messages and logs
   - Steps to reproduce

---

## Links

- [GitHub Repository](https://github.com/chrono-meter/certbot-dns-valuedomain)
- [Issue Tracker](https://github.com/chrono-meter/certbot-dns-valuedomain/issues)
- [PyPI Package](https://pypi.org/project/certbot-dns-valuedomain/)
- [Documentation](https://github.com/chrono-meter/certbot-dns-valuedomain/wiki)
