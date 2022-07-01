#!/usr/bin/env python3

import re
from set_breakouts import rooms_for_papers, conflict_names


def add_conflicts(lines):
    line_length = len(lines[0])
    new_lines = []
    for line in lines:
        line = line.rstrip()
        new_lines.append(line)
        components = re.split(r"""\s+""", line.rstrip())
        day, time, topic, paper_id = components
        paper_id = int(paper_id)
        names = conflict_names(rooms_for_papers([paper_id]))
        for name in names:
            new_lines.append(" " * 4 + name)
    return new_lines


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("schedule", help="file with schedule.txt")

    args = parser.parse_args()

    with open(args.schedule) as f:
        lines = list(f)
    lines = add_conflicts(lines)
    for line in lines:
        print(line)


if __name__ == "__main__":
    import argparse

    main()
