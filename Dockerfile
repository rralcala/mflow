FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

RUN pip install external/mflow_shared_rralcala-0.0.1-py3-none-any.whl

EXPOSE 50051
# Define the command to run your Python application
CMD ["python", "grpc_server/cash_flow_server.py"]