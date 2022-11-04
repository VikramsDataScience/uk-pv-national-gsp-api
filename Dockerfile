FROM python:3.10-slim-bullseye

# copy files requirements
COPY ./requirements.txt /app/requirements.txt

# install requirements
RUN apt-get update -y
RUN #apt-get install -y gdal-bin libgdal-dev g++
RUN pip install -U pip
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y git
RUN pip install git+https://github.com/SheffieldSolar/PV_Live-API#pvlive_api

# set working directory
WORKDIR /app

# copy files over
COPY ./src /app/src
COPY ./script /app/script

# make sure 'src' is in python path - this is so imports work
ENV PYTHONPATH=${PYTHONPATH}:/app/src
