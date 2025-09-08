FROM python:3.12-slim

WORKDIR /app

# Install critical system dependencies required for OpenCV to function
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 --no-install-recommends

# Copy the component manifest
COPY requirements.txt .

# Install all required Python libraries, including the AI and image processing components
RUN pip install --no-cache-dir -r requirements.txt

# Copy your definitive engine schematic
COPY . .

# Expose the port the engine will run on
EXPOSE 10000

# The definitive ignition sequence for your engine
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:application"]







