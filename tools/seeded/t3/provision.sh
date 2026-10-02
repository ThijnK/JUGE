#!/bin/sh
# Build the pinned author source in the existing benchmark image. Downloads stay
# outside the repository's tracked files; the final runner has no network needs.
set -eu
adapter_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
out=${1:?Usage: provision.sh /absolute/output-directory}
case "$out" in /*) ;; *) echo 'Output path must be absolute' >&2; exit 2 ;; esac
image=${AST2027_BUILD_IMAGE:-maze-ast2027:amd64}
build="$out.build"
mkdir -p "$out/lib" "$out/classes" "$build/source"
curl -fL --retry 3 'https://git.science.uu.nl/api/v4/projects/prase101%2Ft3/repository/archive.tar.gz?sha=a12cf1a3b1b7149566cf6dbb80e43eabdbb70041' -o "$build/source.tar.gz"
"${JUGE_PROVISION_PYTHON:-python3}" - "$build/source.tar.gz" <<'PY'
import hashlib, pathlib, sys
if hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() != 'b8bbd2ff84124933cfc2decb51449de7b7ac7c3c040c509d44fece965c2b226e':
    raise SystemExit('T3 source checksum mismatch')
PY
tar -xzf "$build/source.tar.gz" -C "$build/source" --strip-components=1
cache=${AST2027_MAVEN_CACHE:-$build/maven}
mkdir -p "$cache"
docker run --platform linux/amd64 --rm --user="$(id -u):$(id -g)" -e HOME=/tmp -e MAVEN_CONFIG=/tmp/.m2 --cpus=2 --memory=2g \
    -v "$build/source:/source" -v "$out:/output" -v "$adapter_dir:/adapter:ro" \
    -v "$cache:/maven" -w /source "$image" sh -c '
    mvn -B -ntp -Dmaven.repo.local=/maven -DskipTests -Dmaven.compiler.release=8 -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8 clean package dependency:copy-dependencies -DoutputDirectory=target/lib &&
    cp target/t3-3.0.1-SNAPSHOT.jar target/lib/*.jar /output/lib/ &&
    /opt/java8/bin/javac -cp "/output/lib/*" -d /output/classes /adapter/SeededT3.java'
cp "$adapter_dir/runtool" "$out/runtool"
cp "$adapter_dir/../generation.py" "$out/generation.py"
chmod +x "$out/runtool"
printf '%s\n' '3.0.1-SNAPSHOT-a12cf1a3-java8-api-seeded' > "$out/VERSION.txt"
