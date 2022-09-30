FROM pytorch/pytorch:1.10.0-cuda11.3-cudnn8-devel

RUN apt-key del 7fa2af80 && \
    apt-key adv --fetch-keys http://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/3bf863cc.pub \
    apt-get update \
    apt install -y bash \
    build-essential \
    libsndfile1-dev \
    git-lfs \
    ffmpeg \
    sox \
    wget \
    libsox-fmt-mp3

RUN mkdir -p /workspace/
WORKDIR /workspace/
COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt && \
    python3 -m pip install --no-cache-dir jupyter ipython
