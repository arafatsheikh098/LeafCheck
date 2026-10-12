# Deploying LeafCheck

LeafCheck is a self-contained Docker image. The intended deployment
topologies are:

1. **Local** — `docker run -p 8000:8000 leafcheck:dev`. For demo and
   field-test use. What `scripts/smoke_test.sh` assumes.
2. **Hugging Face Space (Docker)** — push the image to a Space, the
   `SPACE_README.md` at the repo root is the Space card.
3. **Self-hosted (single-node)** — `docker compose` on a small VPS.
   Suitable for a village-office or NGO deployment.
4. **Behind a reverse proxy** — nginx / Caddy in front, TLS terminated
   there, the container listens on `127.0.0.1` only. Recommended for any
   non-local use.

Out-of-scope topologies (per `SCOPE.md`): GPU serving, kubernetes
horizontal scaling, multi-tenant hosting, anything that requires a
database. None of those are planned.

---

## 1. Local (the README quick-start)

```bash
docker build -t leafcheck:dev .
docker run --rm -p 8000:8000 leafcheck:dev
# Open http://127.0.0.1:8000
```

Verify:

```bash
scripts/smoke_test.sh                # hits http://127.0.0.1:8000
BASE_URL=http://my-host:8000 scripts/smoke_test.sh
```

Expected output: `/health` 200, `/api/classes` returns 19 (or 6 for
the shipped smoke model), 6/6 examples predict (class-matching is
logged but not failed — that's the G5 test, not the smoke test), a
non-image upload is rejected with 400.

## 2. Hugging Face Space (Docker)

LeafCheck is structured to drop into a `docker` Space on HF:

1. Create a new Space, SDK = **Docker**, hardware = **CPU basic**.
2. Add `SPACE_README.md` (this repo) as the Space card. Rename if HF
   requires `README.md` at the Space root.
3. Push the repo's `Dockerfile`, `models/`, `data/`, `static/`,
   `examples/`, `scripts/`, and the application sources. The Space
   builder will run the Dockerfile as-is.
4. Once the Space is `Running`, point your smoke test at the public
   URL: `BASE_URL=https://<user>-<space>.hf.space scripts/smoke_test.sh`.

Note: the shipped `models/` directory includes a small
`model.pt` (5.9 MB). It is **not** the production PlantVillage model
(see `data/DATASET_INFO.md` and `examples/README.md`). A real
deployment should retrain against the full PlantVillage corpus and
replace `models/model.pt` (the API contract is unchanged — only the
contents of `models/class_names.json`, `models/threshold.json`, and
`models/metrics.json` need to stay in sync).

## 3. Self-hosted single-node

`docker compose` is overkill for a single-container service. A systemd
unit is plenty:

```ini
# /etc/systemd/system/leafcheck.service
[Unit]
Description=LeafCheck
After=docker.service
Requires=docker.service

[Service]
Restart=always
ExecStartPre=-/usr/bin/docker rm -f leafcheck
ExecStart=/usr/bin/docker run --rm --name leafcheck \
    -p 127.0.0.1:8000:8000 \
    --read-only \
    --tmpfs /tmp \
    --memory=2g \
    --cpus=2 \
    leafcheck:dev
ExecStop=/usr/bin/docker stop leafcheck

[Install]
WantedBy=multi-user.target
```

The container is `python:3.12-slim` plus CPU-only torch; the `--memory`
and `--cpus` caps in the unit file are conservative defaults for a
shared server. `--read-only` plus `--tmpfs /tmp` means a runaway
request cannot fill the disk.

## 4. Behind a reverse proxy

nginx:

```nginx
server {
    listen 443 ssl;
    server_name leafcheck.example.org;

    ssl_certificate     /etc/letsencrypt/live/leafcheck.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/leafcheck.example.org/privkey.pem;

    client_max_body_size 6m;   # 5 MB upload + multipart envelope

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;     # slow mobile uploads
    }
}
```

Important: `client_max_body_size` must be at least 6 MB (the API
rejects anything > 5 MB, but nginx will 413 anything > 1 MB by
default). `proxy_read_timeout` is generous because a slow mobile
network can take a while to flush a 5 MB upload.

The container should bind to `127.0.0.1` only (`docker run -p
127.0.0.1:8000:8000 ...`), not `0.0.0.0`, so the proxy is the only
way in.

---

## Operational notes

* The Docker `HEALTHCHECK` hits `/health` every 30 s. If the model
  fails to load, `/health` returns `{"status": "degraded", "model_loaded": false}`.
  The container stays up; orchestrators (Docker Compose, systemd) can
  react.
* The `models/` directory is read-only at runtime (the container does
  not write to it). Replacing the model is a `docker rm && docker run`
  cycle.
* No background workers, no scheduled jobs, no queue. The image is a
  pure request/response service.
* The service is **stateless**: no session storage, no database, no
  uploaded-image retention (per F1 OUT-OF-SCOPE: "storing uploaded
  images"). A user can submit the same photo twice and get the same
  result.
* Memory: at idle the container holds ~300 MB of RSS (Python + torch).
  Under load with `batch_size=1` inference, peak is ~700 MB. The
  hard cap suggested above (`--memory=2g`) leaves headroom for OS
  page cache.
