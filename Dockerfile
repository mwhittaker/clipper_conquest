# The Clipper Conquest game server, with the game app it serves. From the repo's top folder:
#   docker build -t clipper-conquest .
#   docker run -p 8080:8080 -v "$PWD/game-data:/data" clipper-conquest
# (or just: docker compose up -d --build)
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 TZ=America/Los_Angeles CLIPPER_DATA=/data
WORKDIR /app
COPY server.py app.html app.js mobile.js mobile.css replay-core.js challenges.json \
     sf_neighborhoods.geojson /app/
VOLUME /data
EXPOSE 8080
# PORT is honored too, as Cloud Run and similar hosts set it
CMD ["python3", "/app/server.py"]
