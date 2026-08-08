FROM mcr.microsoft.com/devcontainers/miniconda:1-3

#unix
RUN umask 0002 \
    && conda create --yes --name garena --channel conda-forge python=3.12 nodejs=22 pip \
    && conda clean --all --yes

ENV PATH="/opt/conda/envs/garena/bin:${PATH}"

RUN echo '. /opt/conda/etc/profile.d/conda.sh' >> /home/vscode/.bashrc \
    && echo 'conda activate garena' >> /home/vscode/.bashrc \
    && chown vscode:vscode /home/vscode/.bashrc

WORKDIR /workspace

CMD ["sleep", "infinity"]
