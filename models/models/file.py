from typing import Optional
from pydantic import BaseModel

from models.base import SMBase
from cloudpathlib.anypath import AnyPath
import hashlib


class File(BaseModel):
    """File model for external use"""

    id: int
    analysis_id: int
    path: str
    basename: str
    dirname: str
    nameroot: str
    nameext: Optional[str]
    checksum: Optional[str]
    size: int

    def to_internal(self):
        """Convert to internal model"""
        return FileInternal(
            id=self.id,
            analysis_id=self.analysis_id,
            path=self.path,
            basename=self.basename,
            dirname=self.dirname,
            nameroot=self.nameroot,
            nameext=self.nameext,
            checksum=self.checksum,
            size=self.size,
        )


class FileInternal(SMBase):
    """File model for internal use"""

    id: int
    analysis_id: int
    path: str
    basename: str
    dirname: AnyPath
    nameroot: str
    nameext: str | None
    checksum: str | None
    size: int

    @staticmethod
    def get_basename(path: str) -> str:
        """Get file basename"""
        return AnyPath(path).name

    @staticmethod
    def get_dirname(path: str) -> str:
        """Get file dirname"""
        return str(AnyPath(path).parent)

    @staticmethod
    def get_nameroot(path: str) -> str:
        """Get file nameroot"""
        return AnyPath(path).stem

    @staticmethod
    def get_extension(path: str) -> str:
        """Get file extension"""
        return AnyPath(path).suffix

    @staticmethod
    def get_checksum(path: str) -> str:
        try:
            return hashlib.sha256(AnyPath(path).read_bytes()).hexdigest()
        except FileNotFoundError:
            return None

    @staticmethod
    def get_size(path: str) -> int:
        """Get file size"""
        try:
            return AnyPath(path).stat().st_size
        except FileNotFoundError:
            return 0

    def to_external(self):
        """Convert to external model"""
        return File(
            id=self.id,
            analysis_id=self.analysis_id,
            path=self.path,
            basename=self.basename,
            dirname=self.dirname,
            nameroot=self.nameroot,
            nameext=self.nameext,
            checksum=self.checksum,
            size=self.size,
        )
