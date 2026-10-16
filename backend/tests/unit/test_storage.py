import re
from pathlib import Path

import pytest

from app.storage.files import FileStorage


def test_save_uses_random_uuid_name_and_delete_removes_file(tmp_path: Path) -> None:
    storage = FileStorage(tmp_path / "uploads")

    name = storage.save(b"%PDF-icerik", "pdf")

    assert re.fullmatch(r"[0-9a-f]{32}\.pdf", name)
    assert storage.path_for(name).read_bytes() == b"%PDF-icerik"
    storage.delete(name)
    assert not storage.path_for(name).exists()
    storage.delete(name)  # Zaten silinmiş dosya hata vermez.


@pytest.mark.parametrize("name", ["../secret.pdf", "cv.pdf", "a" * 32 + ".exe", ""])
def test_rejects_names_outside_pattern(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="Geçersiz dosya adı"):
        FileStorage(tmp_path).path_for(name)
