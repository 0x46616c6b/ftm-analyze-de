"""Turn German findings and parsed register data into FollowTheMoney entities."""

from collections.abc import Iterable

from followthemoney import model
from followthemoney.proxy import EntityProxy
from followthemoney.util import make_entity_id
from rigour.names import normalize_name

from ftm_analyze_de.extract import Findings
from ftm_analyze_de.extract.orgs import is_plausible_name
from ftm_analyze_de.extract.register import Register
from ftm_analyze_de.normalize import fold

ANALYZABLE = model["Analyzable"]
TAG_PERSON = ANALYZABLE.properties["peopleMentioned"]
TAG_COMPANY = ANALYZABLE.properties["companiesMentioned"]
TAG_LOCATION = ANALYZABLE.properties["locationMentioned"]

# Seed of organization/person ids. Kept from the first version (`hr_analyze`)
# so entities already stored by it are merged, not duplicated.
ID_PREFIX = "hr-analyze"


def organization_id(court: str | None, number: str) -> str:
    """One entity per register entry, wherever it is found."""
    return make_entity_id(ID_PREFIX, "org", court, number)


def register_entities(document_id: str, reg: Register) -> Iterable[EntityProxy]:
    """Yield organization, persons and directorships of one register printout."""
    org = model.make_entity("Company" if reg.is_company else "Organization")
    org.id = organization_id(reg.court, reg.number or document_id)
    if reg.name:
        org.add("name", reg.name)
        org.add("registrationNumber", reg.number)
        org.add("jurisdiction", "de")
        org.add("country", "de")
        org.add("address", reg.address or reg.seat)
        org.add("notes", f"Registergericht: {reg.court}" if reg.court else None)
        org.add("proof", document_id)
        if reg.is_company:
            org.add("capital", reg.capital)
        yield org

    for person in reg.persons:
        entity = model.make_entity("Person")
        entity.id = entity.make_id(ID_PREFIX, "person", person.last_name, person.first_name, person.birth_date)
        entity.add("name", f"{person.first_name} {person.last_name}")
        entity.add("firstName", person.first_name)
        entity.add("lastName", person.last_name)
        entity.add("birthDate", person.birth_date)
        entity.add("address", person.city)
        entity.add("country", "de")
        entity.add("proof", document_id)
        yield entity

        if not reg.name:
            continue
        link = model.make_entity("Directorship")
        link.id = link.make_id(ID_PREFIX, "directorship", org.id, entity.id, person.role)
        link.add("director", entity.id)
        link.add("organization", org.id)
        link.add("role", person.role)
        link.add("proof", document_id)
        yield link


def _mention(entity: EntityProxy, prop, value: str, schema: str) -> EntityProxy | None:
    """Same id scheme as ftm-analyze, so a name found by NER and rules is stored once."""
    key = normalize_name(prop.type.node_id_safe(value))
    if not key:
        return None
    mention = model.make_entity("Mention")
    mention.make_id("mention", entity.id, prop.name, key)
    mention.add("resolved", make_entity_id(key))
    mention.add("document", entity.id)
    mention.add("name", value)
    mention.add("detectedSchema", schema)
    mention.add("contextCountry", "de")
    return mention


def german_entities(entity: EntityProxy, findings: Findings) -> Iterable[EntityProxy]:
    """
    Yield mention, address and company entities for rule based findings and
    patch the analyzed document with the matching `*Mentioned` properties.
    """
    for values, prop, schema in (
        (findings.organizations, TAG_COMPANY, "Organization"),
        (findings.public_bodies, TAG_COMPANY, "PublicBody"),
        (findings.persons, TAG_PERSON, "Person"),
    ):
        for value in sorted(values):
            if mention := _mention(entity, prop, value, schema):
                yield mention
                entity.add(prop, value, quiet=True)

    # NER often tags `Amtsgericht Leipzig` as a location
    bodies = {fold(b) for b in findings.public_bodies}
    if bodies and (locations := entity.get(TAG_LOCATION)):
        entity.set(TAG_LOCATION, [v for v in locations if fold(v) not in bodies])

    for address in sorted(findings.addresses, key=lambda a: a.full):
        place = model.make_entity("Address")
        place.id = place.make_id("german-address", address.full.lower())
        place.add("full", address.full)
        place.add("street", f"{address.street} {address.number}")
        place.add("postalCode", address.postal_code)
        place.add("city", address.city)
        place.add("country", "de")
        place.add("proof", entity.id)
        yield place
        entity.add(TAG_LOCATION, address.full, quiet=True)

    # an imprint names one company with its register entry and VAT id
    registered = [r for r in findings.register_entries if r.organization]
    single = len({r.organization for r in registered}) == 1
    for entry in sorted(registered, key=lambda r: r.number):
        company = model.make_entity("Company")
        company.id = organization_id(entry.court, entry.number)
        company.add("name", entry.organization)
        company.add("registrationNumber", entry.number)
        company.add("jurisdiction", "de")
        company.add("country", "de")
        company.add("notes", f"Registergericht: {entry.court}" if entry.court else None)
        company.add("proof", entity.id)
        if single:
            company.add("vatCode", sorted(findings.vat_ids))
        yield company
        entity.add(TAG_COMPANY, entry.organization, quiet=True)
    if not (single and registered):
        entity.add("keywords", sorted(findings.vat_ids), quiet=True)


def drop_noisy_mentions(results: list[EntityProxy]) -> list[EntityProxy]:
    """
    Remove implausible organization/person mentions found by the NER model and
    the matching `*Mentioned` values on the analyzed entity.
    """
    dropped: dict[str, set[str]] = {TAG_COMPANY.name: set(), TAG_PERSON.name: set()}
    kept: list[EntityProxy] = []
    for result in results:
        if result.schema.name == "Mention":
            schema = result.first("detectedSchema")
            name = result.first("name") or ""
            if schema in ("Organization", "Company", "Person", "LegalEntity") and not is_plausible_name(name):
                prop = TAG_PERSON if schema == "Person" else TAG_COMPANY
                dropped[prop.name].add(name)
                continue
        kept.append(result)
    for result in kept:
        if result.schema.is_a("Analyzable"):
            for prop_name, names in dropped.items():
                if names and (values := result.get(prop_name)):
                    result.pop(prop_name)
                    result.add(prop_name, [v for v in values if v not in names], quiet=True)
    return kept
