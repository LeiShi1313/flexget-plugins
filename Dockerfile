FROM python
ENV PYTHONUNBUFFERED 1

RUN \
    echo "**** install build packages ****" && \
    apt-get update && \
    apt-get install -y gcc git

WORKDIR /wheels
RUN pip install -U pip && \
    pip wheel flexget && \
    pip wheel 'transmission-rpc>=3.0.0,<4.0.0' && \
    pip wheel python-telegram-bot==12.8 && \
    pip wheel chardet && \
    pip wheel baidu-aip && \
    pip wheel pillow && \
    pip wheel pandas && \
    pip wheel matplotlib && \
    pip wheel fuzzywuzzy && \
    pip wheel python-Levenshtein && \
    pip wheel pyppeteer && \
    pip wheel pyppeteer_stealth && \
    pip wheel deluge-client && \
    pip wheel autoremove-torrents


FROM python
LABEL maintainer="madwind.cn@gmail.com" \
      org.label-schema.name="flexget"
ENV PYTHONUNBUFFERED 1

COPY --from=0 /wheels /wheels
COPY root/ /

RUN \
    echo "**** install runtime packages ****" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
                    ca-certificates \
                    libx11-xcb1 \
                    libxcomposite1 \
                    libxcursor1 \
                    libxdamage1 \
                    libxi6 \
                    libxtst6 \
                    libnss3 \
                    libcups2 \
                    libxrandr2 \
                    libasound2 \
                    libatk1.0-0 \
                    libatk-bridge2.0-0 \
                    libgtk-3-0
RUN \
    pip install -U pip && \
    pip install --no-cache-dir \
                --no-index \
                -f /wheels \
                flexget \
                'transmission-rpc>=3.0.0,<4.0.0' \
                python-telegram-bot==12.8 \
                chardet \
                baidu-aip \
                pillow \
                pandas \
                matplotlib \
                fuzzywuzzy \
                python-Levenshtein \
                pyppeteer \
                pyppeteer_stealth \
                deluge-client \
                autoremove-torrents
RUN \
    echo "**** create flexget user and make our folders ****" && \
    mkdir /home/flexget && \
    groupmod -g 1000 users && \
    useradd -u 911 -U -d /home/flexget -s /bin/sh flexget && \
    usermod -G users flexget && \
    chown -R flexget:flexget /home/flexget && \
    su flexget -c "pyppeteer-install" && \
    chmod +x /usr/bin/entrypoint.sh && \
    rm -rf /wheels \
           /var/lib/apt/lists/*

# add default volumes
VOLUME /config /downloads
WORKDIR /config

RUN \
  mkdir -p /config/plugins && \
  SITE=$(python -c 'import site; print(site.getsitepackages()[0])') && \
  git clone https://github.com/madwind/flexget_qbittorrent_mod.git && \
  cp -r flexget_qbittorrent_mod/* $SITE/flexget/plugins && \
  git clone https://github.com/Juszoe/flexget-nexusphp.git && \
  cp -r flexget-nexusphp/* $SITE/flexget/plugins && \
  git clone https://github.com/LeiShi1313/flexget-plugins.git && \
  cp -r flexget-plugins/* $SITE/flexget/plugins && \
  rm -r flexget_qbittorrent_mod flexget-nexusphp flexget-plugins

# expose port for flexget webui
EXPOSE 3539 3539/tcp

ENTRYPOINT ["sh","-c","/usr/bin/entrypoint.sh"]
