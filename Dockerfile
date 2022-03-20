FROM python:latest
RUN mkdir /app
WORKDIR /app
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
ENV PYTHONUNBUFFERED 1
COPY ./bot.py .
COPY ./vpns.py .
COPY ./run.sh .
CMD [ "sh", "run.sh" ]