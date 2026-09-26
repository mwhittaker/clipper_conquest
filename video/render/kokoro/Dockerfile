FROM python:3.12-slim
RUN apt-get update -qq && apt-get install -y -qq espeak-ng >/dev/null && rm -rf /var/lib/apt/lists/*
RUN pip install -q --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch kokoro soundfile
ENV HF_HOME=/hf
