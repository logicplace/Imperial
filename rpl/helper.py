import codecs

def readFrom(etc):
	"""
	Helper class to read from a file or stream
	"""
	if type(etc) in [str, unicode]:
		x = codecs.open(etc, encoding="utf-8", mode="r")
		ret = x.read()
		x.close()
		return ret
	else: return etc.read()
#enddef

def writeTo(etc, data):
	"""
	Helper class to write to a file or stream
	"""
	if type(etc) in [str, unicode]:
		x = codecs.open(etc, encoding="utf-8", mode="w")
		ret = x.write(data)
		x.close()
		return ret
	else: return etc.write(data)
#enddef

def stream(etc):
	"""
	Helper class to open a file as a stream
	"""
	if type(etc) in [str, unicode]:
		try: etc = open(etc, "r+b")
		except IOError: etc = open(etc, "a+b")
	#endif
	return etc
#enddef
