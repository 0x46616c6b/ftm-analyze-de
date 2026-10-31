"""
Drop-in replacement for the OpenAleph `analyze` stage. Point OpenAleph at it with
`OPENALEPH_ANALYZE_TASK=ftm_analyze_de.tasks.analyze`.
"""

from os import environ

from followthemoney.proxy import EntityProxy
from ftm_analyze.tasks import should_geocode
from openaleph_procrastinate import defer
from openaleph_procrastinate.app import make_app
from openaleph_procrastinate.model import DatasetJob
from openaleph_procrastinate.settings import OpenAlephSettings
from openaleph_procrastinate.tasks import task
from openaleph_procrastinate.util import make_stub_entity

from ftm_analyze_de.pipeline import analyze_entity_de

app = make_app(__loader__.name)
TASK_OPTIONS = {"retry": defer.tasks.analyze.retries, "tracer_uri": OpenAlephSettings().redis_url}
ORIGIN = "analyze"
ORIGIN_REGISTER = "hr-analyze"
# upstream reads an unset variable as the language "None" and translates everything
TARGET_LANGUAGE = environ.get("FTM_TRANSLATE_TARGET_LANGUAGE") or None


def should_translate(result: EntityProxy, entity: EntityProxy) -> bool:
    if TARGET_LANGUAGE is None or not result.schema.is_a("Document"):
        return False
    if any(lang != TARGET_LANGUAGE for lang in result.get("detectedLanguage", quiet=True)):
        return entity.has("indexText", quiet=True) or entity.has("bodyText", quiet=True)
    return False


def _run(job: DatasetJob) -> None:
    to_translate = []
    to_geocode = []
    to_index = []

    overwrite_lang = job.context.get("overwrite_lang", False)
    with job.get_writer() as bulk:
        for entity in job.load_entities():
            results, register = analyze_entity_de(entity, overwrite_lang=overwrite_lang, dataset=job.dataset)
            for result in results:
                bulk.put(result, origin=ORIGIN, fragment=entity.id)
                to_index.append(make_stub_entity(result))
                if should_geocode(result):
                    to_geocode.append(make_stub_entity(result))
                if should_translate(result, entity):
                    to_translate.append(make_stub_entity(result))
            for result in register:
                bulk.put(result, origin=ORIGIN_REGISTER, fragment=entity.id)
                to_index.append(make_stub_entity(result))

    if to_index:
        defer.index(app, job.dataset, to_index, batch=job.batch, **job.context)
    if to_geocode:
        defer.geocode(app, job.dataset, to_geocode, batch=job.batch, **job.context)
    if to_translate:
        defer.translate(app, job.dataset, to_translate, batch=job.batch, **job.context)


@task(app=app, **TASK_OPTIONS)
def analyze(job: DatasetJob) -> None:
    _run(job)


# jobs deferred under the names of the stock and the former image still run
@task(app=app, name="ftm_analyze.tasks.analyze", **TASK_OPTIONS)
def analyze_stock(job: DatasetJob) -> None:
    _run(job)


@task(app=app, name="hr_analyze.tasks.analyze", **TASK_OPTIONS)
def analyze_hr(job: DatasetJob) -> None:
    _run(job)
