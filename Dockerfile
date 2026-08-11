FROM python:3.13-slim AS build

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 patchwitness
COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

USER patchwitness
WORKDIR /workspace
ENTRYPOINT ["patchwitness"]
CMD ["--help"]

