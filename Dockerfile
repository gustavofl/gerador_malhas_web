FROM debian:12

RUN apt update
RUN apt install python3 -y
RUN apt install python3-venv -y
RUN apt install ffmpeg libsm6 libxext6 -y

RUN python3 -m venv /opt/.venv
ENV PATH="/opt/.venv/bin:$PATH"

RUN pip install trame
RUN pip install trame-vuetify trame-vtk
RUN pip install vtk

RUN apt install git -y

EXPOSE 8080

WORKDIR /data

COPY ./on_start_container.sh .

SHELL ["/bin/bash", "-c"]

ENTRYPOINT ./on_start_container.sh