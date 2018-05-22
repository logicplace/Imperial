#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

class BaseError(Exception): pass

class TypeError(BaseError): pass
class NonReferenceError(TypeError): pass

class ValueError(BaseError): pass
class UndefinedKey(BaseError): pass
class AssertionError(BaseError): pass
class NoBasicValue(BaseError): pass
class KeyRequired(BaseError): pass

class PackingError(BaseError): pass
class SerializationError(PackingError): pass
class EncodingError(SerializationError): pass
class DataLossError(SerializationError): pass


class LibraryError(BaseError): pass
class ArgumentsError(LibraryError): pass
class ArgumentsTypeError(ArgumentsError): pass
class MethodUnimplemented(LibraryError): pass
class DefineClonedError(LibraryError): pass
