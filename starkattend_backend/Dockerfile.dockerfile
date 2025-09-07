# Use a specific, stable version of Python for reliability
FROM python:3.12.2-slim-bookworm

# Set an environment variable to prevent prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    --no-install-recommends

# Install a specific, stable version of Google Chrome
RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_124.0.6367.60-1_amd64.deb \
    && apt-get install -y ./google-chrome-stable_124.0.6367.60-1_amd64.deb \
    && rm google-chrome-stable_124.0.6367.60-1_amd64.deb

# Install the corresponding version of ChromeDriver and move it to a standard PATH location
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/124.0.6367.60/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && rm chromedriver-linux64.zip \
    && rm -rf chromedriver-linux64

# Set the working directory
WORKDIR /app

# Copy and install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port Gunicorn will run on
EXPOSE 10000

# Run the application. Gunicorn will start the 'application' object from the 'starkattend_api' file.
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "starkattend_api:application"]


