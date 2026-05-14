"""Extract the icon image from an Amiga OS 2.x .info file and save as PNG + ICO.

The .info format: 78-byte DiskObject (with embedded 44-byte Gadget),
optional 56-byte DrawerData, then for each non-NULL gadget Render:
  - 20-byte Image header (LeftEdge, TopEdge, Width, Height, Depth,
    ImageData ptr, PlanePick, PlaneOnOff, NextImage ptr)
  - planar bitmap data: depth * (height * row_bytes), row_bytes = ceil(w/16)*2
"""
import struct
import sys
from pathlib import Path

WB_PALETTE = [
    (170, 170, 170),   # 0 background gray
    (0,   0,   0),     # 1 black text
    (255, 255, 255),   # 2 white highlight
    (102, 136, 187),   # 3 workbench blue
]


def parse_image(data, pos):
    le, te, w, h, depth = struct.unpack('>HHHHH', data[pos:pos + 10])
    # data[pos+10:pos+14] = ImageData pointer (ignored on disk)
    plane_pick = data[pos + 14]
    plane_off  = data[pos + 15]
    # data[pos+16:pos+20] = NextImage pointer (ignored on disk)
    row_bytes = ((w + 15) // 16) * 2
    plane_size = row_bytes * h
    base = pos + 20
    # Decode planar to indexed pixels
    pixels = [[0] * w for _ in range(h)]
    for plane_idx in range(depth):
        plane_off_bytes = plane_idx * plane_size
        for y in range(h):
            row_start = base + plane_off_bytes + y * row_bytes
            for x in range(w):
                bit = (data[row_start + (x >> 3)] >> (7 - (x & 7))) & 1
                if bit:
                    pixels[y][x] |= (1 << plane_idx)
    return {'w': w, 'h': h, 'depth': depth, 'pixels': pixels,
            'end': base + depth * plane_size}


def parse_info(path):
    data = Path(path).read_bytes()
    if struct.unpack('>H', data[:2])[0] != 0xE310:
        raise ValueError('not an Amiga .info file')
    gadget_render = struct.unpack('>I', data[0x16:0x1A])[0]
    select_render = struct.unpack('>I', data[0x1A:0x1E])[0]
    drawer_ptr    = struct.unpack('>I', data[0x42:0x46])[0]
    pos = 78
    if drawer_ptr:
        pos += 56
    images = []
    if gadget_render:
        img = parse_image(data, pos)
        images.append(img)
        pos = img['end']
    if select_render:
        img = parse_image(data, pos)
        images.append(img)
    return images


def to_rgba(img, palette=WB_PALETTE, transparent_index=0):
    """Convert indexed pixels to a flat RGBA byte buffer.
    Index 0 (background) becomes transparent."""
    w, h = img['w'], img['h']
    out = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            idx = img['pixels'][y][x]
            r, g, b = palette[idx % len(palette)]
            o = (y * w + x) * 4
            out[o] = r
            out[o + 1] = g
            out[o + 2] = b
            out[o + 3] = 0 if idx == transparent_index else 255
    return out


def save_png_pillow(img, path):
    from PIL import Image
    rgba = to_rgba(img)
    pil = Image.frombytes('RGBA', (img['w'], img['h']), bytes(rgba))
    pil.save(path)


def save_ico_pillow(img, path):
    from PIL import Image
    rgba = to_rgba(img)
    pil = Image.frombytes('RGBA', (img['w'], img['h']), bytes(rgba))
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    # Use nearest-neighbor scaling to preserve pixel-art look
    versions = []
    for size in sizes:
        v = pil.resize(size, Image.NEAREST)
        # ICO requires square images; pad if source isn't square
        versions.append(v)
    versions[0].save(path, format='ICO', sizes=sizes,
                     append_images=versions[1:])


def main():
    if len(sys.argv) < 2:
        print('usage: extract_icon.py <ASokoban.info>')
        sys.exit(1)
    info = sys.argv[1]
    images = parse_info(info)
    print(f'Found {len(images)} image(s)')
    for i, img in enumerate(images):
        print(f'  image {i}: {img["w"]}x{img["h"]} depth={img["depth"]}')

    # Use the first (normal) icon
    out_dir = Path(__file__).parent
    save_png_pillow(images[0], out_dir / 'icon.png')
    save_ico_pillow(images[0], out_dir / 'icon.ico')
    if len(images) > 1:
        save_png_pillow(images[1], out_dir / 'icon_select.png')
    print(f'Saved icon.png and icon.ico to {out_dir}')


if __name__ == '__main__':
    main()
