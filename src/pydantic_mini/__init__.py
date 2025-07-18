"""
===========================================================================================
Copyright (C) 2025 Nafiu Shaibu <nafiushaibu1@gmail.com>.
Purpose: Dataclass with validation
-------------------------------------------------------------------------------------------
This is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 3 of the License, or (at your option)
any later version.

This is distributed in the hopes that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

===========================================================================================
"""

__version__ = "1.1.0"

from .base import BaseModel
from .typing import Attrib, MiniAnnotated


__all__ = ["BaseModel", "Attrib", "MiniAnnotated"]
