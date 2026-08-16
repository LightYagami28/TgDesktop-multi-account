# Telegram Desktop Build Environment - CentOS Stream 9 (Latest)
# Production-ready, security-hardened, actively maintained
# Audio libraries installed from alternative sources

FROM quay.io/centos/centos:stream9 AS tdesktop_builder

LABEL maintainer="TgDesktop Multi-Account Builder"
LABEL description="Secure build environment for Telegram Desktop with multi-account support"
LABEL version="1.3.0"

# Prevent interactive prompts
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    MAKEFLAGS=${MAKEFLAGS:--j4}

# Install CRB (CodeReady Builder) repository for additional packages
RUN dnf config-manager --set-enabled crb && \
    dnf install -y --setopt=install_weak_deps=False \
      dnf-plugins-core epel-release epel-next-release && \
    dnf install -y --setopt=install_weak_deps=False --allowerasing \
      gcc gcc-c++ make cmake git \
      openssl openssl-devel libstdc++-devel zlib-devel \
      libjpeg-turbo-devel libpng-devel libwebp-devel \
      pulseaudio-libs-devel alsa-lib-devel \
      qt5-qtbase-devel qt5-qtimageformats-devel qt5-qtsvg-devel \
      pkgconfig python3 wget curl ca-certificates && \
    dnf clean all && \
    rm -rf /var/cache/dnf/* /tmp/* /var/tmp/* && \
    groupadd -r builder && \
    useradd -r -g builder -u 1000 -d /home/builder -s /sbin/nologin -c "Build user" builder && \
    mkdir -p /home/builder && \
    chown -R builder:builder /home/builder

# Set working directory
WORKDIR /usr/src/tdesktop

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -d /usr/src/tdesktop || exit 1

# Default build command
CMD ["/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh"]
