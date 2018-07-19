#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

class BaseWarning(Warning): pass

class DataLossWarning(BaseWarning): pass
class TruncationWarning(DataLossWarning): pass

class ExportedDuplicateData(BaseWarning): pass
class ImportedExtraData(BaseWarning): pass

class LibraryWarning(BaseWarning): pass
