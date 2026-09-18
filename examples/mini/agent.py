#!/usr/bin/env python3
"""The world's tiniest agent. Reads the task prompt, writes result.txt.

  --method buggy     ignores the 'even' requirement (writes the largest number)
  --method correct   writes the largest EVEN number

Swap this file for your real agent; the loop around it stays identical.
"""

import argparse
import pathlib
import re

parser = argparse.ArgumentParser()
parser.add_argument("--method", choices=["buggy", "correct"], default="buggy")
method = parser.parse_args().method

prompt = pathlib.Path("task/prompt.txt").read_text()
fixture = re.search(r"nums_[AB]\.txt", prompt).group(0)
nums = [int(x) for x in (pathlib.Path("task/fixtures") / fixture).read_text().split()]
if method == "correct":
    evens = [n for n in nums if n % 2 == 0]
    answer = max(evens) if evens else max(nums)
else:
    answer = max(nums)
pathlib.Path("result.txt").write_text(str(answer))
