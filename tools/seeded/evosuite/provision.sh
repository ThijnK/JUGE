#!/bin/sh
# Run on the host; output is a self-contained JUGE tool directory.
set -eu
adapter_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=${1:?Usage: provision.sh /absolute/output-directory}
mkdir -p "$out/lib"
for artifact in evosuite-1.2.0 evosuite-standalone-runtime-1.2.0; do
    curl -fL --retry 3 "https://github.com/EvoSuite/evosuite/releases/download/v1.2.0/$artifact.jar" -o "$out/lib/$artifact.jar"
done
"${JUGE_PROVISION_PYTHON:-python3}" - "$out" <<'PY'
import hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
expected = {'evosuite-1.2.0.jar': '0bc0062fdec70c35089ad736c9b88ccf87308c2f0aaaafe43176f3c4a89ddeba',
            'evosuite-standalone-runtime-1.2.0.jar': 'cc856a6d02b391367d2a4516346c699c67e4b4a370203471df1f3d78b46b74dc'}
for name, digest in expected.items():
    actual = hashlib.sha256((root / 'lib' / name).read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit('Checksum mismatch: ' + name)
PY
cp "$adapter_dir/runtool" "$out/runtool"
cp "$adapter_dir/../generation.py" "$out/generation.py"
chmod +x "$out/runtool"
printf '%s\n' 'EvoSuite 1.2.0; algorithm=DYNAMOSA; seed passed with -seed' > "$out/VERSION.txt"
