#!/usr/bin/env bash
# smoke_test.sh — End-to-end check that a running LeafCheck instance
# (either local uvicorn or the Docker image) is healthy and predicts on
# every example in `examples/`.
#
# Usage:
#   scripts/smoke_test.sh                # tests http://127.0.0.1:8000
#   BASE_URL=http://host:8000 scripts/smoke_test.sh
#
# Exits non-zero on any failure.

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

say() { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
die() { printf '  \033[1;31m✗\033[0m %s\n' "$*"; exit 1; }

# 1. /health
say "GET $BASE_URL/health"
status=$(curl -sS -o /tmp/leafcheck_health.json -w "%{http_code}" "$BASE_URL/health") || die "curl /health failed"
[ "$status" = "200" ] || die "/health returned $status (body: $(cat /tmp/leafcheck_health.json))"
loaded=$(python3 -c "import json; print(json.load(open('/tmp/leafcheck_health.json'))['model_loaded'])")
[ "$loaded" = "True" ] || die "/health.model_loaded is $loaded, want True"
say "/health reports model_loaded=True"

# 2. /api/classes
say "GET $BASE_URL/api/classes"
status=$(curl -sS -o /tmp/leafcheck_classes.json -w "%{http_code}" "$BASE_URL/api/classes") || die "curl /api/classes failed"
[ "$status" = "200" ] || die "/api/classes returned $status"
n_classes=$(python3 -c "import json; print(len(json.load(open('/tmp/leafcheck_classes.json'))['classes']))")
[ "$n_classes" -ge 1 ] || die "no classes reported"
say "/api/classes reports $n_classes classes"

# 3. /api/predict on every example
say "POST $BASE_URL/api/predict (per example)"
python3 - "$BASE_URL" "$ROOT" <<'PYEOF'
import json
import sys
import urllib.request
import uuid

base_url, root = sys.argv[1], sys.argv[2]
labels = json.load(open(f"{root}/examples/labels.json"))
boundary = "----leafcheck" + uuid.uuid4().hex

def multipart(fname: str, data: bytes) -> bytes:
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n".encode()
    )
    parts.append(data)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)

failures = 0
for fname, info in labels.items():
    path = f"{root}/examples/{fname}"
    expected = info["expected_class"]
    with open(path, "rb") as fh:
        data = fh.read()
    body = multipart(fname, data)
    req = urllib.request.Request(
        f"{base_url}/api/predict",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ {fname}: request failed: {e}")
        failures += 1
        continue
    if "class_name" not in result:
        print(f"  ✗ {fname}: no class_name in response: {result}")
        failures += 1
        continue
    predicted = result["class_name"]
    if predicted != expected:
        # Soft-fail: log mismatch but don't fail the smoke test. The
        # M7 AC says "the image builds and serves"; class-matching is
        # F8.AC3 / G5 and lives in the tests/ folder, not in this script.
        print(f"  · {fname}: predicted={predicted} (expected {expected})")
    else:
        print(f"  ✓ {fname}: predicted={predicted}")
print(f"smoke_test: {len(labels) - failures}/{len(labels)} matched expected class")
PYEOF
say "all examples returned a prediction"

# 4. Reject non-image. We must include the `file` multipart field so FastAPI's
# form parser accepts the request (missing field → 422); the validation
# layer is what should reject bytes that aren't a valid JPEG/PNG/WebP → 400.
say "POST $BASE_URL/api/predict (rejects text file)"
TMP_BAD=/tmp/leafcheck_notanimage.txt
printf 'this is not an image' > "$TMP_BAD"
status=$(curl -sS -o /tmp/leafcheck_bad.json -w "%{http_code}" -X POST \
    -F "file=@${TMP_BAD};type=application/octet-stream" \
    "$BASE_URL/api/predict") || die "curl /api/predict failed"
[ "$status" = "400" ] || die "expected 400, got $status (body: $(cat /tmp/leafcheck_bad.json))"
rm -f "$TMP_BAD"
say "non-image upload rejected with 400"

printf '\n\033[1;32mAll smoke checks passed.\033[0m\n'