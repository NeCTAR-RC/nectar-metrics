FROM python:3.14-slim-trixie

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Running pip as root is expected inside the image build
ENV PIP_ROOT_USER_ACTION=ignore

# Install pip requirements. A C/C++ toolchain is only needed to build wheels
# during the install (numpy has no Python 3.14 wheels for the constrained
# version), so install it, build, then purge it and the apt cache so the
# compilers are not left in the runtime image.
COPY requirements.txt .

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && python -m pip install --no-cache-dir \
        -c https://releases.openstack.org/constraints/upper/2026.1 \
        -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY dist/* /app

RUN python -m pip install --no-cache-dir \
        -c https://releases.openstack.org/constraints/upper/2026.1 \
        *.tar.gz \
    && rm *.tar.gz

# Creates a non-root user and adds permission to access the /app folder
RUN useradd -u 42420 appuser && chown -R appuser /app
USER appuser

# The collectors are one-shot commands run by cron or a CronJob spec,
# which supplies the real command (nectar-metrics-nova, -cinder,
# -rcshibboleth). Config is expected at /etc/nectar/metrics.ini.
CMD ["nectar-metrics-nova", "--help"]
