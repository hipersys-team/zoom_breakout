#!/usr/bin/env python3

import pandas as pd
import csv
import os
import shutil


def normalize_email(e):
    return e.lower().strip()


def uniqify_list(l):
    seen = set()
    unique = []
    for x in l:
        if x not in seen:
            unique.append(x)
            seen.add(x)
    return unique


class PcMembers:
    """Represents the set of PC members and their emails."""

    def __init__(self):
        self._name_to_emails = {}
        self._email_to_name = {}

    def _load_email_csv(self, fname):
        with open(fname) as f:
            for line in f:
                fields = line.split(",")
                name = fields[0]
                emails = fields[1:]
                self.add_name_emails(name, emails)

    def add_name_emails(self, name, emails):
        emails = [normalize_email(e) for e in emails]
        emails = [e for e in emails if e != ""]
        if name not in self._name_to_emails:
            self._name_to_emails[name] = []
        email_list = self._name_to_emails[name]
        email_list.extend(emails)
        self._name_to_emails[name] = uniqify_list(email_list)
        for e in emails:
            self._email_to_name[e] = name

    @classmethod
    def from_email_csv(cls, fname):
        x = cls()
        x._load_email_csv(fname)
        return x

    def name_for_email(self, email):
        return self._email_to_name.get(email, None)

    def email_known(self, email):
        return email in self._email_to_name

    def rooms_for_conflicts(self, conflicted_emails, discussion_room):
        """Generate a list of room participants where non-conflicts go to
        discussion_room.

        Set discussion_room to None to leave non-conflicted participants
        unassigned (in the main room).

        """
        rooms = {"Conflict Room": []}
        if discussion_room is not None:
            rooms[discussion_room] = []
        for name, emails in self._name_to_emails.items():
            if set(emails).intersection(conflicted_emails):
                # has a conflict
                for e in emails:
                    rooms["Conflict Room"].append(e)
            else:
                # non-conflicted
                if discussion_room is not None:
                    for e in emails:
                        rooms[discussion_room].append(e)
        return rooms


def write_zoom_breakout_csv(rooms, out):
    w = csv.writer(out)
    w.writerow(["Pre-assign Room Name", "Email Address"])
    for room, emails in rooms.items():
        for e in emails:
            w.writerow([room, e])


def get_paper_conflicts(conflict_df):
    paper_conflicts = {}
    for _index, conflict in conflict_df.iterrows():
        paper = conflict["paper"]
        email = normalize_email(conflict["email"])
        if paper not in paper_conflicts:
            paper_conflicts[paper] = set()
        paper_conflicts[paper].add(email)
    return paper_conflicts


def load_pc_conflicts(assignment_csv, email_csv, conflict_csv):
    pc = PcMembers.from_email_csv(email_csv)
    # extend pc with any emails found in paper_conflicts
    conflict_df = pd.read_csv(conflict_csv)
    # extend list of papers with non-conflicted R3 papers
    assignment_df = pd.read_csv(assignment_csv)
    assignment_df = assignment_df[assignment_df["round"] == "R3"]
    for _index, conflict in conflict_df.iterrows():
        first = conflict["first"]
        last = conflict["last"]
        email = normalize_email(conflict["email"])
        if not pc.email_known(email):
            name = f"{first} {last}"
            pc.add_name_emails(name, [email])
    paper_conflicts = get_paper_conflicts(conflict_df)
    for _index, row in assignment_df.iterrows():
        paper_id = row["paper"]
        if paper_id not in paper_conflicts:
            paper_conflicts[paper_id] = set()
    return pc, paper_conflicts


def main():
    pc, paper_conflicts = load_pc_conflicts(
        "data/sosp21-pcassignments.csv",
        "data/SOSP'21 PC meeting members - Zoom emails.csv",
        "data/sosp21-pcconflicts.csv",
    )

    if os.path.exists("configurations"):
        shutil.rmtree("configurations")
    os.mkdir("configurations")
    for paper, conflicts in paper_conflicts.items():
        with open(
            os.path.join("configurations", f"paper-{paper}.csv"), "w", newline=""
        ) as out:
            rooms = pc.rooms_for_conflicts(conflicts, f"Discussion (paper {paper})")
            write_zoom_breakout_csv(rooms, out)


if __name__ == "__main__":
    main()
