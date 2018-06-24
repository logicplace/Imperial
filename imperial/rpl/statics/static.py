#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

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
