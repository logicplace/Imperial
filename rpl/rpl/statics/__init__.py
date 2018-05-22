#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

""" lang=en_US
# statics #
Represent information declared in-line in the RPL structure
for internal use. These do not export and they accept any key
and accept all substructs that their parent accepts.

When a root or most other struct type iterates over its
children, it should descend into statics, ignoring the static
iteself, and yield the static's children in order.

The typing system for keys works as normal but they should
generally contain syntactic types only. When a Dynamic struct
references the contents of a static key, the data will be
cast by the Dynamic as appropriate for itself. In a sense,
as if one had copy-and-pasted the contents of the static key
into the position of the reference.

<!IMPORT base>
<!IMPORT static>
"""

from .base import *
from .static import *
