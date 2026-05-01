import asyncio
import base64
import json
import logging
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

logger = logging.getLogger("HLL.Sync")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setLevel(logging.DEBUG)
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_h)
    # Also write to a log file in case stdout is not visible (Qt on Windows)
    _log_dir = Path(__file__).resolve().parent / "logs"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_path = _log_dir / "sync_debug.log"
    _fh = logging.FileHandler(str(_log_path), encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_fh)
    logger.info(f"Logging to {_log_path}")

from aiortc import RTCConfiguration, RTCIceServer

from sync.viewer_page import write_session_viewer


class DesktopSyncManager:
    def __init__(self, project_dir, config):
        self.project_dir = Path(project_dir)
        self.config = config

        self._thread = None
        self._loop = None
        self._stop_event = threading.Event()
        self._asset_queue = queue.Queue()
        self._state_lock = threading.Lock()
        self._latest_state = None

        self._peer = None
        self._connection = None
        self._session_peer_id = None
        self._viewer_file = None
        self._status = "idle"
        self._last_error = ""
        self._connected_peer_label = ""
        self._seq = 0

        self._on_status = None
        self._peer_module = None
        self._peer_event_type = None
        self._connection_event_type = None
        self._peer_options_type = None

    @property
    def status(self):
        return self._status

    @property
    def peer_id(self):
        return self._session_peer_id or ""

    @property
    def viewer_file(self):
        return self._viewer_file

    @property
    def last_error(self):
        return self._last_error

    @property
    def connection_label(self):
        return self._connected_peer_label

    def set_status_callback(self, callback):
        self._on_status = callback

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running():
            return False

        try:
            self._import_backend()
        except Exception as exc:
            self._set_status("missing_dependency", str(exc))
            return False

        self._stop_event.clear()
        self._latest_state = None
        self._session_peer_id = self._generate_peer_id()
        self._viewer_file = self._prepare_viewer_file()
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()
        self._set_status("starting", "")
        return True

    def stop(self):
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(lambda: None)
        self._set_status("stopping", "")

    def publish_state(self, state):
        if not self.is_running():
            return

        payload = {
            "type": "state",
            "seq": self._next_seq(),
            "timestampMs": int(time.time() * 1000),
            "payload": state,
        }
        with self._state_lock:
            self._latest_state = payload

    def publish_asset(self, name, image_bytes, width_px, height_px, mime_type="image/jpeg"):
        """Enqueue an asset for publishing. Runs on the main thread.
        Raw bytes are queued; base64 encoding and chunking happen
        later on the sync thread to avoid blocking the UI."""
        if not self.is_running():
            logger.warning(f"SYNC-DIAG publish_asset({name!r}) skipped: not running")
            return

        logger.info(f"SYNC-DIAG publish_asset({name!r}) raw={len(image_bytes)}B dims={width_px}x{height_px} mime={mime_type}")
        job = {
            "type": "asset_job",
            "name": name,
            "image_bytes": image_bytes,
            "width_px": width_px,
            "height_px": height_px,
            "mime_type": mime_type,
        }
        self._asset_queue.put(job)

    async def _process_asset_job(self, job):
        """Run on the sync thread: base64-encode, split into chunks, send all.
        This moves CPU-heavy base64 encoding off the Qt main thread."""
        name = job["name"]
        image_bytes = job["image_bytes"]
        mime_type = job["mime_type"]
        width_px = job["width_px"]
        height_px = job["height_px"]

        base64_data = base64.b64encode(image_bytes).decode("ascii")
        chunk_size = 15000
        total = max(1, (len(base64_data) + chunk_size - 1) // chunk_size)

        logger.info(
            f"SYNC-DIAG _process_asset_job({name!r}) "
            f"raw={len(image_bytes)}B base64={len(base64_data)}chars "
            f"chunks={total} dims={width_px}x{height_px} mime={mime_type}"
        )

        for i in range(total):
            chunk = base64_data[i * chunk_size:(i + 1) * chunk_size]
            payload = {
                "type": "asset_chunk",
                "seq": self._next_seq(),
                "timestampMs": int(time.time() * 1000),
                "name": name,
                "index": i,
                "total": total,
                "mimeType": mime_type,
                "widthPx": width_px,
                "heightPx": height_px,
                "encoding": "base64",
                "data": chunk,
            }
            await self._send_payload(payload)
        logger.info(f"SYNC-DIAG _process_asset_job({name!r}) sent {total} chunks")

    def clear_asset(self, name):
        if not self.is_running():
            logger.warning(f"SYNC-DIAG clear_asset({name!r}) skipped: not running")
            return

        logger.info(f"SYNC-DIAG clear_asset({name!r})")
        payload = {
            "type": "clear_asset",
            "seq": self._next_seq(),
            "timestampMs": int(time.time() * 1000),
            "name": name,
        }
        self._asset_queue.put(payload)

    def _next_seq(self):
        self._seq += 1
        return self._seq

    def _generate_peer_id(self):
        return f"hll-{uuid.uuid4().hex}"

    def _prepare_viewer_file(self):
        sessions_dir = self.project_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        output_path = sessions_dir / f"mobile_viewer_{self._session_peer_id}.html"
        return write_session_viewer(
            output_path,
            peer_id=self._session_peer_id,
            signal_host=self.config["SYNC_SIGNAL_HOST"],
            signal_port=self.config["SYNC_SIGNAL_PORT"],
            signal_path=self.config["SYNC_SIGNAL_PATH"],
            secure=self.config["SYNC_SIGNAL_SECURE"],
        )

    def _thread_main(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_main())
        except Exception as exc:
            self._set_status("error", str(exc))
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self._loop.close()
            self._loop = None
            self._peer = None
            self._connection = None
            self._connected_peer_label = ""
            self._thread = None
            if self._status not in {"error", "missing_dependency"}:
                self._set_status("stopped", "")

    def _build_rtc_configuration(self):
        ice_servers = []
        for server in self.config["SYNC_ICE_SERVERS"]:
            urls = server["urls"]
            username = server.get("username")
            credential = server.get("credential")
            credential_type = server.get("credentialType", "password")
            if isinstance(urls, list):
                for url in urls:
                    ice_servers.append(RTCIceServer(
                        urls=url, username=username,
                        credential=credential, credentialType=credential_type,
                    ))
            else:
                ice_servers.append(RTCIceServer(
                    urls=urls, username=username,
                    credential=credential, credentialType=credential_type,
                ))
        return RTCConfiguration(iceServers=ice_servers)

    async def _async_main(self):
        peer_options = self._peer_options_type(
            host=self.config["SYNC_SIGNAL_HOST"],
            port=self.config["SYNC_SIGNAL_PORT"],
            path=self.config["SYNC_SIGNAL_PATH"],
            secure=self.config["SYNC_SIGNAL_SECURE"],
            key=self.config["SYNC_SIGNAL_KEY"],
            debug=self.config["SYNC_DEBUG_LEVEL"],
            config=self._build_rtc_configuration(),
        )

        peer_type = self._peer_module.Peer
        self._peer = peer_type(self._session_peer_id, peer_options)
        self._bind_peer_events()

        await self._peer.start()
        while not self._stop_event.is_set():
            await self._flush_asset_messages()
            await self._flush_latest_state()
            await asyncio.sleep(1.0 / self.config["SYNC_STATE_FPS"])

        await self._shutdown_peer()

    async def _shutdown_peer(self):
        try:
            if self._connection is not None:
                await self._connection.close()
        except Exception:
            pass

        try:
            if self._peer is not None:
                await self._peer.destroy()
        except Exception:
            pass

    async def _flush_asset_messages(self):
        if self._connection is None:
            # Drain asset_jobs to avoid unbounded memory from raw image bytes
            while not self._asset_queue.empty():
                item = self._asset_queue.get_nowait()
                if item.get("type") == "asset_job":
                    logger.debug(f"SYNC-DIAG _flush_assets: no connection, dropping asset_job {item.get('name')}")
            return
        count = 0
        while not self._asset_queue.empty():
            item = self._asset_queue.get_nowait()
            if item.get("type") == "asset_job":
                await self._process_asset_job(item)
            else:
                await self._send_payload(item)
            count += 1
        if count:
            logger.info(f"SYNC-DIAG _flush_assets: processed {count} items")

    async def _flush_latest_state(self):
        with self._state_lock:
            payload = self._latest_state
            self._latest_state = None
        if payload is not None:
            await self._send_payload(payload)

    async def _send_payload(self, payload):
        connection = self._connection
        if connection is None:
            logger.warning(f"SYNC-DIAG _send_payload: connection is None, dropping msg type={payload.get('type')}")
            return

        msg_type = payload.get("type", "?")
        chunk_info = ""
        if msg_type == "asset_chunk":
            chunk_info = f" name={payload.get('name')} idx={payload.get('index')}/{payload.get('total')} data_len={len(payload.get('data',''))}"
        elif msg_type == "state":
            chunk_info = f" seq={payload.get('seq')}"
        elif msg_type == "clear_asset":
            chunk_info = f" name={payload.get('name')}"

        try:
            await connection.send(payload)
            logger.debug(f"SYNC-DIAG _send OK: type={msg_type}{chunk_info}")
        except Exception as exc:
            logger.error(f"SYNC-DIAG _send FAIL: type={msg_type}{chunk_info} err={exc}")
            self._set_status("error", f"Send failed: {exc}")

    def _bind_peer_events(self):
        peer = self._peer

        def on_open(peer_id):
            self._set_status("waiting_client", "")
            self._session_peer_id = peer_id

        def on_connection(connection):
            asyncio.create_task(self._handle_incoming_connection(connection))

        def on_error(error):
            self._set_status("error", str(error))

        def on_close():
            if not self._stop_event.is_set():
                self._set_status("closed", "")

        def on_disconnected(_peer_id):
            if not self._stop_event.is_set():
                self._set_status("disconnected", "")

        peer.on(self._peer_event_type.Open.value, on_open)
        peer.on(self._peer_event_type.Connection.value, on_connection)
        peer.on(self._peer_event_type.Error.value, on_error)
        peer.on(self._peer_event_type.Close.value, on_close)
        peer.on(self._peer_event_type.Disconnected.value, on_disconnected)

    async def _handle_incoming_connection(self, connection):
        logger.info(f"SYNC-DIAG _handle_incoming_connection called, existing_conn={self._connection is not None}, conn_type={type(connection).__name__}, serialization={getattr(connection, 'serialization', '?')}")

        if self._connection is not None:
            logger.warning(f"SYNC-DIAG _handle_incoming_connection: already connected, rejecting new connection")
            try:
                await connection.close()
            except Exception:
                pass
            return

        self._connection = connection
        self._connected_peer_label = getattr(connection, "peer", "mobile-client")
        self._set_status("connected", "")
        logger.info(f"SYNC-DIAG connection set, queue_depth={self._asset_queue.qsize()}")

        def on_close():
            self._connection = None
            self._connected_peer_label = ""
            if not self._stop_event.is_set():
                self._set_status("waiting_client", "")

        def on_error(error):
            self._set_status("error", str(error))

        connection.on(self._connection_event_type.Close.value, on_close)
        connection.on(self._connection_event_type.Error.value, on_error)

        await self._send_payload(
            {
                "type": "hello",
                "seq": self._next_seq(),
                "timestampMs": int(time.time() * 1000),
                "payload": {
                    "peerId": self._session_peer_id,
                    "protocolVersion": 1,
                    "mode": "one-source-one-client",
                },
            }
        )

    def _import_backend(self):
        if self._peer_module is not None:
            return

        from peerjs_py import enums as peer_enums
        from peerjs_py import peer as peer_module

        self._peer_module = peer_module
        self._peer_event_type = peer_enums.PeerEventType
        self._connection_event_type = peer_enums.ConnectionEventType
        self._peer_options_type = peer_module.PeerOptions

    def _set_status(self, status, error_message):
        self._status = status
        self._last_error = error_message or ""
        callback = self._on_status
        if callback is not None:
            callback(status, self._last_error)

