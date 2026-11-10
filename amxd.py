#!/usr/bin/env python3
"""amxd - write and read Max for Live device files (.amxd) without opening Max.

Two layouts exist. Both start with a 32-byte header:

  'ampf' LE32(4) <type 4cc: aaaa audio effect | iiii instrument | mmmm MIDI effect>
  'meta' LE32(4) LE32(meta)
  'ptch' LE32(len(rest))               rest = everything after the header, to the end of the file

PLAIN (editable; what Live's own templates `Misc/Max Devices/Max Audio Effect.amxd` etc. use; meta 0):
  <patcher JSON, UTF-8> 0x00

FROZEN (Max's "Freeze Device"; Live greys out the Max edit button; meta 4 with no embedded files, 7 with):
  'mx@c' BE32(16) BE32(0) BE32(len(json) + 16)
  <patcher JSON, UTF-8> 0x0A 0x00
  'dlst' BE32 { 'dire' BE32 { 'type' 'JSON' | 'fnam' <name> | 'sz32' len(json) | 'of32' 16 | 'vers' 0 | 'flag' 0x11 | 'mdat' <time> } }
  Every chunk after 'mx@c' is TAG + BE32(8 + len(data)) + data. 'fnam' data is the file name plus a NUL, padded to a
  multiple of 4. 'mdat' is seconds since 1904-01-01. Frozen devices with embedded files carry one more 'dire' per
  file and their bytes after the JSON: not written here (a generated frozen device must have no dependencies).

Verified byte-for-byte: SDK `OSC Monitor.amxd` (frozen) and Live's `Max Audio Effect.amxd` (plain) rebuild identically.
The patcher's own `project.amxdtype` is the type tag as a big-endian integer (audio 1633771873).

  amxd.py build <patcher.json> --name "My Device" [--type audio|instrument|midi] [--frozen] --out My.amxd
  amxd.py info <file.amxd>
  amxd.py selftest <file.amxd>      rebuild it from its own parts and compare bytes (no embedded files)
"""
import argparse
import json
import struct
import sys
import time

TYPES = {"audio": b"aaaa", "instrument": b"iiii", "midi": b"mmmm"}
MAC_EPOCH_OFFSET = 2082844800  # seconds from 1904-01-01 to 1970-01-01


def be32(n):
    return struct.pack(">I", n)


def le32(n):
    return struct.pack("<I", n)


def chunk(tag, data):
    assert len(tag) == 4
    return tag + be32(8 + len(data)) + data


def fnam_data(name):
    raw = name.encode("utf-8") + b"\0"
    return raw + b"\0" * (-len(raw) % 4)


def header(kind, meta, payload_len):
    return b"ampf" + le32(4) + kind + b"meta" + le32(4) + le32(meta) + b"ptch" + le32(payload_len)


def pack_plain(json_bytes, kind=b"aaaa", meta=0):
    """Editable layout. `json_bytes` is the patcher text exactly as it goes in the file (incl. the final NUL)."""
    assert json_bytes.endswith(b"\0")
    return header(kind, meta, len(json_bytes)) + json_bytes


def pack_frozen(json_bytes, name, kind=b"aaaa", meta=4, mdat=None, flag=0x11):
    """Frozen layout with the device itself as the only file entry."""
    assert json_bytes.endswith(b"\0")
    if mdat is None:
        mdat = int(time.time()) + MAC_EPOCH_OFFSET
    dire = chunk(b"dire", b"".join([
        chunk(b"type", b"JSON"),
        chunk(b"fnam", fnam_data(name)),
        chunk(b"sz32", be32(len(json_bytes))),
        chunk(b"of32", be32(16)),
        chunk(b"vers", be32(0)),
        chunk(b"flag", be32(flag)),
        chunk(b"mdat", be32(mdat)),
    ]))
    mx = b"mx@c" + be32(16) + be32(0) + be32(len(json_bytes) + 16) + json_bytes + chunk(b"dlst", dire)
    return header(kind, meta, len(mx)) + mx


def build(patcher, name="", kind="audio", frozen=False, **kw):
    """High level: `patcher` is the Max patcher dict ({"patcher": {...}}); returns the .amxd bytes.
    Sets project.amxdtype to match the device type. `name` is only used by the frozen layout (file name)."""
    tag = TYPES.get(kind) if isinstance(kind, str) else kind
    if tag is None:
        raise ValueError("unknown device type %r" % (kind,))
    proj = patcher.get("patcher", {}).get("project")
    if isinstance(proj, dict):
        proj["amxdtype"] = int.from_bytes(tag, "big")
    if frozen:
        text = json.dumps(patcher, indent="\t", ensure_ascii=False) + "\n"
        if not name.endswith(".amxd"):
            name += ".amxd"
        return pack_frozen(text.encode("utf-8") + b"\0", name, tag, **kw)
    text = json.dumps(patcher, indent="\t", ensure_ascii=False) + "\n"
    return pack_plain(text.encode("utf-8") + b"\0", tag, **kw)


def parse(data):
    """Return dict(layout 'plain'|'frozen', kind, meta, json (bytes, with NUL), ...); raise ValueError if malformed.
    Frozen devices also give name, mdat, flag, sz32 and `embedded` (True if they carry extra files)."""
    if data[:4] != b"ampf" or data[24:28] != b"ptch":
        raise ValueError("not an amxd (no ampf/ptch header)")
    if struct.unpack("<I", data[28:32])[0] != len(data) - 32:
        raise ValueError("ptch length does not match the file size")
    out = {"kind": data[8:12], "meta": struct.unpack("<I", data[20:24])[0]}
    if data[32:33] == b"{":
        if not data.endswith(b"\0"):
            raise ValueError("plain patcher text does not end with a NUL")
        out.update(layout="plain", json=data[32:], embedded=False)
        return out
    if data[32:36] != b"mx@c":
        raise ValueError("unknown layout after the header: %r" % data[32:40])
    hdr, _, clen = struct.unpack(">III", data[36:48])
    if hdr != 16:
        raise ValueError("unexpected mx@c header size %d" % hdr)
    jend = 48 + clen - 16
    if data[jend:jend + 4] != b"dlst":
        raise ValueError("no dlst after the JSON")
    dlst_len = struct.unpack(">I", data[jend + 4:jend + 8])[0]
    if jend + dlst_len != len(data):
        raise ValueError("dlst does not end at end of file")
    dire_len = struct.unpack(">I", data[jend + 12:jend + 16])[0]
    fields, j = {}, jend + 16
    while j < jend + 8 + dire_len:
        tag, n = data[j:j + 4], struct.unpack(">I", data[j + 4:j + 8])[0]
        fields[tag] = data[j + 8:j + n]
        j += n
    out.update(
        layout="frozen", json=data[48:jend], embedded=(jend + 8 + dire_len) != len(data),
        name=fields[b"fnam"].rstrip(b"\0").decode("utf-8"), mdat=struct.unpack(">I", fields[b"mdat"])[0],
        flag=struct.unpack(">I", fields[b"flag"])[0], sz32=struct.unpack(">I", fields[b"sz32"])[0])
    return out


def rebuild(d):
    if d["layout"] == "plain":
        return pack_plain(d["json"], d["kind"], d["meta"])
    return pack_frozen(d["json"], d["name"], d["kind"], d["meta"], d["mdat"], d["flag"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("patcher")
    b.add_argument("--name", default="")
    b.add_argument("--type", default="audio", choices=sorted(TYPES))
    b.add_argument("--frozen", action="store_true", help="write the frozen layout (name required)")
    b.add_argument("--out", required=True)
    i = sub.add_parser("info")
    i.add_argument("file")
    s = sub.add_parser("selftest")
    s.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        if a.frozen and not a.name:
            sys.exit("--frozen needs --name")
        with open(a.patcher, encoding="utf-8") as f:
            patcher = json.load(f)
        out = build(patcher, a.name, a.type, frozen=a.frozen)
        with open(a.out, "wb") as f:
            f.write(out)
        print("wrote %s (%d bytes, %s)" % (a.out, len(out), "frozen" if a.frozen else "plain"))
    else:
        with open(a.file, "rb") as f:
            raw = f.read()
        d = parse(raw)
        if a.cmd == "info":
            p = json.loads(d["json"].rstrip(b"\0"))["patcher"]
            print("%s type %s meta %d json %d bytes, %d boxes, %d lines, amxdtype %s%s" % (
                d["layout"], d["kind"].decode(), d["meta"], len(d["json"]), len(p.get("boxes", [])),
                len(p.get("lines", [])), p.get("project", {}).get("amxdtype"),
                (", name %r, flag 0x%x, embedded %s" % (d["name"], d["flag"], d["embedded"])) if d["layout"] == "frozen" else ""))
        else:
            if d["embedded"]:
                sys.exit("selftest needs a device without embedded files")
            if rebuild(d) != raw:
                sys.exit("MISMATCH: rebuilt %d bytes vs original %d" % (len(rebuild(d)), len(raw)))
            print("selftest OK: %s (%s) rebuilt byte-identical (%d bytes)" % (a.file, d["layout"], len(raw)))


if __name__ == "__main__":
    main()
