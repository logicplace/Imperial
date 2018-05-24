#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

class BaseWarning(Warning): pass

class DataLossWarning(BaseWarning): pass
class TruncationWarning(DataLossWarning): pass

class ExportedDuplicateData(BaseWarning): pass
class ImportedExtraData(BaseWarning): pass

class LibraryWarning(BaseWarning): pass
