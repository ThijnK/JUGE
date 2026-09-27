#!/usr/bin/env python3
"""Build the common image and provision pinned upstream tools for AST 2027."""
import argparse
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
JUGE = HERE.parents[1]


def definitions(root):
    return {
        'EvoSuite': dict(directory=str(root / 'evosuite'), version='1.2.0', seed_env='JUGE_TOOL_SEED',
                        configuration='DYNAMOSA; real -seed; Java8; phase budgets follow JUGE adapter; see frozen runtool'),
        'T3': dict(directory=str(root / 't3'), version='3.0.1-SNAPSHOT-a12cf1a3-java8-api-seeded', seed_env='JUGE_TOOL_SEED',
                   configuration='Gen2 SBST settings; unmodified upstream source built for Java8; T3Random seeded through existing API; Worklist RNG unseeded; see SeededT3.java'),
        'Kex': dict(directory=str(root / 'kex'), version='0.0.11', seed_env='JUGE_TOOL_SEED',
                    configuration='concolic; easy-random.seed=scheduled seed; ksmt.seed=seed & 0x7fffffff; timeLimit=requested seconds; one executor and worker; Linux AMD64 Java8')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    if root.exists():
        raise SystemExit('Use a fresh output directory; existing provisioned tools are never overwritten.')
    root.mkdir(parents=True)
    commands = [
        ['docker', 'build', '--platform', 'linux/amd64', '-t', 'maze-ast2027:amd64', '-f', str(JUGE / 'experiments/ast2027/Dockerfile'), str(JUGE)],
        ['sh', str(HERE / 'evosuite/provision.sh'), str(root / 'evosuite')],
        ['sh', str(HERE / 't3/provision.sh'), str(root / 't3')],
        ['python3', str(HERE / 'kex/fetch.py'), str(root / 'kex')]]
    with (root / 'provision.log').open('w') as log:
        for command in commands:
            print('Running: ' + ' '.join(command), flush=True)
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    (root / 'tools.json').write_text(json.dumps(definitions(root), indent=2) + '\n')
    print('Ready: ' + str(root / 'tools.json'))


if __name__ == '__main__':
    main()
