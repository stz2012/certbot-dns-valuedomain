from setuptools import setup, find_packages
import os

# バージョン情報を読み込む
here = os.path.abspath(os.path.dirname(__file__))
about = {}
with open(os.path.join(here, 'certbot_dns_valuedomain', '_version.py'), encoding='utf-8') as f:
    exec(f.read(), about)

# READMEを読み込む
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='certbot-dns-valuedomain',
    version=about['__version__'],  # ← _version.pyから取得
    description="ValueDomain DNS Authenticator plugin for Certbot",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/chrono-meter/certbot-dns-valuedomain',
    author='chrono-meter / stz2012',
    author_email='chrono-meter@gmx.net',
    license='Apache License 2.0',
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'certbot>=1.1.0',
        'requests>=2.20.0',
        'setuptools>=41.6.0',
    ],
    entry_points={
        'certbot.plugins': [
            'dns-valuedomain = certbot_dns_valuedomain.dns_valuedomain:Authenticator',
        ],
    },
)