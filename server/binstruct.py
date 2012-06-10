# binstruct - binary structure serialization
# code by Albert Zeyer, 2012-06-10
# code under BSD

# I wanted sth as simple as Python repr or JSON, but:
#  - binary data should only add constant overhead
#  - very simple format
#  - very very big data should be possible
#  - searching through the file should be fast
# Where the first 2 points were so important for me that
# I implemented this format.

# Some related formats and the reasons they weren't good
# enough for me.
# BSON:
#  - keys in structs are only C-strings. I want
#    any possible data here.
#  - already too complicated
# Bencode:
#  - too restricted, too less formats
# OGDL:
#  - too simple
# ...

# ------- This format. ------------

class FormatError(Exception): pass

# Bool. Byte \x00 or \x01.

def boolEncode(b): return "\x01" if b else "\x00"
def boolDecode(stream): return bool(ord(stream.read(1)))

# Integers. Use EliasGamma to decode the byte size
# of the signed integer. I.e. we start with EliasGamma,
# then align that to the next byte and the signed integer
# in big endian follows.

from array import array
from StringIO import StringIO

def bitsOf(n):
	assert n >= 0
	return n.bit_length()

def bitListToInt(l):
	i = 0
	bitM = 1
	for bit in reversed(l):
		i += bitM * int(bit)
		bitM <<= 1
	return i

def bitListToBin(l):
	bin = array("B", (0,)) * (len(l) / 8)
	for i in range(0, len(l), 8):
		byte = bitListToInt(l[i:i+8])
		bin[i/8] = byte
	return bin

def eliasGammaEncode(n):
	assert n > 0
	bitLen = bitsOf(n)
	binData = [False] * (bitLen - 1) # prefix
	bit = 2 ** (bitLen - 1)
	while bit > 0:
		binData += [bool(n & bit)]
		bit >>= 1
	binData += [False] * (-len(binData) % 8) # align by 8
	return bitListToBin(binData)

def eliasGammaDecode(stream):
	def readBits():
		while True:
			byte = ord(stream.read(1))
			bitM = 2 ** 7
			while bitM > 0:
				yield bool(byte & bitM)
				bitM >>= 1
	num = 0
	state = 0
	bitM = 1
	for b in readBits():
		if state == 0:
			if not b:
				bitM <<= 1
				continue
			state = 1
		num += bitM * int(b)
		bitM >>= 1
		if bitM == 0: break
	return num

def intToBin(x):
	bitLen = x.bit_length() if (x >= 0) else (x+1).bit_length() # two-complement
	bitLen += 1 # for the sign
	byteLen = (bitLen+7) / 8
	bin = array("B", (0,)) * byteLen
	if x < 0:
		x += 256 ** byteLen
		assert x > 0
	for i in range(byteLen):
		bin[byteLen-i-1] = (x >> (i * 8)) & 255
	return bin

def binToInt(bin):
	if isinstance(bin, str): bin = array("B", bin)
	n = 0
	byteLen = len(bin)
	for i in range(byteLen):
		n += bin[byteLen-i-1] << (i * 8)
	if n >= 2**(byteLen*8 - 1):
		n -= 256 ** byteLen
	return n

def intEncode(x):
	bin = intToBin(x)
	assert len(bin) > 0
	gammaBin = eliasGammaEncode(len(bin))
	return gammaBin + bin

def intDecode(stream):
	if isinstance(stream, array): stream = stream.tostring()
	if isinstance(stream, str): stream = StringIO(stream)
	binLen = eliasGammaDecode(stream)
	return binToInt(stream.read(binLen))

# Float numbers. Let's keep things simple but let's
# also cover a lot of cases.
# I use x = (numerator/denominator) * 2^exponent,
# where num/denom/exp are all integers.
# The binary representation just uses the Integer repr.
# If denom=0, with num>0 we get +inf, num=0 we get NaN,
# with num<0 we get -inf.

def floatEncode(x):
	import math
	from fractions import Fraction
	from decimal import Decimal
	if math.isnan(x): return intEncode(0) * 3
	if math.isinf(x): return intEncode(math.copysign(1, x)) + intEncode(0) * 2
	if isinstance(x, Decimal):
		sign,digits,base10e = x.as_tuple()
		e = 0
		num = digits
		denom = 10 ** -base10e
	elif isinstance(x, Fraction):
		e,num,denom = 0, x.numerator, x.denominator
	else:
		m,e = math.frexp(x)
		num,denom = m.as_integer_ratio()
	return intEncode(num) + intEncode(denom) + intEncode(e)

def floatDecode(stream):
	if isinstance(stream, array): stream = stream.tostring()
	if isinstance(stream, str): stream = StringIO(stream)
	num,denom,e = intDecode(stream),intDecode(stream),intDecode(stream)
	return (float(num)/denom) * (2 ** e)

# Strings. Just size + string.

def strEncode(s):
	if isinstance(s, str): s = array("B", s)
	if isinstance(s, unicode): s = array("B", s.encode("utf-8"))
	return intEncode(len(s)) + s

def strDecode(stream):
	strLen = intDecode(stream)
	return stream.read(strLen)

# Lists. Amounts of items, each item as variant.

def listEncode(l):
	pass


def listDecode(stream):
	pass

# Dicts. Amounts of items, each item as 2 variants (key+value).

def dictEncode(d):
	pass

def dictDecode(d):
	pass

# Variants. Bytesize + type-ID-byte + data.
# Type-IDs:
#  1: list
#  2: dict
#  3: bool
#  4: int
#  5: float
#  6: str
# None has no type-ID. It is just bytesize=0.

def prefixWithSize(data):
	return intEncode(len(data)) + data
	
def varEncode(v):
	from numbers import Integral, Real
	if v is None: return intEncode(0)
	if isinstance(v, bool):
		return prefixWithSize(array("B", (3,)) + boolEncode(v))
	if isinstance(v, Integral):
		return prefixWithSize(array("B", (4,)) + intEncode(v))
	if isinstance(v, Real):
		return prefixWithSize(array("B", (5,)) + floatEncode(v))
	if isinstance(v, (str,unicode,array)):
		return prefixWithSize(array("B", (6,)) + strEncode(v))
	if isinstance(v, list):
		data = listEncode(v)
		typeEncoded = array("B", (1,))
		lenEncoded = intEncode(len(data) + 1)
		return lenEncoded + typeEncoded + data
	if isinstance(v, dict):
		data = dictEncode(v)
		typeEncoded = array("B", (2,))
		lenEncoded = intEncode(len(data) + 1)
		return lenEncoded + typeEncoded + data
	assert False

def varDecode(stream):
	varLen = intDecode(stream)
	if varLen < 0: raise FormatError("varLen < 0")
	if varLen == 0: return None
	type = ord(stream.read(1))
	if type == 1: return listDecode(stream)
	if type == 2: return dictDecode(stream)
	if type == 3: return boolDecode(stream)
	if type == 4: return intDecode(stream)
	if type == 5: return floatDecode(stream)
	if type == 6: return strDecode(stream)
	raise FormatError("type %i unknown" % type)

	