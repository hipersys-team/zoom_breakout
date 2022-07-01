#!/usr/bin/env osascript -l JavaScript
// -*- mode: javascript -*-

/* global configuration */

// currently mainly prints participants already in the right place when moving
let debugLogging = true;
function debugLog(msg) {
  if (debugLogging) {
    console.log(msg);
  }
}

// multiply delays by this number
let patienceFactor = 1.5;

/* load meeting info */

let config = (function () {
  var app = Application.currentApplication();
  app.includeStandardAdditions = true;
  var fileName = Path("/Users/tchajed/sosp21-pc-meeting/meeting.json");
  return JSON.parse(app.read(fileName));
})();

let meetingID = config["meeting_id"];
let meetingPwd = config["meeting_pwd"];

function getUnique(arraySpec) {
  if (arraySpec.length == 0) {
    return null;
  }
  if (arraySpec.length == 1) {
    return arraySpec.at(0);
  }
  throw "element not unique";
}

function waitForWindow(filter, timeToWait) {
  var totalWait = 0.0;
  while (totalWait < timeToWait * patienceFactor) {
    let matches = app.windows.whose(filter);
    if (matches.length > 0) {
      return getUnique(matches);
    }
    delay(0.5);
    totalWait += 0.5;
  }
  console.log("window did not appear:");
  console.log(JSON.stringify(filter));
  return null;
}

let SystemEvents = Application("System Events");
let app = SystemEvents.processes.byName("zoom.us");

function getZoomMeeting() {
  let meeting = waitForWindow({ title: { _contains: "Zoom Meeting" } }, 5);
  if (meeting == null) {
    throw "no Zoom meeting in progress";
  }
  return meeting;
}

function openBreakoutRoomsMenu() {
  let br = getUnique(
    app.windows.whose({ title: { _contains: "Breakout Rooms" } })
  );
  if (br !== null) {
    return br;
  }
  let meeting = getZoomMeeting();
  let brButton = getUnique(
    meeting.buttons.whose({ description: { "=": "Breakout Rooms" } })
  );
  if (brButton == null) {
    throw "Breakout Rooms button not visible (expand meeting window)";
  }
  brButton.click();
  return waitForWindow({ title: { _contains: "Breakout Rooms" } }, 3);
}

function closeRooms() {
  let br = openBreakoutRoomsMenu();
  let b = getUnique(
    br.buttons.whose({ description: { "=": "Close All Rooms" } })
  );
  if (b == null) {
    return;
  }
  b.click();
  // wait to rejoin main room if needed
  waitForWindow({ title: { "=": "Zoom Meeting" } }, 10);
  delay(1 * patienceFactor);
}

function openRooms() {
  let br = openBreakoutRoomsMenu();
  let b = getUnique(
    br.buttons.whose({ description: { "=": "Open All Rooms" } })
  );
  if (b == null) {
    return;
  }
  b.click();
}

function leaveMeeting() {
  let w = getUnique(app.windows.whose({ title: { "=": "Zoom Meeting" } }));
  if (w == null) {
    // not in a meeting
    return;
  }
  getUnique(w.buttons.whose({ description: { "=": "End" } })).click();
  delay(0.3 * patienceFactor);
  getUnique(
    app.windows[0].buttons.whose({ description: { "=": "Leave Meeting" } })
  ).click();
}

function joinMeeting() {
  let Zoom = Application("zoom.us");
  Zoom.includeStandardAdditions = true;
  Zoom.activate();
  Zoom.openLocation(
    "zoommtg://zoom.us/join?confno=" + meetingID + "&pwd=" + meetingPwd
  );
  waitForWindow({ title: { "=": "Zoom Meeting" } }, 5);
  // might still be connecting or something
  delay(1 * patienceFactor);
}

// use the "Recreate" button to load changed meeting settings
// assumes that breakout rooms have been closed
//
// this will go through the motions but not do anything if you
// haven't done one of : enter a breakout room, or leave/re-enter the meeting
function recreatePreAssigned() {
  let br = openBreakoutRoomsMenu();
  let b = getUnique(br.buttons.whose({ description: { "=": "Recreate" } }));
  b.click();
  // press down to navigate to "recover to pre-assigned rooms" then "enter",
  SystemEvents.keyCode([125, 36]);
  // and "enter" to confirm the dialog (delay is only so you can observe this working)
  delay(0.5 * patienceFactor);
  SystemEvents.keyCode([36]);
}

// automate the process of reloading from assigned rooms
function reload() {
  closeRooms();
  recreatePreAssigned();
  openRooms();
}

// join the "Discussion (paper ...)" room, if not already in a breakout room
//
// after doing this, recreating saved breakout rooms will actually change configurations
function joinBreakout() {
  if (
    app.windows.whose({ title: { _beginsWith: "Zoom Meeting -" } }).length > 0
  ) {
    // already in a breakout room
    return true;
  }
  let br = openBreakoutRoomsMenu();
  let rows = br.scrollAreas[0].tables[0].rows;
  for (var i = 0; i < rows.length; i++) {
    if (
      rows[i].uiElements[0].buttons[0].description().startsWith("Discussion")
    ) {
      rows[i].uiElements[0].buttons[1].click();
      delay(0.3 * patienceFactor);
      getUnique(app.windows[0].buttons.whose({ description: "Yes" })).click();
      waitForWindow({ title: { _beginsWith: "Zoom Meeting -" } }, 5);
      return true;
    }
  }
  console.log("discussion room not found");
  return false;
}

// we can't tell if UI corresponds to a room or a participant, so guess by the name...
//
// also normalizes "Discussion (paper ...)" to just "Discussion"
//
// returns null if not a room
function toRoomName(name) {
  if (name == null) {
    return null;
  }
  if (name == "Unassigned" || name == "Main Session") {
    return "Main Session";
  }
  if (name == "Conflict Room" || name == "Conflict") {
    return "Conflict Room";
  }
  if (name.startsWith("Discussion")) {
    return "Discussion";
  }
  return null;
}

// click on normalized room name in the "Move To" popup
function clickRoomInPopup(name) {
  // not a great way to identify the popup but better than just using windows[0]
  let chooseRoomWindow = waitForWindow({ title: "" }, 1);
  let rows = chooseRoomWindow.scrollAreas[0].tables[0].rows;
  for (var i = 0; i < rows.length; i++) {
    let b = rows[i].uiElements[0].buttons[0];
    let roomName = toRoomName(b.description());
    if (roomName == name) {
      b.click();
      return true;
    }
  }
  console.log("failed to find room " + name);
  // close popup even on failure to reset state
  SystemEvents.keyCode([53]);
  return false;
}

function _mapNextParticipant(roomForName, alreadyMoved) {
  let br = openBreakoutRoomsMenu();
  let rows = br.scrollAreas[0].tables[0].rows;
  var currentRoom = null;
  let startLength = rows.length;
  var numMoved = 0;
  for (var i = 0; i < rows.length; i++) {
    // UI might get invalidated by moving people around, don't take chances on
    // race conditions
    if (rows.length != startLength) {
      return false;
    }
    let name = rows[i].uiElements[0].buttons[0].description();
    if (name == null) {
      console.log("no description for row");
      continue;
    }
    if (name.startsWith("Tej Chajed")) {
      continue;
    }
    let room = toRoomName(name);
    if (room != null) {
      currentRoom = room;
      continue;
    }
    let desiredRoom = toRoomName(roomForName(name));
    if (desiredRoom == null) {
      console.log(
        name + " should go to non-existent room " + roomForName(name)
      );
      continue;
    }
    if (desiredRoom == currentRoom) {
      debugLog("participant " + name + " already in " + desiredRoom);
      continue;
    }
    if (name in alreadyMoved) {
      debugLog("skipping " + name + " (should have already moved them)");
      continue;
    }
    // check for a button (otherwise this is a weird row, possibly someone
    // currently moving)
    if (rows[i].uiElements[0].buttons.length == 2) {
      let b = rows[i].uiElements[0].buttons[1];
      if (!(b.description() == "Move To" || b.description() == "Assign To")) {
        console.log("unexpected move to button " + b.description());
        continue;
      }
      console.log(
        ["moving", name, "from", currentRoom, "to", desiredRoom].join(" ")
      );
      b.click();
      if (!clickRoomInPopup(desiredRoom)) {
        return false;
      }
      alreadyMoved[name] = true;
      numMoved += 1;
      // UI is probably messed up by now, wait a bit
      if (numMoved >= 4) {
        return false;
      }
    }
  }
  return true;
}

function mapAllParticipants(roomForName) {
  var alreadyMoved = {};
  while (!_mapNextParticipant(roomForName, alreadyMoved)) {
    debugLogging("waiting for stability...");
    delay(3 * patienceFactor);
  }
}

function moveAllByRoom(nameTokenToRoomJSON) {
  let nameTokenToRoom = JSON.parse(nameTokenToRoomJSON);
  mapAllParticipants((name) => {
    let tokens = name.split(/[ ()]/);
    let rooms = [];
    for (const token of tokens) {
      let room = nameTokenToRoom[token];
      if (room === undefined) {
        continue;
      }
      if (!rooms.includes(room)) {
        rooms.push(room);
      }
    }
    if (rooms.length == 0) {
      console.log("no room for " + name);
      return null;
    }
    if (rooms.length > 1) {
      console.log("too many rooms for " + name);
      console.log(rooms);
      return null;
    }
    return rooms[0];
  });
}

function runCommand(command, arg) {
  let wait = () => {
    console.log("wait 1s");
    delay(1);
  };

  let commands = {
    close: closeRooms,
    recreate: recreatePreAssigned,
    open: openRooms,
    reload: reload,
    leave: leaveMeeting,
    join: joinMeeting,
    wait: wait,
    joinBreakout: joinBreakout,
    "moveTo=": moveAllByRoom,
  };
  if (!commands.hasOwnProperty(command)) {
    throw "unknown command '" + command + "'";
  }
  if (arg != null) {
    commands[command](arg);
  } else {
    commands[command]();
  }
}

function run(argv) {
  if (argv.length == 0) {
    console.log(
      "Use close/recreate/open/reload/joinBreakout/moveTo=/leave/join commands"
    );
    console.log("reload is a convenience for close recreate open");
  }
  for (var i = 0; i < argv.length; i++) {
    let command = argv[i];
    if (command.endsWith("=")) {
      if (!(i + 1 < argv.length)) {
        throw "command " + command + " takes an argument";
      }
      let arg = argv[i + 1];
      runCommand(command, arg);
      i++;
    } else {
      runCommand(command);
    }
  }
}

// debugging (final result is displayed in Script Editor output)

// mapAllParticipants((name) => { return "Discussion"; })

// let br = openBreakoutRoomsMenu();
// let rows = br.scrollAreas[0].tables[0].rows;

// br.scrollAreas[0].tables[0].rows[7].entireContents()
