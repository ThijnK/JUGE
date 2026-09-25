#!/usr/bin/env python3
"""Run real JUGE generation, JaCoCo coverage, PIT mutation analysis, and aggregation."""
import csv
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[2]
HOME = Path(os.environ["MAZE_HOME"])
JAVA8 = Path(os.environ.get("JAVA8_HOME", "/opt/java8"))
M2 = Path(os.environ.get("MAVEN_REPOSITORY", "/root/.m2/repository"))
SCRIPTS = REPO / "infrastructure/scripts"
RUNNER = REPO / "benchmarktool/target/benchmarktool-1.0.0-shaded.jar"
LIBRARIES = {
    "junit": M2 / "junit/junit/4.12/junit-4.12.jar",
    "junit.dependency": M2 / "org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar",
    "jacoco": REPO / "infrastructure/lib/jacocoagent.jar",
}
PIT = [M2 / ("org/pitest/{0}/1.1.11/{0}-1.1.11.jar".format(name))
       for name in ("pitest", "pitest-command-line")]
for required in [JAVA8 / "bin/java", RUNNER, *LIBRARIES.values(), *PIT]:
    if not required.is_file():
        raise SystemExit("Missing pipeline prerequisite: " + str(required))

def verify():
    work = Path(tempfile.mkdtemp(prefix="pipeline-", dir=REPO / "maze_runtool/target"))
    print("Pipeline work directory: " + str(work), flush=True)
    research = work / "research"
    shutil.copytree(HOME / "examples/search-extensions", research)
    source = research / "src/research/DepthSearch.java"
    (source.parent / "Broken.java").write_text(source.read_text().replace("DepthSearch", "Broken")
        .replace('preferDeep = options.getBoolean("preferDeep", false);',
                 'throw new IllegalStateException("deliberate failure");'))
    subprocess.run(["javac", "-cp", str(HOME / "maze.jar"), "-d", str(research / "extensions")]
                   + list(map(str, (research / "src/research").glob("*.java"))), check=True)
    subprocess.run(["jar", "--create", "--file", str(research / "research.jar"),
                    "-C", str(research / "extensions"), "."], check=True)
    subject = research / "subject/example/SmokeSubject.java"
    (subject.parent / "OtherSubject.java").write_text(subject.read_text().replace("SmokeSubject", "OtherSubject"))
    (research / "classes").mkdir()
    subprocess.run([str(JAVA8 / "bin/javac"), "-g", "-d", str(research / "classes")]
                   + list(map(str, subject.parent.glob("*.java"))), check=True)
    benchmarks = work / "benchmarks/conf"
    benchmarks.mkdir(parents=True)
    config = benchmarks / "benchmarks.list"
    config.write_text('{\nSUBJECT={ src="%s"; bin="%s"; classpath=("%s"); classes=(example.SmokeSubject, example.OtherSubject); };\n}\n'
                      % (research / "subject", research / "classes", research / "classes"))
    tool = work / "tool"
    (tool / "lib").mkdir(parents=True)
    shutil.copy(REPO / "tools/maze/runtool", tool / "runtool")
    shutil.copy(REPO / "tools/maze/lib/maze-adapter.jar", tool / "lib")
    commands = work / "commands"
    commands.mkdir()
    properties = {"config": config, "java": JAVA8 / "bin/java", "javac": JAVA8 / "bin/javac",
                  "pitest": os.pathsep.join(map(str, PIT)), **LIBRARIES}
    # Same runner and arguments as the full image, with portable validation paths.
    command = [str(JAVA8 / "bin/java"), "-ea"] + ["-Dsbst.benchmark." + key + "=" + str(value)
               for key, value in properties.items()] + ["-jar", str(RUNNER)]
    launcher = commands / "contest_run_benchmark_tool.sh"
    launcher.write_text("#!/bin/sh\nexec " + shlex.join(command) + ' "$@"\n')
    launcher.chmod(0o755)
    env = dict(os.environ, BENCH_HOME=str(benchmarks.parent),
               PATH=str(commands) + os.pathsep + str(SCRIPTS) + os.pathsep + os.environ["PATH"])
    for mode in ("symbolic", "concrete"):
        for kind, arguments in [
            ("baseline", ["--strategy", "BFS"]),
            ("strategy", ["--plugin", "research.jar", "--strategy", "research.DepthSearch"]),
            ("heuristic", ["--plugin", "research.jar", "--strategy", "PS", "--heuristic", "research.DepthWindowHeuristic"]),
        ]:
            name = kind + "-" + mode
            experiment = research / (name + ".json")
            experiment.write_text(json.dumps({"name": name, "mode": mode,
                                              "arguments": arguments + ["--minimization=true"]}))
            subprocess.run(["bash", str(REPO / "tools/maze/run_benchmarks.sh"), "5", "1", str(experiment)],
                           cwd=tool, env=env, check=True, timeout=180)
            result = tool / ("results_maze-" + name + "_5/SUBJECT_1")
            with (result / "metrics/transcript.csv").open() as stream:
                rows = [row for row in csv.DictReader(stream) if row.get("class")]
            assert {r["class"] for r in rows} == {"example.SmokeSubject", "example.OtherSubject"}, rows
            for row in rows:
                assert int(row["linesCovered"]) > 0, row
                assert int(row["mutantsTotal"]) > 0 and int(row["mutantsKilled"]) > 0, row
                assert int(row["uncompilableNumber"]) == 0, row
    # Exercise failure through the real benchmark runner too.
    broken = research / "broken.json"
    broken.write_text(json.dumps({"name": "broken", "mode": "symbolic", "arguments":
                                  ["--plugin", "research.jar", "--strategy", "research.Broken"]}))
    failed = subprocess.run(["bash", str(REPO / "tools/maze/run_benchmarks.sh"), "5", "1", str(broken)],
                            cwd=tool, env=env, timeout=60)
    assert failed.returncode != 0
    assert not (tool / "results_maze-broken_5/SUBJECT_1/metrics").exists()
    subprocess.run(["bash", str(SCRIPTS / "contest_transcript_single.sh"), "."], cwd=tool, env=env, check=True)
    with (tool / "results.tmp").open() as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("class")]
    assert len(rows) == 12 and all(row["tool"] != "maze-broken" for row in rows), rows
    print("JUGE pipeline passed: six configurations, two classes each, real coverage and mutation scores, failed extension excluded.")
    shutil.rmtree(work)


if __name__ == "__main__":
    verify()
