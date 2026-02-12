import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(ROOT, "assets")
PNG_PATH = os.path.join(ASSETS_DIR, "app_icon.png")
ICO_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")


def _chunk(tag, data):
    body = tag + data
    return (
        struct.pack(">I", len(data))
        + body
        + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    )


def _point_in_polygon(x, y, points):
    inside = False
    n = len(points)
    j = n - 1
    for i in range(n):
        xi, yi = points[i]
        xj, yj = points[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _dist_sq(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def generate_png(path):
    width = 256
    height = 256
    pixels = [[(0, 0, 0, 0) for _ in range(width)] for _ in range(height)]

    cx = width // 2
    cy = height // 2
    r_outer = 124
    r_inner = 102

    for y in range(height):
        for x in range(width):
            d2 = _dist_sq(x, y, cx, cy)
            if d2 <= r_outer * r_outer:
                pixels[y][x] = (8, 20, 45, 255)
            if d2 <= r_inner * r_inner:
                pixels[y][x] = (12, 35, 72, 255)

    for i in range(28):
        sx = (i * 37) % 240 + 8
        sy = (i * 61) % 240 + 8
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1):
                px = sx + ox
                py = sy + oy
                if 0 <= px < width and 0 <= py < height and ox * ox + oy * oy <= 1:
                    pixels[py][px] = (210, 225, 255, 255)

    body = [(128, 48), (172, 160), (150, 154), (128, 186), (106, 154), (84, 160)]
    for y in range(height):
        for x in range(width):
            if _point_in_polygon(x, y, body):
                pixels[y][x] = (52, 211, 153, 255)

    cockpit_cx, cockpit_cy, cockpit_r = 128, 118, 16
    for y in range(height):
        for x in range(width):
            d2 = _dist_sq(x, y, cockpit_cx, cockpit_cy)
            if d2 <= cockpit_r * cockpit_r:
                pixels[y][x] = (34, 211, 238, 255)
            if cockpit_r * cockpit_r - 3 * cockpit_r <= d2 <= cockpit_r * cockpit_r + 3 * cockpit_r:
                pixels[y][x] = (240, 248, 255, 255)

    flame = [(120, 188), (128, 226), (136, 188)]
    for y in range(height):
        for x in range(width):
            if _point_in_polygon(x, y, flame):
                pixels[y][x] = (34, 211, 238, 255)

    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend((r, g, b, a))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_chunk(b"IHDR", ihdr))
    png.extend(_chunk(b"IDAT", zlib.compress(bytes(raw), level=9)))
    png.extend(_chunk(b"IEND", b""))

    with open(path, "wb") as f:
        f.write(png)


def png_to_ico(png_path, ico_path):
    with open(png_path, "rb") as f:
        png_data = f.read()

    # ICO header + one PNG image entry
    # ICONDIR: Reserved(2), Type(2), Count(2)
    icon_dir = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY:
    # Width(1)=0 for 256, Height(1)=0 for 256, ColorCount(1), Reserved(1),
    # Planes(2), BitCount(2), BytesInRes(4), ImageOffset(4)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png_data), 6 + 16)

    with open(ico_path, "wb") as f:
        f.write(icon_dir)
        f.write(entry)
        f.write(png_data)


def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    generate_png(PNG_PATH)
    png_to_ico(PNG_PATH, ICO_PATH)
    print(f"Generated {PNG_PATH}")
    print(f"Generated {ICO_PATH}")


if __name__ == "__main__":
    main()
