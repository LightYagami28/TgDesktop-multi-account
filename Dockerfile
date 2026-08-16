# Multi-stage Telegram Desktop Build Environment
# Based on CentOS 7 for maximum compatibility
# Security-hardened with minimal attack surface

FROM centos:7 AS tdesktop_builder

LABEL maintainer="TgDesktop Multi-Account Builder"
LABEL description="Secure build environment for Telegram Desktop with multi-account support"
LABEL version="1.3.0"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    MAKEFLAGS=${MAKEFLAGS:--j4}

# Install security updates and build dependencies
RUN yum update -y && \
    yum install -y epel-release && \
    yum install -y \
      # Build tools
      gcc gcc-c++ make cmake ninja-build \
      # Version control
      git \
      # Dependencies
      openssl openssl-devel \
      libstdc++-devel \
      zlib-devel \
      libjpeg-turbo-devel \
      libpng-devel \
      libwebp-devel \
      opus-devel \
      openal-soft-devel \
      # Qt dependencies
      qt5-qtbase-devel \
      qt5-qtimageformats-devel \
      qt5-qtsvg-devel \
      # Additional tools
      pkgconfig \
      python \
      wget \
      curl && \
    # Clean up package manager cache to reduce image size
    yum clean all && \
    rm -rf /var/cache/yum/* /tmp/* /var/tmp/*

# Create build user (non-root for security)
RUN groupadd -r builder && \
    useradd -r -g builder -u 1000 -d /home/builder -s /sbin/nologin -c "Build user" builder && \
    mkdir -p /home/builder && \
    chown -R builder:builder /home/builder

# Set working directory
WORKDIR /usr/src/tdesktop

# Copy build script
COPY --chown=builder:builder . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -d /usr/src/tdesktop || exit 1

# Default build command
CMD ["/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh"]
