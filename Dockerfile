# Docker image for the PDF comparison pipeline
FROM python:3.10-slim

WORKDIR /app/pdf_compare_dev

# Optional: fonts and GL libs for image/PDF rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libglib2.0-0 \
      libgl1 \
      fonts-dejavu-core && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/pdf_compare_dev/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/pdf_compare_dev

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
