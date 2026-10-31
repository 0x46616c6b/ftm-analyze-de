# ftm-analyze-de

German language extension for [ftm-analyze](https://github.com/openaleph/ftm-analyze), the
entity extraction stage of [OpenAleph](https://openaleph.org). Drop-in replacement for the
`analyze` worker image, and a CLI for FollowTheMoney entity streams.

Stock ftm-analyze runs unchanged first (language detection, NER, e-mail, IBAN). On top of it:

| Area | Stock ftm-analyze | ftm-analyze-de |
|---|---|---|
| NER model | `de_core_news_sm` | `de_core_news_lg` |
| Short names | Names under 8 characters are dropped (`Bosch`, `Dresden`, `Merkel`) | Length limit 3 characters; upstream's type model still rejects some single words |
| Phone numbers | Only with country prefix (`+49 …`) | National notation too (`0351 4567890`, `(030) 1234-56`), stored as E.164 |
| Organizations | NER only | Plus rules for German legal forms (GmbH & Co. KG, UG (haftungsbeschränkt), e.V., gGmbH, KGaA, PartG mbB, AöR, …) |
| Public bodies | NER only | Courts, prosecutors, ministries, authorities (`Amtsgericht Dresden`, `Bundesministerium für …`) |
| Persons | NER only | Plus names after salutations, titles and offices (`Frau Dr.`, `Rechtsanwalt`, `Oberbürgermeisterin`) |
| Addresses | — | `Straße Nr, PLZ Ort`, `Am Markt 7`, `Postfach` as `Address` entities |
| Register entries | — | `Amtsgericht Dresden, HRB 12345` linked to the company named before it, with VAT id |
| Register printouts | — | Handelsregister/Vereinsregister printouts yield `Company`, `Person`, `Directorship` |
| OCR text | — | Words hyphenated at line ends are joined before NER |

## Use with OpenAleph

Replace the image of the `analyze` worker and route the stage to this task:

```yaml
analyze:
  image: ghcr.io/0x46616c6b/ftm-analyze-de:0.1.0
  command: procrastinate worker -q analyze
  environment:
    OPENALEPH_ANALYZE_TASK: ftm_analyze_de.tasks.analyze
```

Jobs queued under `ftm_analyze.tasks.analyze` still run, so switching images needs no queue drain.
Image tags follow the releases of this project (`0.1.0`, `0.1`, `latest`); `0.1.0-ftm-analyze-5.3.2`
names the ftm-analyze base as well. Only `linux/amd64`, like the upstream image.

## Releasing

Release Drafter keeps a draft release with the merged pull requests. Labels choose the section and
the next version: `feature`/`enhancement` minor, `major` major, everything else patch. Publishing the
draft creates the tag and builds and pushes the image.

## CLI

```bash
docker run -i --rm --entrypoint ftm-analyze-de ghcr.io/0x46616c6b/ftm-analyze-de:0.1.0 \
  analyze < entities.ftm.json > results.ftm.json
```

## Settings

Environment variables. All upstream `FTM_ANALYZE_*` settings apply as well, e.g.
`FTM_ANALYZE_NER_ENGINE` or `FTM_ANALYZE_SPACY_MODELS_DEU`.

| Variable | Default | |
|---|---|---|
| `FTM_ANALYZE_DE_NAME_MIN_LENGTH` | `3` | Shortest NER name kept |
| `FTM_ANALYZE_DE_PHONE_REGION` | `DE` | Country for numbers without international prefix |
| `FTM_ANALYZE_DE_LANGUAGES` | `de,deu,ger` | Detected languages that enable the German rules |
| `FTM_ANALYZE_DE_RULES_WITHOUT_LANGUAGE` | `true` | Apply the rules when no language was detected |
| `FTM_ANALYZE_DE_REGISTER_MODE` | `auto` | `auto`: parse register printouts recognised by their page header, `off` |
| `FTM_ANALYZE_DE_REGISTER_DATASETS` | | Datasets always parsed as register printouts, e.g. `collection_4` |
| `FTM_TRANSLATE_TARGET_LANGUAGE` | | Documents in other languages are sent to translation; unset: none |

## Development

Pure extractors (`ftm_analyze_de/extract`) only need `phonenumbers`:

```bash
PYTHONPATH=. uv run --no-project --with phonenumbers --with pytest pytest tests/test_extract.py
```

The full suite needs ftm-analyze with its models and native dependencies; it runs in the
`test` stage of the image:

```bash
docker build --platform linux/amd64 --target test -t ftm-analyze-de:test .
docker run --rm ftm-analyze-de:test
```

Upstream internals changed by this package are all in `ftm_analyze_de/compat.py`.

## License

AGPL-3.0-or-later, like ftm-analyze.
