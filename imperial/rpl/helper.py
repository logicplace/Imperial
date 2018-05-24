#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

import itertools
from collections import OrderedDict

class mixed(dict):
	def __init__(self, *args, **kwargs):
		dict.__init__(self, itertools.chain(enumerate(args), kwargs.items()))
	#enddef

	def __entries(self, argform, keyform):
		ret = []
		extra = []

		i = 0
		while i in self:
			ret.append(repr(self[i]))
			i += 1
		#endwhile

		for k, v in self.items():
			if isinstance(k, int):
				if k < i: continue
			#endif
			
			if isinstance(k, str) and k.isidentifier():
				lst = ret
				form = argform
			else:
				k = repr(k)
				lst = extra
				form = keyform
			#endif

			lst.append(form.format(k, repr(v)))
		#endfor

		return ret, extra
	#enddef

	def __str__(self):
		args, keys = self.__entries("{} = {}", "{}: {}")
		if keys: args.append("**{" + ", ".join(keys) + "}")
		return "{}({})".format(self.__class__.__name__, ", ".join(args))
	#enddef

	def __repr__(self):
		args, keys = self.__entries("{}={}", "{}:{}")
		if keys: args.append("**{" + ",".join(keys) + "}")
		return "{}({})".format(self.__class__.__qualname__, ",".join(args))
	#enddef
#endclass

class OrderedMixed(OrderedDict, mixed):
	def __init__(self, *args):
		OrderedDict.__init__(self, [])

		i = 0
		for arg in args:
			if isinstance(arg, tuple):
				larg = len(arg)
				if larg == 2:
					key, value = arg
					self[key] = value
					continue
				elif larg > 2:
					raise TypeError("OrderedMixed requires entries of value or (key, value)")
				#endif
				arg = arg[0]
			#endif
			self[i] = arg
			i += 1
		#endfor
		self.keyless_length = i
	#enddef

	def append(self, *args):
		i = self.keyless_length
		for arg in args:
			self[i] = arg
			i += 1
		#endfor
		self.keyless_length = i
	#enddef

	def pop(self, *args):
		if args:
			return OrderedDict.pop(args[0])
		#endif

		self.keyless_length -= 1
		ret = OrderedDict.pop(self.keyless_length)
	#enddef

	def keyless(self):
		for i in range(self.keyless_length):
			yield self[i]
		#endfor
	#enddef
#endclass

class frozendict(dict):
	def __init__(self, base, update=None):
		new_base = {}
		new_base.update(base)
		if update: new_base.update(update)
		return dict.__init__(self, new_base)
	#enddef

	# https://www.python.org/dev/peps/pep-0351/
	def _immutable(self, *args, **kwargs):
		raise TypeError("{} is immutable".format(self.__class__.__qualname__))
	#enddef

	__setitem__ = _immutable
	__delitem__ = _immutable
	clear       = _immutable
	update      = _immutable
	setdefault  = _immutable
	pop         = _immutable
	popitem     = _immutable
#endclass
