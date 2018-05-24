#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
## iterator ##
### ChildrenIterartor ###

"""

__all__ = ["ChildrenIterartor"]

class ChildrenIterartor:
	def __init__(self, children):
		self.parents = []
		self.current = children
	#enddef

	def __iter__(self):
		return self
	#enddef

	def __next__(self):
		try:
			child = next(self.current)
		except StopIteration:
			try:
				self.current = self.parents.pop()
			except IndexError:
				raise StopIteration
			else:
				return next(self)
			#endtry
		#endtry

		if isinstance(child, BaseStatic):
			self.parents.append(self.current)
			self.current = child.children()
			return next(self)
		#endif

		return child
	#enddef
#endclass
