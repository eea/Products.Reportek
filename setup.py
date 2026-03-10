import os
from os.path import join

from setuptools import find_packages, setup

NAME = "Products.Reportek"
PATH = NAME.split(".") + ["version.txt"]
VERSION = open(join(*PATH)).read().strip()
setup(
    name=NAME,
    version=VERSION,
    description="Products Reportek",
    long_description_content_type="text/x-rst",
    long_description=(
        open("README.rst").read()
        + "\n"
        + open(os.path.join("docs", "changelog.rst")).read()
    ),
    author="European Environment Agency: DIS1 P-Team",
    author_email="eea-edw-c-team-alerts@googlegroups.com",
    url="https://github.com/eea/Products.Reportek",
    packages=find_packages(),
    include_package_data=True,
    license="MPL",
    zip_safe=False,
    install_requires=[
        "Products.PluggableAuthService",
        "Zope2",
        "collective.monkeypatcher",
        "lxml",
        "plone.caching",
        "plone.cachepurging",
        "plone.keyring",
        "plone.memoize",
        "requests",
        "xlwt",
        "clamd",
        "zipstream",
        "xmltodict==0.11.0",
        "pika>=1.3",
        "contextlib2",
        "Beaker",
        "redis",
    ],
    entry_points="""
    # -*- Entry points: -*-
    [console_scripts]
    zip_cache_cleanup = Products.Reportek.RepUtils:cleanup_zip_cache
    automatic_qa = Products.Reportek.scripts.automatic_qa:main
    auto_fallin = Products.Reportek.scripts.auto_fallin:main
    auto_cleanup = Products.Reportek.scripts.auto_cleanup:main
    auto_env_cleanup = Products.Reportek.scripts.auto_env_cleanup:main

    [zodbupdate]
    renames = Products.Reportek.zodbupdate_renames:RENAMES

    [paste.filter_app_factory]
    beaker_session = Products.Reportek.session:beaker_session_filter_factory
    """,
)
