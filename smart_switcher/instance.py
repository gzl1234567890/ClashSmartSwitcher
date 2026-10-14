import hashlib

from PySide6.QtCore import QObject, QLockFile, QTimer, Signal
from PySide6.QtNetwork import QHostAddress, QLocalServer, QLocalSocket, QTcpServer, QTcpSocket


class SingleInstance(QObject):
    show_requested = Signal()

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        directory.mkdir(parents=True, exist_ok=True)
        suffix = hashlib.sha256(str(directory.resolve()).casefold().encode()).hexdigest()[:20]
        self.name = "ClashSmartSwitcher-" + suffix
        self.lock = QLockFile(str(directory / "instance.lock"))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self.tcp_server = QTcpServer(self)
        self.tcp_server.newConnection.connect(self._accept_tcp)
        digest = int(suffix[-8:], 16)
        self.tcp_port = 39000 + digest % 20000
        self.owned = False
        self.sockets = set()
        self.tcp_sockets = set()
        self.notification = None

    def acquire(self):
        if not self.lock.tryLock(0):
            connection = QLocalSocket(self)
            self.notification = connection
            connection.connectToServer(self.name)
            if connection.waitForConnected(1000):
                connection.write(b"show\n")
                connection.flush()
                if connection.bytesToWrite():
                    connection.waitForBytesWritten(1000)
                # Keep the sender alive until the receiver acknowledges delivery.
                connection.readyRead.connect(connection.disconnectFromServer)
                return False
            tcp_connection = QTcpSocket(self)
            self.notification = tcp_connection
            tcp_connection.connectToHost(QHostAddress.LocalHost, self.tcp_port)
            if tcp_connection.waitForConnected(1000):
                tcp_connection.write(b"show\n")
                tcp_connection.flush()
                if tcp_connection.bytesToWrite():
                    tcp_connection.waitForBytesWritten(1000)
                tcp_connection.readyRead.connect(tcp_connection.disconnectFromHost)
            return False
        self.owned = True
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            # Some locked-down Windows environments reject Qt's named-pipe
            # security descriptor. The lock still enforces single ownership;
            # use a loopback TCP channel for the optional wake-up message.
            if not self.tcp_server.listen(QHostAddress.LocalHost, self.tcp_port):
                self.tcp_server.close()
        return True

    def _accept(self):
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            self.sockets.add(connection)
            connection.readyRead.connect(lambda c=connection: self._read(c))
            connection.disconnected.connect(lambda c=connection: self._discard(c))
            timeout = QTimer(connection)
            timeout.setSingleShot(True)
            timeout.timeout.connect(connection.disconnectFromServer)
            timeout.start(2000)
            self._read(connection)

    def _accept_tcp(self):
        while self.tcp_server.hasPendingConnections():
            connection = self.tcp_server.nextPendingConnection()
            self.tcp_sockets.add(connection)
            connection.readyRead.connect(lambda c=connection: self._read(c))
            connection.disconnected.connect(lambda c=connection: self._discard_tcp(c))
            timeout = QTimer(connection)
            timeout.setSingleShot(True)
            timeout.timeout.connect(connection.disconnectFromHost)
            timeout.start(2000)
            self._read(connection)

    def _read(self, connection):
        if connection.canReadLine() and bytes(connection.readLine(64)).strip() == b"show":
            self.show_requested.emit()
            connection.write(b"ok\n")
            connection.flush()

    def _discard(self, connection):
        self.sockets.discard(connection)
        connection.deleteLater()

    def _discard_tcp(self, connection):
        self.tcp_sockets.discard(connection)
        connection.deleteLater()

    def release(self):
        if self.owned:
            self.server.close()
            self.tcp_server.close()
            QLocalServer.removeServer(self.name)
            self.lock.unlock()
            self.owned = False
