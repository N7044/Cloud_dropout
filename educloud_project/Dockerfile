# Use a lightweight Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install dependencies
# NOTE: the build context is the REPOSITORY ROOT (this is how Openship builds),
# so every COPY source is prefixed with the project subdirectory. Build locally
# the same way: `docker build -f educloud_project/Dockerfile .` from the repo root.
COPY educloud_project/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY educloud_project/ .

# Expose port 8000
EXPOSE 8000

# Run the Django app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "educloud_project.wsgi:application"]
