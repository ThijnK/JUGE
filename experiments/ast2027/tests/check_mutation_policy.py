"""Run inside the image with prepared /results/env and /suite mounts."""
from pathlib import Path
import subprocess
import tempfile

with tempfile.TemporaryDirectory() as name:
    work = Path(name)
    (work / 'ManyMutants.java').write_text('public class ManyMutants { public static int f(int x) {\n' + 'x = x + 1;\n' * 500 + 'return x; }}\n')
    jar = '/results/env/lib/runner.jar'
    subprocess.run(['/opt/java8/bin/javac', '-g', '-cp', jar, '-d', name, str(work / 'ManyMutants.java'), '/suite/tests/MutationPolicyCheck.java'], check=True)
    subprocess.run(['/opt/java8/bin/java', '-cp', jar + ':' + name, 'MutationPolicyCheck', name], check=True)
