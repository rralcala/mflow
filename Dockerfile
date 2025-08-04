FROM python:3.14-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

EXPOSE 5000
# Define the command to run your Python application
CMD ["python", "service.py", "--base", "/data/"]