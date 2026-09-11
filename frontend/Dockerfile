FROM nginx:alpine

COPY certs/ /usr/local/share/ca-certificates/extra/
RUN if find /usr/local/share/ca-certificates/extra -name '*.crt' 2>/dev/null | grep -q .; then \
      HAS_CA=1; \
      cp /etc/apk/repositories /etc/apk/repositories.bak && \
      sed -i 's/https:\/\//http:\/\//g' /etc/apk/repositories && \
      apk add --no-cache ca-certificates && \
      cat /usr/local/share/ca-certificates/extra/*.crt >> /etc/ssl/certs/ca-certificates.crt && \
      update-ca-certificates && \
      mv /etc/apk/repositories.bak /etc/apk/repositories; \
    fi

COPY public/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1
