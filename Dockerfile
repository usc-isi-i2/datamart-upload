# Base docker images contains d3m core and common primitives from Summer 2019 evaluation
# FROM registry.datadrivendiscovery.org/jpl/docker_images/complete:ubuntu-bionic-python36-v2019.6.7-20190622-073225
FROM registry.gitlab.com/datadrivendiscovery/images/primitives:ubuntu-bionic-python36-v2019.11.10

WORKDIR /app

RUN git clone https://github.com/usc-isi-i2/dsbox-primitives.git && cd dsbox-primitives && git checkout bf6723b102704657116f48d240538fab1a3ce18e && pip install -e .

# RUN git clone https://github.com/usc-isi-i2/datamart-userend.git && cd datamart-userend && git checkout 2b4cffe8c962c1b9f65fd7bf3a8dc431117a4383 && pip install -e .
RUN git clone https://github.com/usc-isi-i2/datamart-userend.git && cd datamart-userend && git checkout 92521e2a55608206b3e880aa51344930191e89b2 && pip install -e .

# RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && git checkout cdd4aa236ebfeb288b26b504a1dee626f2028edd && pip install -e .
# RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && git checkout be374b12a9ac659a3d13b9b655f002b79f1b1f80 && pip install -e .
RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && git checkout 403be4e1bd7bc76c1f2d193e59e797b14f7fba70 && pip install -e .

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
