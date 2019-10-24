# Base docker images contains d3m core and common primitives from Summer 2019 evaluation
FROM registry.datadrivendiscovery.org/jpl/docker_images/complete:ubuntu-bionic-python36-v2019.6.7-20190622-073225

WORKDIR /app

RUN git clone https://github.com/usc-isi-i2/dsbox-primitives.git && cd dsbox-primitives && git checkout bf6723b102704657116f48d240538fab1a3ce18e && pip install -e .

RUN git clone https://github.com/usc-isi-i2/datamart-userend.git && cd datamart-userend && git checkout 80f75ef6300261753c6d2447b6f50448cb90d528 && pip install -e .

RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && git checkout 161ee2717eef396697e5ce89e41d5361fe73b7cd && pip install -e .

RUN pip3 install rq==1.1.0
RUN pip3 install bcrypt>=3.1.7
RUN pip3 install gunicorn>=19.9.0

RUN git clone https://github.com/RDFLib/OWL-RL.git && cd OWL-RL && git checkout 471d1dfe8f6ed710b99395d3a563c3c4218cf46a && git checkout e98d23297216ad81c9a9982d861162bd2388600b && pip install -e .

RUN python3 -m spacy download en_core_web_sm

WORKDIR /root/memcache_storage/other_cache
COPY config/wikifier/wikifier_choice.json .

WORKDIR /app/datamart-upload

# CMD ["python3", "webapp-openapi.py"]
CMD ["/bin/sh", "start-datamart.sh"]
