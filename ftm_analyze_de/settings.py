from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings via environment variables prefixed with `FTM_ANALYZE_DE_`.
    Upstream `FTM_ANALYZE_*` settings (NER engine, spaCy models, …) still apply.
    """

    model_config = SettingsConfigDict(env_prefix="ftm_analyze_de_", extra="ignore")

    name_min_length: int = 3
    """Shortest NER name kept (upstream: 8, which drops `Bosch`, `Dresden`, `Merkel`)"""

    phone_region: str = "DE"
    """Country for phone numbers written without international prefix"""

    languages: str = "de,deu,ger"
    """Detected languages that enable the German rules (comma separated)"""

    rules_without_language: bool = True
    """Apply the German rules to texts without a detected language"""

    register_mode: Literal["auto", "off"] = "auto"
    """`auto`: parse register printouts recognised by their page header"""

    register_datasets: str = Field(
        default="", validation_alias=AliasChoices("ftm_analyze_de_register_datasets", "hr_analyze_datasets")
    )
    """Datasets whose documents are always parsed as register printouts (comma separated)"""

    @property
    def language_set(self) -> set[str]:
        return _split(self.languages)

    @property
    def register_dataset_set(self) -> set[str]:
        return _split(self.register_datasets)


def _split(value: str) -> set[str]:
    return {v.strip() for v in value.split(",") if v.strip()}
