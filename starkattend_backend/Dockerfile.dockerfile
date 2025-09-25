# Use a specific, stable version of Python for reliability
FROM python:3.12-slim

# Set an environment variable to prevent prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory inside the container
WORKDIR /app

# Install critical system dependencies required for OpenCV to function
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 --no-install-recommends

# Copy the component manifest (your requirements.txt)
COPY requirements.txt .

# Install all required Python libraries, including gunicorn and the AI components
RUN pip install --no-cache-dir -r requirements.txt

# Copy your definitive engine schematic (app.py)
COPY . .

# Expose the port the engine will run on
EXPOSE 10000

# The definitive ignition sequence for your engine
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
