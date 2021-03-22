# Copyright (c) 2020 Leiden University Medical Center
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from typing import Optional

try:
    from . import _isal
    ISAL_MAJOR_VERSION: Optional[int] = _isal.ISAL_MAJOR_VERSION
    ISAL_MINOR_VERSION: Optional[int] = _isal.ISAL_MINOR_VERSION
    ISAL_PATCH_VERSION: Optional[int] = _isal.ISAL_PATCH_VERSION
    ISAL_VERSION: Optional[str] = _isal.ISAL_VERSION
except ImportError:  # isa-l.h not available on windows
    ISAL_MAJOR_VERSION = None
    ISAL_MINOR_VERSION = None
    ISAL_PATCH_VERSION = None
    ISAL_VERSION = None

__all__ = [
    "ISAL_MAJOR_VERSION",
    "ISAL_MINOR_VERSION",
    "ISAL_PATCH_VERSION",
    "ISAL_VERSION",
    "__version__"
]

__version__ = "0.8.0"
