"""Record a seeded generator invocation and enforce its adapter deadline."""
import json
import os
from pathlib import Path
import signal
import subprocess


def run(command, *, tool, version, seed, target, budget, timeout, stdout, env=None):
    receipt = dict(tool=tool, version=version, seed=seed, target=target, budget=budget)
    process = subprocess.Popen(command, stdout=stdout, stderr=subprocess.STDOUT,
                               env=env, start_new_session=True)
    Path('invocation.json').write_text(json.dumps(receipt) + '\n')
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        Path('timeout.json').write_text(json.dumps(dict(receipt, reason='adapter_generation_timeout')) + '\n')
        raise
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    if code:
        raise subprocess.CalledProcessError(code, command)
