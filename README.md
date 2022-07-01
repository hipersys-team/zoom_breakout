# SOSP 2021 PC meeting

Quick guide:

Create a OAuth zoom app in order to get client id, client secret, access tokens:
The instructions are at:
https://github.com/zoom/zoom-oauth-sample-app

Follow the instructions in the above link to launch ngrok, which gives the redirection url.

After following the above instructions, we should have access_token, refresh_token, update them in the token_secrets.json.
Then start a zoom meeting, using the meeting id (appers a number after /j/ in the url) in sample_breakout.py, can create breakout rooms.

sample_breakout.py is a simple test python program. It only creates breakout rooms and sets the assignment. The host has to leave and join back again to see the changes in the assignment.
Only when open-rooms is clicked in the breakout rooms, people will be joining the breakout rooms.


Original documentation:

Important configuration: `meeting.json` points to the meeting ID, for both the
API and to join it with scripting.

Several secrets are needed for authentication:

- See [`zoom_api.py`](zoom_api.py) for documentation on `zoom_secrets.json` and
`token_secrets.json`.
- `hotcrp_secrets.json` should have the form `{ "hotcrpsession": ... }` where
  this session is easiest to get by exporting your cookies for hotcrp.com from a
  browser and reading the output file.

[Zoom application](https://marketplace.zoom.us/develop/apps/zgLubel5Saavh9GT3C0H0w/activation)

[edit Zoom PC meeting](https://zoom.us/meeting/97673041726/edit)

Note: the below commands use fish syntax with `foo (command)` for
interpolation; the analogous bash/zsh is `foo $(command)`.

- `./config_gen.py` generates a folder of CSVs for using Zoom's upload feature.
  Use this by [editing the Zoom
  meeting](https://zoom.us/meeting/97673041726/edit).
- `zoom_api.py` is a library for accessing the Zoom API, with OAuth. When run it
  just tests authentication by fetching the current user's profile.
- `set_breakouts.py` is the workhorse script.
  - `./set_breakouts.py 70` uses the API to set the breakout rooms to paper 70.
  - `./set_breakouts.py 82 87 90` takes the union of conflicts for multiple
    papers.
  - `./set_breakouts.py --conflicts 70` prints the conflicts as a list of names
    (for manual usage).
- `hotcrp_paper.py` returns the current paper in the HotCRP tracker. Use it like
  `./set_breakouts.py (./hotcrp_paper.py)` to get the paper number automatically.
- `./zoom-breakout.applescript` is a DSL for automating Zoom.
  - `./zoom-breakout.applescript reload joinBreakout` goes through the process
      of reloading the meeting breakout rooms. The way this works is that you
      first change the meeting configuration (through the API, or via the
      meeting's edit URL and uploading a CSV file), then to "install" that new
      configuration, the host must close all rooms, then re-open them. All
      participants will then re-join with the correct room assignment.
  - `./zoom-breakout.applescript reload` is `close recreate open`.
  - `./zoom-breakout.applescript moveTo= (./set_breakouts.py --name-json 70)` moves
    people by clicking through the UI. It gets the conflicts based on paper 70.
  - `./zoom-breakout.applescript moveTo= (./set_breakouts.py --name-json (./hotcrp_paper.py))` automatically fixes rooms based on the HotCRP tracker.
  - `./zoom-breakout.applescript leave join` will leave and re-join the PC meeting.
