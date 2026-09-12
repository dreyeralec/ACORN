import logging
import threading

from src.ib import IBApp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ACORN")

_app: IBApp | None = None
_lock = threading.Lock()


def run_loop(app):
    app.run()


def connect_ib_gateway(host="127.0.0.1", port=4002, client_id=1, timeout=10) -> IBApp:
    """Connect client to IB Gateway, or return the existing connection.

        Subsequent calls (from any module) return the same IBApp instance
        instead of opening a new connection. Pass force_new=True (or call
        disconnect_ib() first) if you actually need a fresh connection.

        Args:
            host: Host ip address of gateway
            port: Port to connect to gateway on (4001: live, 4002: paper)
            client_id: Client id to start the connection with (gets incremented during session)
            timeout: Connection wide timeout window value

        Returns:
            IBApp object

        Raises:
            ConnectionError: Fails to connect within timeout
    """
    global _app

    # Fast path: already connected, no lock needed for the common case
    if _app is not None and _app.isConnected():
        return _app

    with _lock:
        # Re-check inside the lock in case another thread just connected
        if _app is not None and _app.isConnected():
            return _app

        app = IBApp()
        app.connect(host, port, clientId=client_id)
        thread = threading.Thread(target=run_loop, args=(app,), daemon=True)
        thread.start()

        if not app.connected_event.wait(timeout=timeout):
            logger.error("Failed to connect to gateway within timeout")
            raise ConnectionError

        _app = app
        return _app


def disconnect_ib_gateway() -> None:
    global _app
    with _lock:
        if _app is not None:
            _app.disconnect()
            _app = None