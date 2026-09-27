#!/bin/sh
# Runs inside the benchmark image; host driver supplies mounts and captures stdout.
set -eu
mkdir -p /results/env/source/juge
cp -R /juge/benchmarktool/src /juge/benchmarktool/pom.xml /results/env/source/juge/
# Use the published engine, independent of uncommitted engine source changes.
release=maze-1.2.2-linux-amd64
release_sha256=75582c006c965677968de303c774e437f72176b1aacf8925e528ce07e47b24f4
release_url=https://github.com/ThijnK/maze/releases/download/v1.2.2/$release.tar.gz
mkdir -p /results/downloads /results/env
curl --fail --location --retry 3 "$release_url" -o "/results/downloads/$release.tar.gz"
printf '%s  %s\n' "$release_sha256" "/results/downloads/$release.tar.gz" | sha256sum -c -
tar -xzf "/results/downloads/$release.tar.gz" -C /results/env
mv "/results/env/$release" /results/env/maze
test "$(/results/env/maze/maze --version)" = 'maze 1.2.2'
printf '{"version":"1.2.2","url":"%s","sha256":"%s"}\n' "$release_url" "$release_sha256" > /results/env/maze-release.json
cd /juge
mvn -B -ntp -N -DskipTests install
mvn -B -ntp -f runtool/pom.xml -DskipTests install
mvn -B -ntp -f benchmarktool/pom.xml -DskipTests package
mkdir -p /results/env/maze/lib /results/env/tool/lib /results/env/lib /results/env/subjects/src /results/env/subjects/classes
MAZE_HOME=/results/env/maze sh tools/maze/build-adapter.sh
cp tools/maze/runtool /results/env/tool/
cp tools/maze/lib/maze-adapter.jar /results/env/tool/lib/
cp benchmarktool/target/benchmarktool-1.0.0-shaded.jar /results/env/lib/runner.jar
cp infrastructure/lib/junit-4.12.jar infrastructure/lib/hamcrest-core-1.3.jar infrastructure/lib/jacocoagent.jar infrastructure/lib/pitest-1.1.11.jar infrastructure/lib/pitest-command-line-1.1.11.jar /results/env/lib/
cp infrastructure/scripts/maze_validate_generation.py /results/env/
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
for name, cmd in {'java21': ['java', '-version'], 'java8': ['/opt/java8/bin/java', '-version'], 'maven': ['mvn', '-version'], 'python': ['python3', '--version'], 'scipy': ['python3', '-c', 'import scipy; print(scipy.__version__)']}.items():
    v[name] = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
v.update(pit='1.1.11; default mutators; allMutants=true', metric='JUGE JaCoCo conditionsCovered/conditionsTotal')
with zipfile.ZipFile('/results/env/lib/runner.jar') as jar:
    v['jacoco_core'] = jar.read('META-INF/maven/org.jacoco/org.jacoco.core/pom.properties').decode()
Path('/results/env/versions.json').write_text(json.dumps(v, indent=2) + '\n')
PY
