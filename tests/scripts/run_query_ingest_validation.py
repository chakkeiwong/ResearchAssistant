#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--query', required=True)
    parser.add_argument('--arxiv-id')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    cmd = ['ra', '--root', str(root), 'ingest', '--query', args.query]
    if args.arxiv_id:
        cmd += ['--arxiv-id', args.arxiv_id]
    paper_id = run(cmd)
    print('PAPER_ID:', paper_id)
    print('FIND:')
    print(run(['ra', '--root', str(root), 'find', '--query', args.query.split()[0]]))
    print('SHOW:')
    print(run(['ra', '--root', str(root), 'show', '--paper-id', paper_id]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
