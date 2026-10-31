"""
Rule based extraction for German text. Pure functions without FollowTheMoney
or OpenAleph imports, so they are testable and reusable on their own.
"""

from dataclasses import dataclass, field

from ftm_analyze_de.extract.addresses import Address, find_addresses
from ftm_analyze_de.extract.identifiers import RegisterEntry, find_register_entries, find_vat_ids
from ftm_analyze_de.extract.orgs import find_organizations, find_public_bodies
from ftm_analyze_de.extract.persons import find_persons
from ftm_analyze_de.normalize import dedupe


@dataclass
class Findings:
    organizations: set[str] = field(default_factory=set)
    public_bodies: set[str] = field(default_factory=set)
    persons: set[str] = field(default_factory=set)
    addresses: set[Address] = field(default_factory=set)
    vat_ids: set[str] = field(default_factory=set)
    register_entries: set[RegisterEntry] = field(default_factory=set)

    def __bool__(self) -> bool:
        return any(vars(self).values())


def extract_german(text: str) -> Findings:
    return Findings(
        organizations=dedupe(find_organizations(text)),
        public_bodies=find_public_bodies(text),
        persons=dedupe(find_persons(text)),
        addresses=find_addresses(text),
        vat_ids=find_vat_ids(text),
        register_entries=find_register_entries(text),
    )


__all__ = ["Address", "Findings", "RegisterEntry", "extract_german"]
