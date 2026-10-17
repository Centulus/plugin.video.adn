"""Bundled pure-Python libraries, copied unmodified from their PyPI releases.

    rsa     4.9.1   Apache-2.0     rsa/LICENSE.txt
    pyasn1  0.6.4   BSD-2-Clause   pyasn1/LICENSE.rst   (dependency of rsa)
    pyaes   1.6.1   MIT            pyaes/LICENSE.txt

They import each other by absolute name, so this directory goes on sys.path.
"""
import os
import sys

_HERE = os.path.dirname(__file__)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import pyaes  # noqa: E402,F401
import rsa  # noqa: E402,F401
