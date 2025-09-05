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
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

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

# Run the application. Selenium will now find Chrome automatically.
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "starkattend_api:application"]
