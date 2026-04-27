FROM debian:bookworm-slim AS ffmpeg-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    cmake \
    curl \
    git \
    libfdk-aac-dev \
    libmp3lame-dev \
    libopus-dev \
    libtool \
    libvorbis-dev \
    nasm \
    pkg-config \
    yasm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN git clone --depth 1 https://git.ffmpeg.org/ffmpeg.git ffmpeg
WORKDIR /tmp/ffmpeg
RUN ./configure \
    --disable-static \
    --enable-shared \
    --enable-gpl \
    --enable-libfdk-aac \
    --enable-nonfree \
    --disable-debug \
    --disable-doc \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-builder /usr/local/bin/ffprobe /usr/local/bin/ffprobe
COPY --from=ffmpeg-builder /usr/local/lib/*.so* /usr/local/lib/
RUN ldconfig

WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/entrypoint.sh ./entrypoint.sh

RUN mkdir -p /input /output
RUN chmod +x /app/entrypoint.sh

ENV INPUT_DIR=/input
ENV OUTPUT_DIR=/output
ENV CONVERT_FORMAT=aac
ENV BITRATE=320k
ENV MAX_THREADS=2
ENV DELETE_SOURCE=false
ENV LOG_LEVEL=INFO
ENV RETRY_LIMIT=3

ENTRYPOINT ["/app/entrypoint.sh"]
