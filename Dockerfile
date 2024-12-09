# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv for faster package installation
RUN pip install uv

# Copy requirements files
COPY requirements.txt requirements.lock ./

# Install dependencies using uv
RUN uv pip install --system -r requirements.lock

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "main.py"] 