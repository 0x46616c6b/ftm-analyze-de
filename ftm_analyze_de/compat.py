"""
The only place that changes ftm-analyze internals. Upstream has no hooks for
these, so module attributes are replaced at import time:

- `extract.base.NAME_MIN_LENGTH`: upstream drops every name below 8 characters
- the phone regex in `patterns.REGEX_TYPES`: upstream only accepts numbers with
  country prefix; national numbers (`0351 123456`) are now read in a region

Both are read at call time upstream, so no function is replaced. A version
check fails loudly when an untested ftm-analyze release is installed.
"""

from importlib.metadata import version

from ftm_analyze_de.extract.phones import PhonePattern
from ftm_analyze_de.settings import Settings

SUPPORTED = ("5.3.",)

_applied = False


def apply(settings: Settings) -> None:
    global _applied
    if _applied:
        return
    installed = version("ftm-analyze")
    if not installed.startswith(SUPPORTED):
        raise RuntimeError(f"ftm-analyze {installed} is not supported, expected {' or '.join(SUPPORTED)}x")

    from ftm_analyze.analysis import patterns
    from ftm_analyze.analysis.extract import base

    if not hasattr(base, "NAME_MIN_LENGTH") or not hasattr(patterns, "PHONE_REGEX"):
        raise RuntimeError("ftm-analyze internals changed, update ftm_analyze_de.compat")

    base.NAME_MIN_LENGTH = settings.name_min_length
    prop = patterns.REGEX_TYPES.pop(patterns.PHONE_REGEX)
    patterns.REGEX_TYPES[PhonePattern(settings.phone_region)] = prop
    _applied = True
