# Telegram Desktop Build Environment - CentOS Stream 9 (Latest)
# Production-ready, security-hardened, clean dependencies

FROM quay.io/centos/centos:stream9@sha256:b76d33c9df2e709b3a2d81ed2913c9deee814a9aabba16a57226b3a9fbea6d84

LABEL maintainer="TgDesktop Multi-Account Builder"
LABEL description="Secure build environment for Telegram Desktop with multi-account support"
LABEL version="1.3.0"

# Environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    MAKEFLAGS=-j4

# Pin delle versioni major: vincolano dnf senza fissare patch del rolling stream.
RUN dnf update -y && \
    dnf install -y \
      gcc-11 gcc-c++-11 make-4 cmake-3 git-2 \
      openssl-3 openssl-devel-3 libstdc++-devel-11 zlib-devel-1 \
      libjpeg-turbo-devel-2 libpng-devel-1 libwebp-devel-1 \
      qt5-qtbase-devel-5 qt5-qtimageformats-devel-5 qt5-qtsvg-devel-5 \
      pkgconf-pkg-config-1 python3-3 wget-1 && \
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
