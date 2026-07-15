import pytest
from app.infrastructure.storage.local_storage_provider import LocalStorageProvider


def test_save_load_exists_and_delete_file(tmp_path):
    provider = LocalStorageProvider(tmp_path)

    provider.save_file("clips/first.bin", b"highlight")

    assert provider.exists("clips/first.bin")
    assert provider.load_file("clips/first.bin") == b"highlight"

    provider.delete_file("clips/first.bin")

    assert not provider.exists("clips/first.bin")


def test_list_files_returns_sorted_root_relative_paths(tmp_path):
    provider = LocalStorageProvider(tmp_path)
    provider.save_file("clips/zeta.bin", b"zeta")
    provider.save_file("clips/alpha.bin", b"alpha")

    assert provider.list_files("clips") == ["clips/alpha.bin", "clips/zeta.bin"]


def test_storage_rejects_paths_outside_configured_root(tmp_path):
    provider = LocalStorageProvider(tmp_path)

    with pytest.raises(ValueError):
        provider.save_file("../outside.bin", b"unsafe")
