#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

""" lang=en_US
## serializeable ##
### serialize ###
### unserialize ###
"""

import os
from io import IOBase, BytesIO
from collections import OrderedDict

from ..exceptions import errors

__all__ = ["serialize", "unserialize"]

class FakeWritableStream(IOBase):
	def __init__(self):
		self.seeks = []
		self.sections = []
		self.seek_names = []
	#enddef

	def seekable(self): return True
	def readable(self): return False
	def writable(self): return True

	def seek(self, offset, whence=os.SEEK_CUR):
		if whence == os.SEEK_SET:
			abs_offset = offset
		elif whence == os.SEEK_CUR:
			abs_offset = self.seeks[-1] + len(self.sections[-1]) + offset
		elif whence == os.SEEK_END:
			if offset > 0:
				# Offset needs to become the new -1, update.
				for i, s in enumerate(self.seeks):
					if s < 0:
						self.seeks[i] = s - offset
					#endif
				#endfor
				abs_offset = -1
			else:
				abs_offset = offset - 1
			#endif
		#endif

		self.seek_names.append(len(self.seeks))
		self.seeks.append(abs_offset)
		self.sections.append(b'')
	#enddef

	def seek_name(self, name):
		# NOTE: Getting the base would be unnecessarily costly.
		self.seeks.append(None)
		self.seek_names.append(name)
		self.sections.append(b'')
		return self
	#enddef

	def write(self, b):
		self.sections[-1] += b
	#enddef

	def get(self):
		# TODO: Verify seek positions don't overlap or join/overwrite if so...?
		return OrderedDict(zip(self.seek_names, self.sections))
	#enddef
#endclass

class FakeReadableStream(IOBase):
	def __init__(self, bs):
		self.bytes = {k: BytesIO(v) for k, v in bs.items()}
		self.reading = None
	#enddef

	def seekable(self): return True
	def readable(self): return True
	def writable(self): return False

	def _error_before(self, method):
		if self.reading is None:
			raise OSError("{} before seek_name in FakeReadableStream".format(method))
		#endif
	#enddef

	def seek(self, offset, whence=os.SEEK_CUR):
		self._error_before("seek")
		if os.whence != os.SEEK_CUR:
			raise OSError("must seek from current position in FakeReadableStream")
		# TODO: Error if offset is past bounds?
		self.reading.seek(offset)
	#enddef

	def seek_name(self, name):
		if name in self.bytes:
			raise OSError("{} does not exist in FakeReadableStream".format(name))
		self.reading = self.bytes[name]
	#enddef

	def read(size=-1):
		self._error_before("read")
		return seek.reading.read(size)
	#enddef

	def readall():
		self._error_before("readall")
		return seek.reading.readall()
	#enddef

	def readinto(b):
		self._error_before("readinto")
		return seek.reading.readinto(b)
	#enddef
#endclass

def get_rebase(struct, stream):
	parent = struct.parent
	while parent is not None and not hasattr(parent, "rebase"):
		parent = parent.parent
	#endwhile

	try:
		rebase = parent.rebase
	except AttributeError:
		raise struct.error(errors.LibraryError,
			"attempt to call serialize(stream) on contextless struct")
	else:
		def rebaser(key):
			rebase(stream, struct, key)
			return stream
		#enddef
		return rebaser
	#endtry
#enddef

def serialize(fun):
	def handler(self, stream=None):
		if stream is None:
			stream = FakeWritableStream()
			fun.rebase = stream.seek_name
			fun(stream)

			ret = stream.get()
			lret = len(ret)
			if lret == 0:
				return b''
			if lret == 1 and list(ret.keys())[0] == "base":
				return ret["base"]
			return ret
		elif isinstance(stream, IOBase):
			fun.rebase = get_rebase(self, stream)
			fun(stream)
		else:
			raise self.error(errors.ArgumentsTypeError,
				"serialize expects a stream")
		#endif
	#enddef
	return handler
#enddef

def unserialize(fun):
	def handler(self, stream):
		if isinstance(stream, bytes):
			real_stream = BytesIO(stream)

			based = []
			def rebaser(key):
				if based:
					if based[0] != key:
						raise self.error(errors.LibraryError,
							"attempt to call unserialize(bytes), expected unserialize({'{}': bytes, '{}': bytes, ...})",
							based[0], key)
					#endif
				else:
					based.append(key)
				#endif

				real_stream.seek(0, os.SEEK_SET)
				return real_stream
			#enddef

			fun.rebase = rebaser
			fun(real_stream)
		elif isinstance(stream, dict):
			real_stream = FakeReadableStream(stream)
			fun.rebase = real_stream.seek_name
			fun(real_stream)
		elif isinstance(stream, IOBase):
			fun.rebase = get_rebase(self, stream)
			fun(stream)
		else:
			raise self.error(errors.ArgumentsTypeError,
				"unserialize expects a stream or bytes")
		#endif
	#enddef
	return handler
#enddef
