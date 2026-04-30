from pathlib import Path


VIEWER_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "web" / "mobile_viewer.html"


def build_session_viewer(peer_id, signal_host, signal_port, signal_path, secure):
    template = VIEWER_TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__DEFAULT_PEER_ID__": peer_id,
        "__SIGNAL_HOST__": signal_host,
        "__SIGNAL_PORT__": str(signal_port),
        "__SIGNAL_PATH__": signal_path,
        "__SIGNAL_SECURE__": "true" if secure else "false",
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def write_session_viewer(output_path, peer_id, signal_host, signal_port, signal_path, secure):
    html = build_session_viewer(peer_id, signal_host, signal_port, signal_path, secure)
    output_path.write_text(html, encoding="utf-8")
    return output_path
