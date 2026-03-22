from __future__ import annotations

import pytest

from ankicli.app.errors import CollectionRequiredError
from ankicli.app.services import DoctorService
from ankicli.backends.python_anki import PythonAnkiBackend


@pytest.mark.unit
def test_doctor_env_report_has_expected_keys() -> None:
    report = DoctorService().env_report()

    assert "python_version" in report
    assert "platform" in report
    assert "anki_import_available" in report


@pytest.mark.unit
def test_python_anki_backend_reports_capabilities() -> None:
    capabilities = PythonAnkiBackend().backend_capabilities()

    assert capabilities.backend == "python-anki"
    assert capabilities.supports_live_desktop is False


@pytest.mark.unit
def test_collection_info_requires_collection_path() -> None:
    from ankicli.app.services import CollectionService

    with pytest.raises(CollectionRequiredError):
        CollectionService(PythonAnkiBackend()).info(None)

