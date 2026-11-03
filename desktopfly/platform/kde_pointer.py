"""Read KDE's cursor even when it is over a native Wayland surface."""

import atexit
import os
import tempfile
from pathlib import Path

from .gtkcompat import Gio, GLib


class KDEPointer:
    def __init__(self):
        self.position = None
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.name = f"desktopfly-pointer-{os.getpid()}"
        self.registration = None
        self.script_path = None
        try:
            info = Gio.DBusNodeInfo.new_for_xml(
                '<node><interface name="org.desktopfly.Pointer">'
                '<method name="Update"><arg type="i" direction="in"/>'
                '<arg type="i" direction="in"/></method></interface></node>'
            )
            self.registration = self.bus.register_object(
                '/org/desktopfly/Pointer', info.interfaces[0], self._update, None, None
            )
            destination = self.bus.get_unique_name()
            script = f'''
function update() {{
    var p = workspace.cursorPos;
    callDBus("{destination}", "/org/desktopfly/Pointer",
             "org.desktopfly.Pointer", "Update", p.x, p.y);
}}
workspace.cursorPosChanged.connect(update);
update();
'''
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(script)
                self.script_path = Path(f.name)
            result = self._call('/Scripting', 'org.kde.kwin.Scripting', 'loadScript',
                                GLib.Variant('(ss)', (str(self.script_path), self.name)))
            script_id = result.unpack()[0]
            if script_id < 0:
                raise RuntimeError('KWin rejected cursor script')
            self._call(f'/Scripting/Script{script_id}', 'org.kde.kwin.Script', 'run')
        except Exception:
            self.close()
            raise
        atexit.register(self.close)

    def _call(self, path, interface, method, args=None):
        return self.bus.call_sync('org.kde.KWin', path, interface, method, args,
                                  None, Gio.DBusCallFlags.NONE, 2000, None)

    def _update(self, _bus, _sender, _path, _interface, _method, args, invocation):
        self.position = tuple(args.unpack())
        invocation.return_value(None)

    def close(self):
        try:
            self._call('/Scripting', 'org.kde.kwin.Scripting', 'unloadScript',
                       GLib.Variant('(s)', (self.name,)))
        except GLib.Error:
            pass
        if self.registration is not None:
            self.bus.unregister_object(self.registration)
            self.registration = None
        if self.script_path is not None:
            self.script_path.unlink(missing_ok=True)
            self.script_path = None
