#!/bin/sh
# Runs inside the benchmark image; host driver supplies mounts and captures stdout.
set -eu
mkdir -p /results/env/source/juge
cp -R /juge/benchmarktool/src /juge/benchmarktool/pom.xml /results/env/source/juge/
# Use the published engine, independent of uncommitted engine source changes.
mkdir -p /results/downloads /results/env
if [ -f /results/maze-package.tar.gz ]; then
    python3 - <<'PACKAGE'
import json, tarfile, hashlib
from pathlib import Path
archive = Path('/results/maze-package.tar.gz')
meta = json.loads(Path('/results/maze-package.json').read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest() == meta['sha256']
with tarfile.open(archive) as tar:
    names = tar.getnames()
    tops = {n.split('/')[0] for n in names}
    assert len(tops) == 1
    top = tops.pop()
    for m in tar.getmembers():
        assert not m.name.startswith('/') and '..' not in Path(m.name).parts
        assert m.isfile() or m.isdir(), 'Links/devices are not accepted in engine archives'
    tar.extractall('/results/env')
Path('/results/env', top).rename('/results/env/maze')
assert Path('/results/env/maze/architecture').read_text().strip() == 'amd64'
Path('/results/env/maze-release.json').write_text(json.dumps(meta))
PACKAGE
else
release=maze-1.2.3-linux-amd64
release_sha256=8cec2a7d6e6d71fa9006a9fd664c96d0f0dfa34437c3d814cd7fbe7ea476af86
release_url=https://github.com/ThijnK/maze/releases/download/v1.2.3/$release.tar.gz
mkdir -p /results/downloads /results/env
curl --fail --location --retry 3 "$release_url" -o "/results/downloads/$release.tar.gz"
printf '%s  %s\n' "$release_sha256" "/results/downloads/$release.tar.gz" | sha256sum -c -
tar -xzf "/results/downloads/$release.tar.gz" -C /results/env
mv "/results/env/$release" /results/env/maze
maze_version=$(/results/env/maze/maze --version)
printf 'MAZE package version: %s\n' "$maze_version"
test "$maze_version" = 'maze 1.2.3'
printf '{"version":"1.2.3","url":"%s","sha256":"%s"}\n' "$release_url" "$release_sha256" > /results/env/maze-release.json
fi
mkdir -p /results/build-source
cp /juge/pom.xml /juge/checkstyle.xml /results/build-source/
cp -R /juge/runtool /juge/benchmarktool /juge/maze_runtool /results/build-source/
mkdir -p /results/build-source/tools
cp -R /juge/tools/maze /results/build-source/tools/
cd /results/build-source
mvn -B -ntp -N -DskipTests install
mvn -B -ntp -f runtool/pom.xml -DskipTests install
mvn -B -ntp -f benchmarktool/pom.xml -DskipTests package
mkdir -p /results/env/maze/lib /results/env/tool/lib /results/env/lib /results/env/subjects/src /results/env/subjects/classes
MAZE_HOME=/results/env/maze sh tools/maze/build-adapter.sh
cp tools/maze/runtool /results/env/tool/
cp tools/maze/lib/maze-adapter.jar /results/env/tool/lib/
cp benchmarktool/target/benchmarktool-1.0.0-shaded.jar /results/env/lib/runner.jar
cp /juge/infrastructure/lib/junit-4.12.jar /juge/infrastructure/lib/hamcrest-core-1.3.jar /juge/infrastructure/lib/jacocoagent.jar /juge/infrastructure/lib/pitest-1.1.11.jar /juge/infrastructure/lib/pitest-command-line-1.1.11.jar /results/env/lib/
cp /juge/infrastructure/scripts/maze_validate_generation.py /results/env/
cp /results/suite/subjects/*.java /results/env/subjects/src/
/opt/java8/bin/javac -g -d /results/env/subjects/classes /results/env/subjects/src/*.java
mkdir -p /results/env/characteristics
/opt/java8/bin/javac -cp /results/env/lib/runner.jar -d /results/env/characteristics /results/suite/SubjectMetrics.java
/opt/java8/bin/java -cp /results/env/lib/runner.jar:/results/env/characteristics SubjectMetrics /results/env/subjects/classes /results/env/subjects/src > /results/env/subject-characteristics.csv
python3 - <<'PY'
import json, platform, subprocess, zipfile
from pathlib import Path
v = {'architecture': platform.machine(), 'platform': platform.platform()}
v['maze_release'] = json.loads(Path('/results/env/maze-release.json').read_text())
v['maze_version'] = subprocess.check_output(['/results/env/maze/maze', '--version'], cwd='/results', text=True).strip()
for name, cmd in {'java21': ['java', '-version'], 'java8': ['/opt/java8/bin/java', '-version'], 'maven': ['mvn', '-version'], 'python': ['python3', '--version'], 'scipy': ['python3', '-c', 'import scipy; print(scipy.__version__)']}.items():
    v[name] = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
v.update(pit='1.1.11; default mutators; allMutants=true', metric='JUGE JaCoCo conditionsCovered/conditionsTotal')
with zipfile.ZipFile('/results/env/lib/runner.jar') as jar:
    v['jacoco_core'] = jar.read('META-INF/maven/org.jacoco/org.jacoco.core/pom.properties').decode()
Path('/results/env/versions.json').write_text(json.dumps(v, indent=2) + '\n')
PY
cd /results
rm -rf /results/build-source
