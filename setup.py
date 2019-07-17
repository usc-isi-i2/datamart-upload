from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    install_requires = list()
    dependency_links = list()
    for line in f:
        re = line.strip()
        if re:
            install_requires.append(re)

setup(name='datamart_isi',
      version='2.0.dev3',
      description='USC ISI implementation of D3M Datamart API',
      author='USC ISI',
      url='https://github.com/usc-isi-i2/datamart-userend/tree/d3m',
      packages=find_packages(),

      install_requires=install_requires,
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
      ])