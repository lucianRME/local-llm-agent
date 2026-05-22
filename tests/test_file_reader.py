import pytest

from local_llm_agent.tools.file_reader import LocalFileReader


def test_reads_txt_files(tmp_path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "notes.txt").write_text("Plain text notes", encoding="utf-8")

    documents = LocalFileReader(documents_dir).load_documents()

    assert len(documents) == 1
    assert documents[0].name == "notes.txt"
    assert documents[0].content == "Plain text notes"


def test_reads_md_files(tmp_path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "guide.md").write_text("# Guide\nMarkdown notes", encoding="utf-8")

    documents = LocalFileReader(documents_dir).load_documents()

    assert len(documents) == 1
    assert documents[0].name == "guide.md"
    assert documents[0].content == "# Guide\nMarkdown notes"


def test_ignores_unsupported_files(tmp_path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "notes.txt").write_text("Keep this", encoding="utf-8")
    (documents_dir / "data.pdf").write_text("Ignore this", encoding="utf-8")
    (documents_dir / "image.png").write_text("Ignore this too", encoding="utf-8")

    documents = LocalFileReader(documents_dir).load_documents()

    assert [document.name for document in documents] == ["notes.txt"]


def test_handles_missing_directory(tmp_path):
    documents_dir = tmp_path / "missing"

    documents = LocalFileReader(documents_dir).load_documents()

    assert documents == []


def test_blocks_path_traversal(tmp_path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (tmp_path / "secret.txt").write_text("Do not read", encoding="utf-8")

    reader = LocalFileReader(documents_dir)

    with pytest.raises(ValueError, match="inside the documents directory"):
        reader.read_document("../secret.txt")


def test_read_document_rejects_unsupported_file(tmp_path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "data.json").write_text("{}", encoding="utf-8")

    reader = LocalFileReader(documents_dir)

    with pytest.raises(ValueError, match="Unsupported document type"):
        reader.read_document("data.json")


def test_load_documents_skips_unsafe_symlinks(tmp_path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (tmp_path / "secret.txt").write_text("Do not read", encoding="utf-8")
    (documents_dir / "secret.txt").symlink_to(tmp_path / "secret.txt")

    documents = LocalFileReader(documents_dir).load_documents()

    assert documents == []
