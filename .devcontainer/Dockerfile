FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    curl \
    libegl1 libglu1-mesa-dev \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /root
RUN curl -L -o mambaforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"
RUN bash mambaforge.sh -b -p $HOME/mambaforge
RUN rm mambaforge.sh

RUN . /root/mambaforge/bin/activate \
    && mamba init bash \
    && . /root/.bashrc \
    && mamba create -y -n cq python \
    && mamba activate cq \
    && mamba install -y -c CadQuery \
        cadquery=master \
    && mamba install -y -c CadQuery \
        cq-editor=master \
    && mamba clean -a -y

RUN echo "source /root/mambaforge/bin/activate" >> /root/.bashrc
RUN echo "mamba activate cq" >> /root/.bashrc