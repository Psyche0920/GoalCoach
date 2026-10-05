"""Explicit provider configuration, pricing and CLI contracts."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from goalcoach.materials.__main__ import parser
from goalcoach.materials.agents import ModelSettings
from goalcoach.materials.models import GateError


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in ModelSettings.model_fields:
        monkeypatch.delenv(f"MATERIALS_{field.upper()}", raising=False)


def test_load_does_not_read_goalcoach_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GOALCOACH_LLM_API_KEY=unrelated\nMATERIALS_MODEL=hidden-model\n"
    )
    settings = ModelSettings.load()
    assert settings.model == ""
    assert settings.api_key.get_secret_value() == ""


def test_explicit_file_and_environment_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "model.env"
    path.write_text(
        "MATERIALS_MODEL=file-model\nMATERIALS_API_KEY=test-only\nMATERIALS_BASE_URL=https://example.org/v1\nMATERIALS_INPUT_USD_PER_MILLION=1.5\nMATERIALS_OUTPUT_USD_PER_MILLION=5\n"
    )
    monkeypatch.setenv("MATERIALS_MODEL", "environment-model")
    settings = ModelSettings.load(path)
    assert settings.model == "environment-model"
    assert settings.api_key.get_secret_value() == "test-only"
    assert str(settings.input_usd_per_million) == "1.5"


def test_missing_or_unknown_file_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "model.env"
    with pytest.raises(GateError, match="does not exist"):
        ModelSettings.load(path)
    path.write_text("MATERIALS_MODELL=typo\n")
    with pytest.raises(GateError, match="unknown"):
        ModelSettings.load(path)


def test_partial_pricing_is_rejected() -> None:
    with pytest.raises(ValidationError, match="both input and output"):
        ModelSettings(input_usd_per_million=1)


def test_cli_supports_batch_and_explicit_model_file() -> None:
    args = parser().parse_args(
        ["--settings-file", "model.env", "publish", "first-version", "second-version"]
    )
    assert args.settings_file == Path("model.env")
    assert args.versions == ["first-version", "second-version"]
