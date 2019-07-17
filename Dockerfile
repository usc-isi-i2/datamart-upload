
FROM python:3.6.9

WORKDIR /app

RUN mkdir github
RUN cd github

RUN python3 -m venv datamart_env
RUN /bin/bash -c "source datamart_env/bin/activate"
RUN pip install --upgrade pip


RUN git clone https://gitlab.com/datadrivendiscovery/d3m.git && cd d3m && git checkout v2019.6.7 && pip install -e .
RUN cd ..

RUN git clone https://gitlab.com/datadrivendiscovery/common-primitives.git && cd common-primitives && pip install -e .
RUN cd ..

RUN git clone https://github.com/usc-isi-i2/dsbox-primitives.git && cd dsbox-primitives && pip install -e .
RUN cd ..

RUN git clone https://github.com/usc-isi-i2/datamart-userend.git && cd datamart-userend && pip install -e .
RUN cd ..

RUN git clone https://github.com/usc-isi-i2/datamart-upload.git && cd datamart-upload && pip install -e .

RUN python -m spacy download en
WORKDIR /app/datamart-upload/datamart_web
CMD python3 webapp-openapi.py
