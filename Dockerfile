FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY . /app
COPY override/timeout.conf /etc/nginx/conf.d/timeout.conf
COPY override/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN mkdir -p /home/nginx/.cloudvolume/secrets \
  \
  && chown -R nginx /home/nginx \
  && usermod -d /home/nginx -s /bin/bash nginx \
  \
  # Add graph-tool repository
  && apt-get update \
  && apt-get install -y lsb-release \
  && export GRAPH_TOOL_REPO="$(lsb_release -c -s)" \
  && echo "deb http://downloads.skewed.de/apt/$GRAPH_TOOL_REPO $GRAPH_TOOL_REPO main" | tee -a /etc/apt/sources.list.d/graph-tool.list \
  && echo "deb-src http://downloads.skewed.de/apt/$GRAPH_TOOL_REPO $GRAPH_TOOL_REPO main" | tee -a /etc/apt/sources.list.d/graph-tool.list \
  && apt-key adv --keyserver pgp.skewed.de --recv-key 612DEFB798507F25 \
  && apt-get update \
  && apt-get install -y python3-graph-tool \
  # Graph tool will install itself to dist-packages, not site-packages
  && echo "/usr/lib/python3/dist-packages/" | tee -a /usr/local/lib/python3.6/site-packages/dist-packages.pth \
  \
  # Need boost and g++ for igneous meshing
  && apt-get install -y build-essential libboost-dev \
  \
  # Need numpy to prevent install issue with cloud-volume/fpzip
  && pip install --no-cache-dir --upgrade numpy \
  # PyChunkedGraph
  && pip install --no-cache-dir --upgrade --process-dependency-links -e . \
  # Cleanup
  && apt-get remove -y build-essential libboost-dev lsb-release \
  && rm -rf /var/lib/apt/lists/*
