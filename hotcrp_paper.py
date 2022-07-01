#!/usr/bin/env python3

import sys
import json
import requests


def get_cookies():
    with open("hotcrp_secrets.json") as f:
        env = json.load(f)
        return dict(hotcrpsession=env["hotcrpsession"])


cookies = get_cookies()
api_base = "https://sosp21.hotcrp.com/api"


def get_status():
    r = requests.get(api_base + "/status", cookies=cookies)
    if r.status_code != 200:
        print(r, file=sys.stderr)
        print(r.text, file=sys.stderr)
        raise ValueError("could not fetch HotCRP status")
    return r.json()


def _current_paper(status):
    if "tracker" not in status:
        return None
    tracker = status["tracker"]
    offset = tracker["paper_offset"]
    return tracker["papers"][offset]


def get_current_paper():
    return _current_paper(get_status())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", help="also print paper title", action="store_true")

    args = parser.parse_args()

    paper = get_current_paper()

    if paper is None:
        print("no paper being tracked", file=sys.stderr)
        sys.exit(1)

    if args.title:
        print(paper["title"], file=sys.stderr)
    print(paper["pid"])


if __name__ == "__main__":
    import argparse

    main()
