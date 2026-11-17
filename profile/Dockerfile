#Imagen base ligera de Python (imagen reducida para evitar incluir herramientas y componentes innecesarios)
FROM python:3.12-slim

#Directorio de trabajo dentro del contenedor
WORKDIR /app

#Copiar las dependencias
COPY requirements.txt .

#Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

#Copiar el código del microservicio
COPY /app ./app/
COPY run.py .

#Crear un usuario sin privilegios de administrador
RUN useradd --create-home appuser && chown -R appuser:appuser /app

USER appuser

#Puerto del microservicio
EXPOSE 5002

#Arrancar Flask mediante Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "app:create_app()"]