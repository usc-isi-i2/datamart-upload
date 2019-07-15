# Install

Please follow the order of installation here, otherwise it may failed:
1.1. Clone and install` d3m` package from [Here](https://gitlab.com/datadrivendiscovery/d3m "link title")

2.1. Clone and install `common-primitives` package from [Here](https://gitlab.com/datadrivendiscovery/common-primitives "link title")
2.2. If you are using MacOS, please go to the common-primitives package and edit the setup.py file: rename the dependency of `tensorflow-gpu` to `tensorflow`.

3.1. Clone and install `dsbox-primitives` from  [Here](https://github.com/usc-isi-i2/dsbox-primitives "link title")

4.1 Clone and install `datamart-userend` from  [Here](https://github.com/usc-isi-i2/datamart-userend "link title")

5.1  Run `pip install -r requirements.txt` to install remained requirement packages.
5.2 Run `pip install -e .` to install datamart upload package.

6.1 Run `python -m spacy download en_core_web_sm` to install spacy dependency.
6.2 Ask the maintainer to send you the `config.py` fil: to get uploading password and store it into the `your_path_to_python3.6/site-packages/wikifier/`
6.3 Try to run `python webapp-openapi.py` to see if it works or not.

7.1 If everything OK, you can now open a browser and go to the REST API page on `127.0.0.1:9000`.

7.2 If you prefer to run with python api, refer to the example codes [Here](https://github.com/usc-isi-i2/datamart-upload/tree/d3m/examples)
