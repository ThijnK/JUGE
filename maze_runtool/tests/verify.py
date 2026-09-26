#!/usr/bin/env python3
"""Artifact-level checks of the real MAZE adapter and the scoring gates."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid

REPO = Path(__file__).resolve().parents[2]
HOME = Path(os.environ["MAZE_HOME"])
SCRIPTS = REPO / "infrastructure/scripts"
spec = importlib.util.spec_from_file_location("gate", SCRIPTS / "maze_validate_generation.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class AdapterCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix="juge research ")
        cls.research = Path(cls.fixture.name)
        shutil.copytree(HOME / "examples/search-extensions", cls.research, dirs_exist_ok=True)
        source = cls.research / "src/research/DepthSearch.java"
        (source.parent / "Broken.java").write_text(source.read_text().replace("DepthSearch", "Broken")
            .replace('preferDeep = options.getBoolean("preferDeep", false);',
                     'throw new IllegalStateException("deliberate extension failure");'))
        subprocess.run(["javac", "-cp", str(HOME / "maze.jar"), "-d", str(cls.research / "extensions")]
                       + [str(p) for p in (cls.research / "src/research").glob("*.java")], check=True)
        subprocess.run(["jar", "--create", "--file", str(cls.research / "research.jar"),
                        "-C", str(cls.research / "extensions"), "."], check=True)
        subject = cls.research / "subject/example/SmokeSubject.java"
        (subject.parent / "OtherSubject.java").write_text(subject.read_text().replace("SmokeSubject", "OtherSubject"))
        subprocess.run(["javac", "--release", "8", "-d", str(cls.research / "classes")]
                       + [str(p) for p in subject.parent.glob("*.java")], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="juge adapter ")
        self.work = Path(self.temp.name)
        (self.work / "lib").mkdir()
        shutil.copy(REPO / "tools/maze/lib/maze-adapter.jar", self.work / "lib")
        shutil.copy(REPO / "tools/maze/runtool", self.work / "runtool")
        self.batch_id = str(uuid.uuid4())

    def tearDown(self):
        self.temp.cleanup()

    def generate(self, mode, arguments, subjects=("example.SmokeSubject", "example.OtherSubject"), extra=None):
        configuration = {"name": "research-run", "mode": mode, "arguments": arguments}
        configuration.update(extra or {})
        config = self.research / "experiment.json"
        config.write_text(json.dumps(configuration))
        env = dict(os.environ, MAZE_EXPERIMENT=str(config), JUGE_MAZE_BATCH_ID=self.batch_id)
        protocol = ["BENCHMARK", str(self.research / "subject"), str(self.research / "classes"),
                    "0", str(len(subjects)), "5", *subjects]
        return subprocess.run([str(self.work / "runtool")], cwd=self.work, env=env,
                              input="\n".join(protocol) + "\n", text=True, capture_output=True, timeout=90)

    def result_directory(self):
        root = self.work / "results_maze-research-run_5/SUBJECT_1"
        root.mkdir(parents=True)
        shutil.copytree(self.work / "temp", root / "temp")
        (root / "maze-process-exit.txt").write_text("0")
        (root / "maze-batch-id.txt").write_text(self.batch_id)
        (root / "GENERATION_FINISHED.txt").touch()
        batch = json.loads((root / "temp/maze-batch.json").read_text())
        for invocation in batch["invocations"]:
            source = (root / "temp" / invocation["status"]).parent
            archived = root / "temp/maze-tests" / invocation["target"]
            shutil.copytree(source, archived)
            (archived / "timing.txt").write_text("prepTime=1\ngenTime=1\n")
        return root

    def test_external_and_builtin_strategies_in_both_modes(self):
        configurations = [
            ["--strategy", "BFS"],
            ["--plugin", "research.jar", "--strategy", "research.DepthSearch"],
            ["--plugin", "research.jar", "--strategy", "PS", "--heuristic", "research.DepthWindowHeuristic"],
            ["--plugin", "research.jar", "--search-config", "search.json"],
        ]
        for mode in ("symbolic", "concrete"):
            for arguments in configurations:
                with self.subTest(mode=mode, arguments=arguments):
                    result = self.generate(mode, arguments + ["--minimization=true", "--seed=4294967295", "--max-replay-steps=10000"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.splitlines().count("READY"), 3)
                    batch = json.loads((self.work / "temp/maze-batch.json").read_text())
                    self.assertEqual(batch["outcome"], "completed")
                    self.assertEqual(len(batch["invocations"]), 2)
                    for invocation in batch["invocations"]:
                        status_path = self.work / "temp" / invocation["status"]
                        status = json.loads(status_path.read_text())
                        self.assertEqual(status["mode"], mode)
                        self.assertEqual(status["seed"], 4294967295)
                        self.assertEqual(status["candidateReplay"]["maxTraceEntries"], 10000)
                        self.assertEqual(status["candidateReplay"]["maxSymbolicSteps"], 10000)
                        if "search.json" in arguments:
                            self.assertEqual(len(status["configuration"]), 3)
                        test_name = invocation["target"].split(".")[-1] + "Test"
                        classpath = os.pathsep.join(map(str, [HOME / "maze.jar", self.research / "classes", status_path.parent]))
                        subprocess.run(["javac", "--release", "8", "-cp", classpath, "-d", str(status_path.parent),
                                        str(status_path.parent / (test_name + ".java"))], check=True)
                        subprocess.run(["java", "-cp", classpath, "org.junit.runner.JUnitCore", test_name], check=True)

    def test_failure_is_not_acknowledged_or_published(self):
        result = self.generate("symbolic", ["--plugin", "research.jar", "--strategy", "research.Broken"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines().count("READY"), 1)
        self.assertFalse(list((self.work / "temp/testcases").glob("*.java")))
        self.assertEqual(json.loads((self.work / "temp/maze-batch.json").read_text())["outcome"], "failed")
        self.assertTrue(list((self.work / "temp").glob("maze-run-*/maze.log")))

    def test_invalid_configuration_and_reserved_arguments_fail(self):
        for arguments, extra in [(["--class-name", "wrong.Target"], {}), (["-C"], {}),
                                 (["@hidden-options"], {}), ([], {"typo": True}), (["-b10"], {})]:
            with self.subTest(arguments=arguments, extra=extra):
                result = self.generate("symbolic", arguments, extra=extra)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("READY", result.stdout)

    def test_completion_gate_rejects_stale_failed_and_changed_records(self):
        self.assertEqual(self.generate("symbolic", ["--strategy", "BFS"]).returncode, 0)
        root = self.result_directory()
        batch = gate.validate(root)
        for filename, contents in [("maze-process-exit.txt", "1"), ("maze-batch-id.txt", "old-run")]:
            path = root / filename
            original = path.read_text()
            path.write_text(contents)
            with self.assertRaises(ValueError): gate.validate(root)
            path.write_text(original)
        path = root / "temp" / batch["invocations"][0]["status"]
        path.write_text(path.read_text().replace('"completed"', '"failed"'))
        with self.assertRaises(ValueError): gate.validate(root)

    def test_generation_script_requires_process_and_batch_success(self):
        commands = self.work / "commands"
        commands.mkdir()
        driver = commands / "contest_run_benchmark_tool.sh"
        driver.write_text("""#!/usr/bin/env python3
import os, pathlib, subprocess, sys, json, shutil
if os.environ.get("SIMULATE_STALE") != "yes":
    result = subprocess.run(["./runtool"], input=os.environ["PROTOCOL"], text=True, capture_output=True)
    pathlib.Path("log.txt").write_text(result.stdout + result.stderr)
    if result.returncode == 0:
        batch = json.loads(pathlib.Path("temp/maze-batch.json").read_text())
        for invocation in batch["invocations"]:
            source = (pathlib.Path("temp") / invocation["status"]).parent
            archived = pathlib.Path("temp/maze-tests") / invocation["target"]
            shutil.copytree(source, archived)
            (archived / "timing.txt").write_text("prepTime=1\\ngenTime=1\\n")
# Emulate a parent driver that can exit zero even when its child failed.
sys.exit(int(os.environ.get("DRIVER_EXIT", "0")))
""")
        driver.chmod(0o755)
        benchmarks = self.work / "benchmarks/conf"
        benchmarks.mkdir(parents=True)
        (benchmarks / "benchmarks.list").write_text("SUBJECT={}\n")
        protocol = "\n".join(["BENCHMARK", str(self.research / "subject"), str(self.research / "classes"),
                                "0", "1", "5", "example.SmokeSubject", ""])
        config = self.research / "generation.json"
        env = dict(os.environ, PATH=str(commands) + os.pathsep + os.environ["PATH"],
                   MAZE_EXPERIMENT=str(config), BENCH_HOME=str(benchmarks.parent), PROTOCOL=protocol)
        for name, strategy, parent_exit in [("good", "BFS", "0"), ("broken", "research.Broken", "0"),
                                             ("parent-failed", "BFS", "1")]:
            with self.subTest(name=name):
                config.write_text(json.dumps({"name": name, "mode": "symbolic",
                    "arguments": ["--plugin", "research.jar", "--strategy", strategy]}))
                result = subprocess.run(["bash", str(SCRIPTS / "contest_generate_tests.sh"), "maze-" + name,
                                         "1", "1", "5"], cwd=self.work, env=dict(env, DRIVER_EXIT=parent_exit),
                                        capture_output=True, text=True, timeout=60)
                root = self.work / ("results_maze-" + name + "_5/SUBJECT_1")
                if name == "good":
                    self.assertEqual(result.returncode, 0, result.stderr)
                    gate.validate(root)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue((root / "GENERATION_FAILED.txt").is_file())
                    self.assertFalse((root / "GENERATION_FINISHED.txt").exists())
        shutil.copytree(self.work / "results_maze-good_5/SUBJECT_1/temp", self.work / "temp")
        result = subprocess.run(["bash", str(SCRIPTS / "contest_generate_tests.sh"), "maze-stale", "1", "1", "5"],
                                cwd=self.work, env=dict(env, SIMULATE_STALE="yes"), capture_output=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.work / "results_maze-stale_5/SUBJECT_1/GENERATION_FAILED.txt").is_file())

    def test_metrics_and_aggregation_do_not_accept_stale_output(self):
        self.assertEqual(self.generate("symbolic", ["--strategy", "BFS"]).returncode, 0)
        root = self.result_directory()
        metrics = root / "metrics"
        metrics.mkdir()
        (metrics / "transcript.csv").write_text("maze,SUBJECT,example.SmokeSubject,1,42\n")
        (metrics / "COMPUTATION_FINISHED.txt").touch()
        # A valid record permits existing results to be aggregated.
        result = subprocess.run(["bash", str(SCRIPTS / "contest_transcript_single.sh"), str(root.parent)],
                                cwd=self.work, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("example.SmokeSubject", (self.work / "results.tmp").read_text())
        (root / "maze-batch-id.txt").write_text("stale")
        result = subprocess.run(["bash", str(SCRIPTS / "contest_compute_metrics.sh"), str(root.parent)],
                                cwd=self.work, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        subprocess.run(["bash", str(SCRIPTS / "contest_transcript_single.sh"), str(root.parent)],
                       cwd=self.work, check=True, capture_output=True)
        self.assertNotIn("example.SmokeSubject", (self.work / "results.tmp").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
