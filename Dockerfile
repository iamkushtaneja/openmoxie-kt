## Moxie needs MQTT and services running on MQTT
# Use an official Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app
COPY deepgram_client.py /app/site/hive/mqtt/deepgram_client.py
RUN echo "✅ deepgram_client.py copied" && ls -l /app/site/hive/mqtt/

COPY zmq_stt_handler.py /app/site/hive/mqtt/zmq_stt_handler.py
RUN echo "Files in /app/site/hive/mqtt:" && ls -l /app/site/hive/mqtt/

# PIP for installing python dep
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libsndfile1

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install aiohttp

# Create a volume for persistent data
VOLUME /app/site/work

# Expose the Mosquitto MQTT port and Django development server port
EXPOSE 8000

# Run Django development server
# - Does data migrations and ensure stock data available, then runs the service
CMD ["bash", "-c", "python3 site/manage.py makemigrations && python3 site/manage.py migrate && python3 site/manage.py init_data && python3 site/manage.py runserver --noreload 0.0.0.0:8000"]


RUN echo "CHECKPOINT: Listing /app/site/hive/mqtt during build" && ls -al /app/site/hive/mqtt/

