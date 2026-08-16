# Telegram Desktop Build Environment - CentOS Stream 9 (Latest)
# Production-ready, security-hardened, clean dependencies

FROM quay.io/centos/centos:stream9

LABEL maintainer="TgDesktop Multi-Account Builder"
LABEL description="Secure build environment for Telegram Desktop with multi-account support"
LABEL version="1.3.0"

# Environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    MAKEFLAGS=-j4

# Update and install core build dependencies
RUN dnf update -y && \
    dnf install -y \
      gcc gcc-c++ make cmake git \
      openssl openssl-devel libstdc++-devel zlib-devel \
      libjpeg-turbo-devel libpng-devel libwebp-devel \
      qt5-qtbase-devel qt5-qtimageformats-devel qt5-qtsvg-devel \
      pkgconfig python3 wget && \
    dnf clean all && \
    rm -rf /var/cache/dnf/* /tmp/* /var/tmp/*

# Create non-root build user
RUN groupadd -r builder && \
    useradd -r -g builder -u 1000 -d /home/builder -s /sbin/nologin builder && \
    mkdir -p /home/builder && \
    chown -R builder:builder /home/builder

# Set working directory
WORKDIR /usr/src/tdesktop

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -d /usr/src/tdesktop || exit 1

# Default build command
CMD ["/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh"]
