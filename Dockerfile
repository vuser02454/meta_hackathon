FROM python:3.11-slim

WORKDIR /app

# The build context is assumed to be the root of the project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from root into /app
COPY . .

EXPOSE 7860

# Adjust uvicorn to find server.app now that paths have changed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
