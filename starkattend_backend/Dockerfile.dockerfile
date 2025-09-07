FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required by OpenCV, Pillow, Selenium, and Chrome
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libu2f-udev \
    wget \
    unzip \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Copy dependency list
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose the app port
EXPOSE 10000

# Run the app with Gunicorn
CMD ["gunicorn", "--workers=4", "--threads=4", "--timeout=120", "--bind", "0.0.0.0:10000", "app:application"]






