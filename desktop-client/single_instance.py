from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Callable

from PySide6.QtCore import QObject, QLockFile, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceManager(QObject):
    def __init__(self, name: str, parent: QObject | None = None):
        super().__init__(parent)
        temp_dir = Path(tempfile.gettempdir())
        self.server_name = name
        self.lock = QLockFile(str(temp_dir / f"{name}.lock"))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._handle_new_connection)
        self._activation_callback: Callable[[str], None] | None = None

    def set_activation_callback(self, callback: Callable[[str], None]) -> None:
        self._activation_callback = callback

    def acquire(self) -> bool:
        if self.lock.tryLock(100):
            QLocalServer.removeServer(self.server_name)
            if not self.server.listen(self.server_name):
                self.lock.unlock()
                return False
            return True

        if self.activate_existing_instance():
            return False

        self.lock.removeStaleLockFile()
        if not self.lock.tryLock(100):
            return False
        QLocalServer.removeServer(self.server_name)
        if not self.server.listen(self.server_name):
            self.lock.unlock()
            return False
        return True

    def activate_existing_instance(self, payload: str = "activate") -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(600):
            return False
        socket.write(payload.encode("utf-8"))
        socket.flush()
        socket.waitForBytesWritten(600)
        socket.disconnectFromServer()
        return True

    @Slot()
    def _handle_new_connection(self) -> None:
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            if socket is None:
                continue
            if not socket.waitForReadyRead(1000):
                socket.disconnectFromServer()
                continue
            payload = bytes(socket.readAll()).decode("utf-8", errors="ignore")
            socket.disconnectFromServer()
            if self._activation_callback is not None:
                self._activation_callback(payload or "activate")
