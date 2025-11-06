FROM python:3.12.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install any necessary dependencies
RUN apt-get update

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the Python packages listed in requirements.txt
RUN pip install -r requirements.txt

# Copy the application code to the working directory
COPY . .

# Set Flask environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 5001

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]