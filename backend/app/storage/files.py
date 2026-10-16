import re
import uuid
from pathlib import Path

from app.core.config import get_settings

# Diskteki ad yalnızca rastgele UUID + uzantıdır; orijinal dosya adı (kişisel veri) yalnızca DB'de.
_STORED_NAME = re.compile(r"^[0-9a-f]{32}\.(pdf|docx)$")


class FileStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save(self, data: bytes, extension: str) -> str:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}.{extension}"
        self.path_for(stored_name).write_bytes(data)
        return stored_name

    def path_for(self, stored_name: str) -> Path:
        # Ad DB'den gelir ama yine de doğrulanır: "../" ile UPLOAD_DIR dışına çıkılamasın.
        if not _STORED_NAME.fullmatch(stored_name):
            raise ValueError("Geçersiz dosya adı")
        return self.base_dir / stored_name

    def delete(self, stored_name: str) -> None:
        self.path_for(stored_name).unlink(missing_ok=True)


def get_storage() -> FileStorage:
    return FileStorage(get_settings().upload_dir)
