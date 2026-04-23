# Kage — Kali pentest sandbox.
# Users run their own Claude Code on the host; this container is a tool sidecar.

FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/usr/local/go/bin:/home/pentester/go/bin:/home/pentester/.local/bin:$PATH" \
    GOPATH=/home/pentester/go \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN for i in 1 2 3 4 5; do apt-get update && break || { echo "[retry $i/5] apt-get update"; sleep 10; }; done \
 && apt-get install -y --no-install-recommends kali-archive-keyring sudo \
 && for i in 1 2 3 4 5; do apt-get update && break || { echo "[retry $i/5] apt-get update"; sleep 10; }; done \
 && useradd -m -s /bin/bash pentester \
 && usermod -aG sudo pentester \
 && echo "pentester ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/pentester \
 && chmod 0440 /etc/sudoers.d/pentester \
 && touch /home/pentester/.hushlogin \
 && apt-get install -y --no-install-recommends \
      kali-linux-headless \
      curl wget git unzip jq ripgrep parallel tmux vim less tree file \
      ca-certificates gnupg \
      build-essential libssl-dev libffi-dev libpcap-dev pkg-config \
      python3 python3-pip python3-dev python3-venv python3-setuptools \
      iproute2 iputils-ping netcat-traditional \
      libcap2-bin \
 && rm -rf /var/lib/apt/lists/* \
 && setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip "$(which nmap)"

RUN pip3 install --break-system-packages --ignore-installed \
      'curl_cffi==0.7.4' \
      'semgrep==1.95.0' \
      'bandit==1.8.0' \
      'trufflehog==2.2.1' \
      'camoufox==0.4.11' \
      'schemathesis==3.39.5' \
      'requests==2.32.3' \
      'safety==3.2.11' \
      'ruff==0.8.2'

ARG TARGETARCH
RUN GO_VERSION=1.24.4 \
 && case "${TARGETARCH:-amd64}" in \
      amd64) GO_ARCH=amd64 ;; \
      arm64) GO_ARCH=arm64 ;; \
      *) echo "Unsupported arch: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
 && curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" \
      | tar -C /usr/local -xz

USER pentester
WORKDIR /home/pentester
RUN set -eux; \
    for tool in \
      github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
      github.com/projectdiscovery/httpx/cmd/httpx@latest \
      github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
      github.com/projectdiscovery/katana/cmd/katana@latest \
      github.com/projectdiscovery/naabu/v2/cmd/naabu@latest \
      github.com/projectdiscovery/dnsx/cmd/dnsx@latest \
      github.com/projectdiscovery/alterx/cmd/alterx@latest \
      github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest \
      github.com/projectdiscovery/uncover/cmd/uncover@latest \
      github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest \
      github.com/d3mondev/puredns/v2@latest \
      github.com/lc/gau/v2/cmd/gau@latest \
      github.com/jaeles-project/gospider@latest \
      github.com/hakluke/hakrawler@latest \
      github.com/ffuf/ffuf/v2@latest \
      github.com/hahwul/dalfox/v2@latest \
      github.com/zricethezav/gitleaks/v8@latest \
      github.com/tomnomnom/waybackurls@latest \
      github.com/tomnomnom/anew@latest \
      github.com/tomnomnom/qsreplace@latest \
      github.com/tomnomnom/unfurl@latest \
      github.com/tomnomnom/gf@latest \
      github.com/owasp-amass/amass/v4/...@master \
    ; do /usr/local/go/bin/go install -v "$tool"; done \
 && /usr/local/go/bin/go clean -cache -modcache

USER root
RUN cp /home/pentester/go/bin/* /usr/local/bin/ 2>/dev/null || true

RUN pip3 install --break-system-packages --ignore-installed 'pipx==1.7.1'

USER pentester
ENV PIPX_HOME=/home/pentester/.local/pipx \
    PIPX_BIN_DIR=/home/pentester/.local/bin
RUN pipx install arjun \
 && pipx install dirsearch && pipx inject dirsearch setuptools \
 && pipx install wafw00f

USER root
RUN ln -sf /home/pentester/.local/bin/arjun     /usr/local/bin/arjun \
 && ln -sf /home/pentester/.local/bin/dirsearch /usr/local/bin/dirsearch \
 && ln -sf /home/pentester/.local/bin/wafw00f   /usr/local/bin/wafw00f

USER root
RUN for i in 1 2 3 4 5; do curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && break || { echo "[retry $i/5] nodesource setup"; sleep 10; }; done \
 && for i in 1 2 3 4 5; do apt-get update && break || { echo "[retry $i/5] apt-get update"; sleep 10; }; done \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g retire@latest js-beautify@latest 2>&1 | tail -5

USER root
RUN set -eux; \
    git clone --depth 1 https://github.com/betterleaks/betterleaks.git /tmp/betterleaks \
 && cd /tmp/betterleaks \
 && make build \
 && install -m 0755 betterleaks /usr/local/bin/betterleaks \
 && cd / && rm -rf /tmp/betterleaks \
 || echo "[warn] betterleaks build failed — gitleaks+trufflehog still cover most patterns"

USER pentester
RUN nuclei -update-templates 2>/dev/null || echo "[warn] nuclei templates update failed"
RUN python3 -m camoufox fetch 2>/dev/null || echo "[warn] camoufox fetch failed (works offline later)"

# Suppress GNU Parallel citation notice (blocks first-run parallel invocations)
RUN mkdir -p /home/pentester/.parallel && touch /home/pentester/.parallel/will-cite

USER root
RUN mkdir -p /workspace && chown pentester:pentester /workspace

USER pentester
WORKDIR /workspace

CMD ["sleep", "infinity"]
