from __future__ import annotations

import argparse
from collections.abc import Callable


Handler = Callable[[argparse.Namespace], int]
Subparsers = argparse._SubParsersAction
