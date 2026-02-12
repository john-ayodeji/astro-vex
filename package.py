import os
import platform
import subprocess
import sys
from importlib.util import find_spec

APP_NAME = "astro-vex"
SERVER_NAME = "astro-vex-server"
CLIENT_ENTRYPOINT = "main.py"
SERVER_ENTRYPOINT = "multiplayer_server.py"
ICON_PATH = os.path.join("assets", "app_icon.ico")


def build_client():
    if not os.path.exists(CLIENT_ENTRYPOINT):
        raise SystemExit(f"Missing entrypoint: {CLIENT_ENTRYPOINT}")

    if find_spec("pygame") is None:
        raise SystemExit(
            "Cannot build client exe: pygame is not installed in this Python environment.\n"
            "Install dependencies first (e.g. `python -m pip install -e .`) and retry."
        )

    separator = ";" if os.name == "nt" else ":"
    add_data = f"assets{separator}assets"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--collect-all",
        "pygame",
        "--add-data",
        add_data,
        CLIENT_ENTRYPOINT,
    ]

    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    print("[client] Running:", " ".join(cmd))
    subprocess.check_call(cmd)

    print("\nClient build complete.")
    if platform.system() == "Windows":
        print(f"Executable: dist\\{APP_NAME}.exe")
    else:
        print(f"Executable: dist/{APP_NAME}")


def build_server():
    if not os.path.exists(SERVER_ENTRYPOINT):
        raise SystemExit(f"Missing entrypoint: {SERVER_ENTRYPOINT}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        SERVER_NAME,
        SERVER_ENTRYPOINT,
    ]
    print("[server] Running:", " ".join(cmd))
    subprocess.check_call(cmd)

    print("\nServer build complete.")
    if platform.system() == "Windows":
        print(f"Executable: dist\\{SERVER_NAME}.exe")
    else:
        print(f"Executable: dist/{SERVER_NAME}")


def main():
    target = "all"
    if len(sys.argv) > 1:
        target = sys.argv[1].lower().strip()

    if target not in {"client", "server", "all"}:
        raise SystemExit("Usage: python package.py [client|server|all]")

    if target in {"client", "all"}:
        build_client()
    if target in {"server", "all"}:
        build_server()


if __name__ == "__main__":
    main()
