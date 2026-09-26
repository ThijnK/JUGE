#!/usr/bin/env python3
"""Require positive, matching MAZE completion evidence before computing or scoring metrics."""
import argparse
import hashlib
import json
from pathlib import Path


def validate(root, require_finished=True):
    root = Path(root)
    if require_finished and not (root / "GENERATION_FINISHED.txt").is_file():
        raise ValueError("generation did not finish successfully")
    if (root / "maze-process-exit.txt").read_text().strip() != "0":
        raise ValueError("JUGE generation exited unsuccessfully")
    batch = json.loads((root / "temp/maze-batch.json").read_text())
    expected = (root / "maze-batch-id.txt").read_text().strip()
    if not expected or batch["batchId"] != expected or batch["outcome"] != "completed":
        raise ValueError("missing or stale MAZE batch completion")
    invocations = batch["invocations"]
    if not invocations:
        raise ValueError("no MAZE invocations completed")
    seen = set()
    for invocation in invocations:
        path = (root / "temp" / invocation["status"]).resolve()
        path.relative_to((root / "temp").resolve())
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != invocation["sha256"]:
            raise ValueError("MAZE completion record changed after generation")
        status = json.loads(content)
        identity = status["invocationId"]
        if (status["outcome"] != "completed" or status["target"] != invocation["target"]
                or status["mode"] != batch["experiment"]["mode"]
                or identity != invocation["invocationId"] or identity in seen):
            raise ValueError("MAZE completion does not match the experiment")
        archived = root / "temp/maze-tests" / invocation["target"]
        if not (archived / "timing.txt").is_file():
            raise ValueError("missing per-class generation archive")
        for source in path.parent.rglob("*.java"):
            if source.read_bytes() != (archived / source.relative_to(path.parent)).read_bytes():
                raise ValueError("archived tests do not match the completed MAZE invocation")
        seen.add(identity)
    return batch


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--generation", action="store_true", help="validate before writing the success marker")
    args = parser.parse_args()
    try:
        validate(args.directory, require_finished=not args.generation)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, "Cannot score MAZE generation in {}: {}\n".format(args.directory, error))
