FROM debian:12

RUN apt update && apt install -y \
    python3 \
    python3-venv \
    ffmpeg \
    libsm6 \
    libxext6 \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/.venv
ENV PATH="/opt/.venv/bin:$PATH"

RUN pip install trame --no-cache-dir
RUN pip install trame-vuetify trame-vtk --no-cache-dir
RUN pip install vtk --no-cache-dir
RUN pip install flask --no-cache-dir

EXPOSE 8080

WORKDIR /data

COPY ./on_start_container.sh .

SHELL ["/bin/bash", "-c"]

ENTRYPOINT ./on_start_container.sh