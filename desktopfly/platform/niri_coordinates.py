"""Locate XWayland brain windows in Niri's global monitor coordinates."""

import json
import os
import socket
import time


class NiriCoordinates:
    def __init__(self, parent):
        self.parent = parent
        self.toplevels = {parent.get_window().get_xid(): parent}
        self.rows = []
        self.checked = 0.0
        self.outputs = {}
        self.workspaces = []
        self.topology_checked = 0.0

    def windows(self):
        now = time.monotonic()
        if now - self.checked < 0.025:
            return self.rows
        self.checked = now
        try:
            self.rows = self.request("Windows")
            if now - self.topology_checked > 0.5:
                self.outputs = self.request("Outputs")
                self.workspaces = self.request("Workspaces")
                self.topology_checked = now
        except (OSError, ValueError, KeyError):
            pass
        return self.rows

    @staticmethod
    def request(kind):
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(0.1)
            connection.connect(os.environ["NIRI_SOCKET"])
            connection.sendall((json.dumps(kind) + "\n").encode())
            with connection.makefile("rb") as stream:
                return json.loads(stream.readline())["Ok"][kind]

    def origin(self, window=None):
        window = window or self.parent
        title = window.get_title()
        for row in self.windows():
            if row["title"] == title:
                layout = row["layout"]
                position = layout.get("tile_pos_in_workspace_view")
                if position is not None:
                    offset = layout["window_offset_in_tile"]
                    workspace = next((w for w in self.workspaces if w["id"] == row["workspace_id"]), {})
                    output = self.outputs.get(workspace.get("output"), {}).get("logical") or {}
                    return (output.get("x", 0) + position[0] + offset[0],
                            output.get("y", 0) + position[1] + offset[1])
        _ok, x, y = window.get_window().get_origin()
        return x, y

    def pointer(self, pointer):
        child = getattr(pointer.child, "id", 0)
        window = self.toplevels.get(child)
        if window is not None:
            _ok, x, y = window.get_window().get_origin()
            actual_x, actual_y = self.origin(window)
            dx, dy = actual_x - x, actual_y - y
            return pointer.root_x + dx, pointer.root_y + dy
        return pointer.root_x, pointer.root_y
