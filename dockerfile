FROM mcr.microsoft.com/devcontainers/miniconda:1-3

#unix
RUN umask 0002 \
    && conda create --yes --name garena --channel conda-forge python=3.12 nodejs=22 pip \
    && conda clean --all --yes

WORKDIR /workspace

CMD ["sleep", "infinity"]
