ARG BASE_VERSION=5.3.2
FROM ghcr.io/openaleph/ftm-analyze:${BASE_VERSION} AS base

# Larger German NER model instead of the default de_core_news_sm
ARG DE_MODEL_VERSION=3.8.0
RUN python -m ensurepip \
    && python -m pip install --no-cache-dir \
      "https://github.com/explosion/spacy-models/releases/download/de_core_news_lg-${DE_MODEL_VERSION}/de_core_news_lg-${DE_MODEL_VERSION}-py3-none-any.whl"

COPY pyproject.toml README.md LICENSE /src/
COPY ftm_analyze_de /src/ftm_analyze_de
# dependencies come with the base image
RUN python -m pip install --no-cache-dir --no-deps /src

ENV PROCRASTINATE_APP=ftm_analyze_de.tasks.app \
    FTM_ANALYZE_SPACY_MODELS_DEU=de_core_news_lg \
    FTM_ANALYZE_NER_DEFAULT_LANG=deu

FROM base AS test
RUN python -m pip install --no-cache-dir pytest
COPY tests /src/tests
# upstream finds its models relative to the working directory /app
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir=/src", "/src/tests"]

FROM base AS runtime
RUN python -m pip uninstall -y pip
