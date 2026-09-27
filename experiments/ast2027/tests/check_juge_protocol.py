"""A tool that exits without READY must fail generation, even after writing output."""
from pathlib import Path
import subprocess
import tempfile

with tempfile.TemporaryDirectory() as name:
    work = Path(name)
    # Script speaks initial protocol, then simulates a failed generator.
    tool = work / 'runtool'
    tool.write_text('''#!/usr/bin/python3
import sys
from pathlib import Path
assert input() == "BENCHMARK"
input(); input()
for _ in range(int(input())): input()
input()
print("READY", flush=True)
input(); input()
Path("temp/testcases/PartialTest.java").write_text("// partial output")
sys.exit(3)
''')
    tool.chmod(0o755)
    config = work / 'benchmarks.list'
    classes = '/results/env/subjects/classes'
    config.write_text('{ SUBJECT={ src="/results/env/subjects/src"; bin="%s"; classpath=("%s"); classes=(nl.uu.maze.benchmarks.BinarySearch); }; }' % (classes, classes))
    cmd = ['/opt/java8/bin/java', '-Dsbst.benchmark.config=' + str(config), '-jar', '/results/env/lib/runner.jar', 'broken', 'SUBJECT', str(work), '1', '10', '--only-generate-tests']
    result = subprocess.run(cmd, cwd=work, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    assert result.returncode != 0, result.stdout
    assert 'Tool failed before sending READY' in result.stdout, result.stdout
    assert 'Execution finished with no timeout' not in result.stdout, result.stdout
    print('JUGE correctly rejected tool exit before READY despite partial output.')
