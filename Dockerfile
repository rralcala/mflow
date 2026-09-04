FROM python:3.14-slim

# Set the working directory inside the container
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

RUN groupadd --gid 1000 ubuntu \
    && useradd --uid 1000 --gid 1000 -m ubuntu

USER ubuntu

EXPOSE 5001
# Define the command to run your Python application
CMD ["python", "service.py", "--base", "/data/"]