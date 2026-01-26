# FROM python:3.11

# WORKDIR /app

# # Copy entire backend folder
# COPY . /app

# RUN pip install --upgrade pip
# RUN pip install -r requirements.txt

# CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
FROM python:3.11

WORKDIR /app

# Copy only requirements first (cache this layer)
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Then copy the rest of the app
COPY . .

CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
