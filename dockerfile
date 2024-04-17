FROM python:3.10

WORKDIR /

COPY lfg.py ./
COPY loabot_db.py ./
COPY loabot_modals.py ./
COPY loabot_views.py ./
COPY exception_handling.py ./
COPY loabot_logger.py ./
COPY cogs/ ./cogs
COPY utils/ ./utils
#COPY .env ./
COPY requirements.txt ./
RUN mkdir /data
RUN mkdir /ressources
#ADD /data/ ./data/
#ADD /ressources/ ./ressources/
RUN pip install -r requirements.txt

CMD ["python", "./lfg.py"]