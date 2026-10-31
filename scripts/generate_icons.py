"""Generate PNG icons from scratch for the PWA using Python standard library."""
import math
import struct
import zlib
from pathlib import Path

def create_png(width, height, pixel_fn):
    """Generate a PNG byte string where pixel_fn(x, y) returns (r, g, b, a) in 0..255."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        for x in range(width):
            r, g, b, a = pixel_fn(x, y)
            raw.extend((r, g, b, a))
    
    compressed = zlib.compress(bytes(raw), 9)
    
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    header = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return header + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

def render_icon(size, maskable=False):
    cx = size / 2.0
    cy = size / 2.0
    s = size / 512.0

    # Colors
    c_spruce = (29, 74, 68, 255)
    c_spruce_dark = (18, 52, 48, 255)
    c_spruce_mid = (36, 90, 83, 255)
    c_white = (254, 254, 254, 255)
    c_gold = (233, 185, 30, 255)
    c_blue = (43, 108, 222, 255)
    c_grass1 = (104, 211, 145, 255)
    c_grass2 = (72, 187, 120, 255)
    c_dark_outline = (21, 38, 43, 255)

    def get_color(x, y):
        # Coordinates normalized to 512x512
        nx = x / s
        ny = y / s

        if maskable:
            # Full bleed background for maskable icon
            base_r, base_g, base_b = c_spruce[0], c_spruce[1], c_spruce[2]
        else:
            # Rounded rect background (radius ~100)
            # Box from 10 to 502
            bx0, by0, bx1, by1 = 16, 16, 496, 496
            rad = 100
            # Test if inside rounded rect
            dx = max(bx0 + rad - nx, 0, nx - (bx1 - rad))
            dy = max(by0 + rad - ny, 0, ny - (by1 - rad))
            dist = math.hypot(dx, dy)
            if dist > rad:
                return (0, 0, 0, 0)
            base_r = int(29 - (ny / 512.0) * 12)
            base_g = int(74 - (ny / 512.0) * 26)
            base_b = int(68 - (ny / 512.0) * 25)

        # Ring / decorative circle
        dist_c = math.hypot(nx - 256, ny - 256)
        if 154 <= dist_c <= 166:
            angle = math.atan2(ny - 256, nx - 256)
            # Dashed pattern
            if int((angle + math.pi) / (math.pi / 8)) % 2 == 0:
                base_r = int(base_r * 0.7 + 163 * 0.3)
                base_g = int(base_g * 0.7 + 196 * 0.3)
                base_b = int(base_b * 0.7 + 184 * 0.3)

        # Center blaze marker
        # Pill: x in [226, 286], y in [120, 260], rx=12
        # Outline: x in [222, 290], y in [116, 264]
        if 222 <= nx <= 290 and 116 <= ny <= 264:
            # Check outline or inner
            if nx <= 226 or nx >= 286 or ny <= 120 or ny >= 260:
                return c_dark_outline
            # Inside blaze
            if 126 <= ny <= 184 and 234 <= nx <= 278:
                return c_gold
            elif 194 <= ny <= 252 and 234 <= nx <= 278:
                return c_blue
            elif (120 <= ny <= 126) or (184 < ny < 194) or (252 <= ny <= 260) or nx < 234 or nx > 278:
                return c_white

        # Grass blades at the bottom:
        # Left leaf curve
        # Approx polygon / curve for left blade:
        # nx in [165..256], ny in [265..390]
        # Check leaf shapes using quadratic/bezier distance or implicit approximation
        # Leaf 1 (Left): center around (210, 320)
        lx = (nx - 160) / 96.0
        ly = (ny - 265) / 125.0
        if 0.0 <= lx <= 1.0 and 0.0 <= ly <= 1.0:
            # leaf shape boundary: width widest near middle
            w = math.sin(ly * math.pi) * 0.65
            center_x = 0.2 + ly * 0.8
            if abs(lx - center_x) < w:
                edge = abs(lx - center_x) / max(w, 0.01)
                if edge > 0.85:
                    return c_dark_outline
                return c_grass1

        # Leaf 2 (Right):
        rx = (nx - 256) / 96.0
        ry = (ny - 255) / 135.0
        if 0.0 <= rx <= 1.0 and 0.0 <= ry <= 1.0:
            w = math.sin(ry * math.pi) * 0.65
            center_x = 0.8 - ry * 0.8
            if abs(rx - center_x) < w:
                edge = abs(rx - center_x) / max(w, 0.01)
                if edge > 0.85:
                    return c_dark_outline
                return c_grass2

        # Central sprout stem
        if 253 <= nx <= 259 and 260 <= ny <= 390:
            return (56, 161, 105, 255)

        # Base soil shadow
        if 392 <= ny <= 408:
            dist_soil = math.hypot((nx - 256) / 60.0, (ny - 400) / 8.0)
            if dist_soil <= 1.0:
                return c_spruce_dark

        return (base_r, base_g, base_b, 255)

    return create_png(size, size, get_color)

def main():
    icons_dir = Path(__file__).resolve().parent.parent / "static" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating 192x192 icon...")
    png_192 = render_icon(192, maskable=False)
    (icons_dir / "icon-192.png").write_bytes(png_192)

    print("Generating 512x512 icon...")
    png_512 = render_icon(512, maskable=False)
    (icons_dir / "icon-512.png").write_bytes(png_512)

    print("Generating 512x512 maskable icon...")
    png_maskable = render_icon(512, maskable=True)
    (icons_dir / "icon-maskable-512.png").write_bytes(png_maskable)

    print("Generating apple-touch-icon (180x180)...")
    png_apple = render_icon(180, maskable=False)
    (icons_dir / "apple-touch-icon.png").write_bytes(png_apple)

    # Also save standard favicon.ico (16x16 / 32x32 simple format)
    # A 32x32 icon inside standard ico
    png_32 = render_icon(32, maskable=False)
    # Write as icon-32.png and apple-touch-icon in static
    (icons_dir / "icon-32.png").write_bytes(png_32)
    
    print("All icons successfully generated!")

if __name__ == "__main__":
    main()
