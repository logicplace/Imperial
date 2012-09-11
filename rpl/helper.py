import codecs
from sys import stderr

# So I can be lazy about writing errors
def err(msg): stderr.write(unicode(msg) + "\n")

# TODO: Define some levels
logLevel = 0
def log(level, msg):
	global logLevel
	if level <= logLevel: print "LOG(%i): %s" % (debugLevel, unicode(msg))
#enddef

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

def oneOfIn(l1, l2):
	for x in l1:
		if x in l2: return True
	#endfor
	return False
#enddef

def list2english(l, conjunction=u"and"):
	l = map(unicode, l)
	if len(l) == 1: return l[0]
	elif len(l) == 2: return u"%s %s %s" % (l[0], conjunction, l[1])
	else: return u"%s, %s %s" % (", ".join(l[0:-1]), conjunction, l[-1])
#enddef
