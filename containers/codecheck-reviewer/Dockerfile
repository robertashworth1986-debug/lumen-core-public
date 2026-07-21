FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04@sha256:3612b800eaae8513e7dca54f21d2e4eda48eda57426f3746a78677f342ac7ee9

ARG UV_VERSION=0.11.28
ARG UV_SHA256=e490a6464492183c5d4534a5527fb4440f7f2bb2f228162ad7e4afe076dc0224

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -eux; \
    curl --fail --location --silent --show-error \
      "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" \
      --output /tmp/uv.tar.gz; \
    echo "${UV_SHA256}  /tmp/uv.tar.gz" | sha256sum --check --strict; \
    tar --extract --gzip --file /tmp/uv.tar.gz --directory /tmp; \
    install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv; \
    install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx; \
    rm -rf /tmp/uv.tar.gz /tmp/uv-x86_64-unknown-linux-gnu; \
    uv python install 3.11.9; \
    python_path="$(uv python find 3.11.9)"; \
    ln -sf "${python_path}" /usr/local/bin/python; \
    ln -sf "${python_path}" /usr/local/bin/python3; \
    uv venv --python 3.11.9 --seed /opt/reviewer-venv

COPY requirements-reviewer.txt /opt/reviewer-lock/requirements-reviewer.txt
COPY requirements-reviewer-ubuntu-py311.lock /opt/reviewer-lock/requirements-reviewer-ubuntu-py311.lock

RUN set -eux; \
    /opt/reviewer-venv/bin/python -m pip install --disable-pip-version-check \
      --require-hashes \
      --only-binary=:all: \
      --requirement /opt/reviewer-lock/requirements-reviewer-ubuntu-py311.lock; \
    /opt/reviewer-venv/bin/python -m pip check; \
    rm -rf /root/.cache/pip

COPY containers/codecheck-reviewer/run_capsule.sh /usr/local/bin/run-codecheck-capsule
RUN chmod 0755 /usr/local/bin/run-codecheck-capsule

ENV PATH="/opt/reviewer-venv/bin:${PATH}" \
    PYTHONHASHSEED=0 \
    TZ=UTC \
    OMP_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

LABEL org.opencontainers.image.title="LumenCore bounded CODECHECK reviewer"
LABEL org.opencontainers.image.source="https://github.com/robertashworth1986-debug/lumen-core-public"
LABEL org.opencontainers.image.base.digest="sha256:3612b800eaae8513e7dca54f21d2e4eda48eda57426f3746a78677f342ac7ee9"

WORKDIR /work/repo
ENTRYPOINT ["/usr/local/bin/run-codecheck-capsule"]
