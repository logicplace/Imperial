#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
## Static ##
The static built-in type.
"""

from .base import BaseStatic
from ..exceptions import errors

__all__ = ["Static"]

class Static(BaseStatic):
	typename = "static"
#endclass