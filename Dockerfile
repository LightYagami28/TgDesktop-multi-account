# Telegram Desktop Build Environment - CentOS Stream 9 (Latest)
# Production-ready, security-hardened, clean dependencies

FROM quay.io/centos/centos:stream9@sha256:99a7748660352b7d87e5689805ddafa6209d6019d0c5b642b5354656dff02be3

LABEL maintainer="TgDesktop Multi-Account Builder"
LABEL description="Secure build environment for Telegram Desktop with multi-account support"
LABEL version="1.3.0"

# Environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    MAKEFLAGS=-j4

# CentOS Stream rolls forward, so exact dnf versions would break the next build.
RUN dnf update -y && \
    dnf install -y \
      gcc gcc-c++ make cmake git \
      openssl openssl-devel libstdc++-devel zlib-devel \
      libjpeg-turbo-devel libpng-devel libwebp-devel \
      qt5-qtbase-devel qt5-qtimageformats-devel qt5-qtsvg-devel \
      pkgconfig python3 wget && \
    dnf clean all && \
    rm -rf /var/cache/dnf/* /tmp/* /var/tmp/* && \
    groupadd -r builder && \
    useradd -r -g builder -u 1000 -d /home/builder -s /sbin/nologin builder && \
    mkdir -p /home/builder && \
    chown -R builder:builder /home/builder

# Set working directory
WORKDIR /usr/src/tdesktop

# Never run the build container as root by default.
USER 1000:1000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["test", "-d", "/usr/src/tdesktop"]

# Default build command
CMD ["/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh"]
