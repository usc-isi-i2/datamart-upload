# Base docker images contains d3m core and common primitives from Summer 2019 evaluation
FROM registry.datadrivendiscovery.org/jpl/docker_images/complete:ubuntu-bionic-python36-v2019.6.7-20190622-073225

WORKDIR /app

RUN git clone https://github.com/usc-isi-i2/dsbox-primitives.git && cd dsbox-primitives && git checkout e13beaff175171a5f4d0b9aafb69f8c2159470b3 && pip install -e .

# RUN git clone https://github.com/usc-isi-i2/datamart-userend.git && cd datamart-userend && git checkout a383ee510001a31de414dbf62d52112a8ffb995e && pip install -e .
RUN git clone https://github.com/usc-isi-i2/datamart-userend.git && cd datamart-userend && git checkout cde86029048c214adf8d07345228f9947b46d9b7 && pip install -e .

# RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && git checkout 9a6842930042eed752cd161c32d48d5d9b3df37b && pip install -e .
RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && git checkout 2308323603a68691bcc7068866fbe2e99374feec && pip install -e .

RUN pip3 install rq==1.1.0
RUN pip3 install bcrypt>=3.1.7
RUN pip3 install gunicorn>=19.9.0

RUN python3 -m spacy download en_core_web_sm

WORKDIR /app/datamart-upload/datamart_web

# COPY datasets-2019-summer/seed_datasets_data_augmentation /data

CMD ["python3", "webapp-openapi.py"]
