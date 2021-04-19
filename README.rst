========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/pitchly/badge/?style=flat
    :target: https://pitchly.readthedocs.io/
    :alt: Documentation Status

.. |travis| image:: https://api.travis-ci.com/opunsoars/pitchly.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.com/github/opunsoars/pitchly

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/opunsoars/pitchly?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/opunsoars/pitchly

.. |requires| image:: https://requires.io/github/opunsoars/pitchly/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/opunsoars/pitchly/requirements/?branch=master

.. |codecov| image:: https://codecov.io/gh/opunsoars/pitchly/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/opunsoars/pitchly

.. |version| image:: https://img.shields.io/pypi/v/pitchly.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/pitchly

.. |wheel| image:: https://img.shields.io/pypi/wheel/pitchly.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/pitchly

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/pitchly.svg
    :alt: Supported versions
    :target: https://pypi.org/project/pitchly

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/pitchly.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/pitchly

.. |commits-since| image:: https://img.shields.io/github/commits-since/opunsoars/pitchly/v0.0.0.svg
    :alt: Commits since latest release
    :target: https://github.com/opunsoars/pitchly/compare/v0.0.0...master



.. end-badges

A python package that is a wrapper for Plotly to generate football tracking and event data plots

* Free software: MIT license

Installation
============
**Yet to be published. Stay tuned!**
::

    pip install pitchly

You can also install the in-development version with::

    pip install https://github.com/opunsoars/pitchly/archive/master.zip

``pitchly`` currently supports Metrica data formats. Other formats coming soon.

Documentation
=============


https://pitchly.readthedocs.io/


Development
===========

To run all the tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
