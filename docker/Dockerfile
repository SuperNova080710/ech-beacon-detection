# syntax=docker/dockerfile:1.7

ARG DEBIAN_IMAGE=debian:bookworm-slim

FROM ${DEBIAN_IMAGE} AS openssl-build
ARG OPENSSL_VERSION=4.0.1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src
RUN git clone --depth 1 --branch "openssl-${OPENSSL_VERSION}" \
    https://github.com/openssl/openssl.git openssl

WORKDIR /usr/src/openssl
RUN ./config \
        --prefix=/opt/openssl \
        --openssldir=/opt/openssl \
        no-tests \
    && make -j"$(nproc)" \
    && make install_sw \
    && make install_ssldirs \
    && test -s /opt/openssl/openssl.cnf

FROM ${DEBIAN_IMAGE} AS nginx-build
ARG NGINX_VERSION=1.30.6
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        libpcre2-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=openssl-build /opt/openssl /opt/openssl

WORKDIR /usr/src
RUN curl -fsSLO "https://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" \
    && tar -xzf "nginx-${NGINX_VERSION}.tar.gz"

WORKDIR /usr/src/nginx-${NGINX_VERSION}
RUN ./configure \
        --prefix=/usr/local/nginx \
        --sbin-path=/usr/local/sbin/nginx \
        --conf-path=/etc/nginx/nginx.conf \
        --pid-path=/tmp/nginx.pid \
        --lock-path=/tmp/nginx.lock \
        --http-log-path=/dev/stdout \
        --error-log-path=/dev/stderr \
        --with-http_ssl_module \
        --with-http_v2_module \
        --with-threads \
        --with-cc-opt='-O2 -fstack-protector-strong -I/opt/openssl/include' \
        --with-ld-opt='-L/opt/openssl/lib64 -L/opt/openssl/lib -Wl,-rpath,/opt/openssl/lib64 -Wl,-rpath,/opt/openssl/lib' \
    && make -j"$(nproc)" \
    && make install

FROM ${DEBIAN_IMAGE} AS curl-build
ARG CURL_VERSION=8.20.0
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/openssl/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/openssl/lib64:/opt/openssl/lib"
ENV PKG_CONFIG_PATH="/opt/openssl/lib64/pkgconfig:/opt/openssl/lib/pkgconfig"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY --from=openssl-build /opt/openssl /opt/openssl

WORKDIR /usr/src
RUN curl -fsSLO "https://curl.se/download/curl-${CURL_VERSION}.tar.xz" \
    && tar -xf "curl-${CURL_VERSION}.tar.xz"

WORKDIR /usr/src/curl-${CURL_VERSION}
RUN ./configure \
        --prefix=/opt/curl-ech \
        --with-openssl=/opt/openssl \
        --enable-ech \
        --disable-shared \
        --enable-static \
        --disable-ldap \
        --disable-ldaps \
        --without-zlib \
        --without-brotli \
        --without-zstd \
        --without-libpsl \
        --without-libidn2 \
        --without-librtmp \
        --without-libssh2 \
        --without-nghttp2 \
        --without-ngtcp2 \
        --without-nghttp3 \
    && make -j"$(nproc)" \
    && make install

FROM ${DEBIAN_IMAGE} AS ech-nginx
ARG NGINX_VERSION=1.30.6
ARG OPENSSL_VERSION=4.0.1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/openssl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ENV LD_LIBRARY_PATH="/opt/openssl/lib64:/opt/openssl/lib"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libpcre2-8-0 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 101 nginx \
    && useradd --system --uid 101 --gid nginx --home-dir /nonexistent --shell /usr/sbin/nologin nginx \
    && install -d -o 101 -g 101 -m 0755 /var/cache/nginx /run \
    && install -d -o 101 -g 101 -m 1777 /tmp

COPY --from=openssl-build /opt/openssl /opt/openssl
COPY --from=nginx-build /usr/local/nginx /usr/local/nginx
COPY --from=nginx-build /usr/local/sbin/nginx /usr/local/sbin/nginx

LABEL org.opencontainers.image.title="ech-beacon-nginx"
LABEL org.opencontainers.image.description="NGINX ${NGINX_VERSION} linked against OpenSSL ${OPENSSL_VERSION} for RFC 9849 ECH testing"

USER 101:101
EXPOSE 8443
STOPSIGNAL SIGQUIT
CMD ["/usr/local/sbin/nginx", "-g", "daemon off;"]

FROM ${DEBIAN_IMAGE} AS ech-tools
ARG OPENSSL_VERSION=4.0.1
ARG CURL_VERSION=8.20.0
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/curl-ech/bin:/opt/openssl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ENV LD_LIBRARY_PATH="/opt/openssl/lib64:/opt/openssl/lib"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3-minimal \
        tcpdump \
        tshark \
    && rm -rf /var/lib/apt/lists/*

COPY --from=openssl-build /opt/openssl /opt/openssl
COPY --from=curl-build /opt/curl-ech /opt/curl-ech

LABEL org.opencontainers.image.title="ech-beacon-tools"
LABEL org.opencontainers.image.description="OpenSSL ${OPENSSL_VERSION}, curl ${CURL_VERSION} with ECH support, Python, and packet-analysis tools"

CMD ["sleep", "infinity"]
