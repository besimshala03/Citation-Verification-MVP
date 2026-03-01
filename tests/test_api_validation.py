import pytest
from pydantic import ValidationError

from backend.config import settings
from backend.models.schemas import CreateProjectRequest


def test_project_name_empty_rejected():
    with pytest.raises(ValidationError):
        CreateProjectRequest(name="   ")


def test_project_name_too_long_rejected():
    with pytest.raises(ValidationError):
        CreateProjectRequest(name="x" * (settings.project_name_max_length + 1))
