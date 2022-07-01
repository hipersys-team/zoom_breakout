#!/usr/bin/env python3

import sys
import argparse
import json
import unidecode
from hotcrp_paper import get_current_paper
from config_gen import load_pc_conflicts
from zoom_api import new_client, api_base

pc, paper_conflicts = load_pc_conflicts(
    "data/sosp21-pcassignments.csv",
    "data/SOSP'21 PC meeting members - Zoom emails.csv",
    "data/sosp21-pcconflicts.csv",
)

with open("meeting.json") as f:
    config = json.load(f)


def rooms_for_papers(paper_ids):
    conflicts = set()
    for paper in paper_ids:
        if paper in paper_conflicts:
            conflicts.update(paper_conflicts[paper])
    label = "papers" if len(paper_ids) > 1 else "paper"
    ids = ", ".join([str(i) for i in paper_ids])
    rooms = pc.rooms_for_conflicts(conflicts, f"Discussion ({label} {ids})")
    return rooms


def set_rooms_by_api(rooms):
    """Set the meeting breakout rooms using the Zoom API.

    Uses rooms in the format of rooms_for_papers, namely a dict from name to
    list of participant emails.

    """
    api_rooms = []
    for name in sorted(rooms.keys()):
        emails = rooms[name]
        api_rooms.append({"name": name, "participants": emails})

    client = new_client()
    r = client.patch(
        api_base + "/meetings/" + config["meeting_id"],
        json={
            "settings": {
                "breakout_room": {
                    "enable": True,
                    "rooms": api_rooms,
                }
            }
        },
    )
    if r.status_code != 204:
        print(r, file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(1)


def name_to_tokens(name):
    return unidecode.unidecode(name).split(" ")


def rooms_by_name(rooms):
    name_to_room = {}

    def map_email(room, e):
        if room.startswith("Discussion"):
            room = "Discussion"
        name = pc.name_for_email(e)
        for tok in name_to_tokens(name):
            if tok in name_to_room and name_to_room[tok] != room:
                # conflicts shouldn't be mapped
                name_to_room[tok] = None
            else:
                name_to_room[tok] = room

    for room, emails in rooms.items():
        for e in emails:
            map_email(room, e)

    return name_to_room


def conflict_names(rooms):
    """Get the names for just the conflicts, from room assignments."""
    names = {pc.name_for_email(e) for e in rooms["Conflict Room"]}
    return sorted(list(names))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--name-json", help="emit JSON mapping from name to room", action="store_true"
    )
    parser.add_argument(
        "--conflicts",
        help="print paper conflict as a list of names",
        action="store_true",
    )
    parser.add_argument(
        "--hotcrp",
        help="use current HotCRP tracker paper",
        action="store_true",
    )
    parser.add_argument("paper", type=int, nargs="*", help="list of paper IDs")

    args = parser.parse_args()

    paper_ids = sorted(args.paper)
    if args.hotcrp:
        if len(paper_ids) > 0:
            paper_ids_str = ", ".join(str(p) for p in paper_ids)
            print(
                f"passed --hotcrp but also some papers ({paper_ids_str})",
                file=sys.stderr,
            )
            sys.exit(1)
        paper = get_current_paper()
        if paper is None:
            print("no paper being tracked in HotCRP", file=sys.stderr)
            sys.exit(1)
        paper_ids = [paper["pid"]]

    # check that all the paper IDs are valid
    for paper in paper_ids:
        if paper not in paper_conflicts:
            print(f"paper {paper} not found", file=sys.stderr)
            sys.exit(1)

    rooms = rooms_for_papers(paper_ids)

    if args.name_json:
        print(json.dumps(rooms_by_name(rooms)))
    if args.conflicts:
        for name in conflict_names(rooms):
            print(name)
    if not (args.name_json or args.conflicts):
        set_rooms_by_api(rooms)


if __name__ == "__main__":
    main()
