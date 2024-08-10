#!/bin/bash

# Se não for ambiente de desenvolvimento, baixar projeto do github
if [ -e "${DEV}" ] || [ "${DEV}" != "true" ]; then
  git clone https://github.com/gustavofl/gerador_malhas_web.git
fi

chmod +x /data/gerador_malhas_web/run.sh
/data/gerador_malhas_web/run.sh