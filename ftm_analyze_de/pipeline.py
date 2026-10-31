"""
Analyze one entity: stock ftm-analyze (language detection, NER, patterns)
on text with repaired line breaks, then the German rules and the register
parser on top. `compat.apply` adjusts upstream before the first analysis.
"""

from followthemoney import model, registry
from followthemoney.proxy import EntityProxy
from ftm_analyze.logic import analyze_entity

from ftm_analyze_de import compat
from ftm_analyze_de.entities import drop_noisy_mentions, german_entities, register_entities
from ftm_analyze_de.extract import extract_german
from ftm_analyze_de.extract.register import is_register_page, parse_document
from ftm_analyze_de.normalize import repair_hyphenation
from ftm_analyze_de.settings import Settings

settings = Settings()
compat.apply(settings)

SKIP_RULES = ("Folder", "Package", "Table", "Workbook")
REGISTER_SCHEMATA = ("Pages", "Document")


def _prepare(entity: EntityProxy) -> EntityProxy:
    prepared = entity.clone()
    for prop in entity.schema.properties.values():
        if prop.type == registry.text and (values := entity.get(prop, quiet=True)):
            prepared.set(prop, [repair_hyphenation(v) for v in values], quiet=True)
    return prepared


def _is_german(base: EntityProxy | None, entity: EntityProxy) -> bool:
    languages = set()
    for source in (base, entity):
        if source is not None:
            languages.update(source.get("detectedLanguage", quiet=True))
            languages.update(source.get("language", quiet=True))
    if not languages:
        return settings.rules_without_language
    return bool(languages & settings.language_set)


def _parse_register(entity: EntityProxy, texts: list[str], forced: bool) -> list[EntityProxy]:
    if entity.schema.name not in REGISTER_SCHEMATA:
        return []
    if not forced and (settings.register_mode == "off" or not any(is_register_page(t) for t in texts)):
        return []
    register = parse_document(texts)
    if register.name or register.persons:
        return list(register_entities(entity.id, register))
    return []


def analyze_entity_de(
    entity: EntityProxy, overwrite_lang: bool = False, dataset: str | None = None
) -> tuple[list[EntityProxy], list[EntityProxy]]:
    """
    Returns the analysis results (stored with origin `analyze`) and the
    register entities (stored with their own origin, so a re-analysis
    replaces them as a whole).
    """
    prepared = _prepare(entity)
    results = drop_noisy_mentions(list(analyze_entity(prepared, overwrite_lang=overwrite_lang)))
    if not entity.schema.is_a("Analyzable") or entity.schema.name in SKIP_RULES:
        return results, []

    texts = [repair_hyphenation(t) for t in entity.get_type_values(registry.text)]
    base = next((r for r in results if r.id == entity.id), None)
    if _is_german(base, entity):
        findings = extract_german("\n".join(texts))
        if findings:
            if base is None:
                base = model.make_entity(entity.schema)
                base.id = entity.id
                results.append(base)
            results.extend(german_entities(base, findings))

    forced = dataset is not None and dataset in settings.register_dataset_set
    return results, _parse_register(entity, texts, forced)
