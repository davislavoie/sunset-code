# Use lightweight Python base image
FROM python:3.10-slim

# Don't cache pip installs to save space
ENV PIP_NO_CACHE_DIR=true

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first (to leverage Docker caching)
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8501

# Run your app when container starts
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
