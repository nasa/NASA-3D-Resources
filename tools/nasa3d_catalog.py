#!/usr/bin/env python3
"""Standalone catalogue and integrity tool for nasa/NASA-3D-Resources (no dependencies beyond the
Python standard library). Candidate upstream contribution: see docs/UPSTREAM.md.

    scripts/nasa3d_catalog.py catalog  [--ref master] [--out CATALOG.json]
    scripts/nasa3d_catalog.py summary  [--catalog CATALOG.json]
    scripts/nasa3d_catalog.py verify   "3D Models/International Space Station (ISS) (A)/International Space Station (ISS) (A).png"

`catalog` lists every file with its size, git blob id, kind and subject from the GitHub tree API
without cloning the 5 GB repository. `verify` downloads one file and checks it against its blob
id (sha1 of "blob <size>\\0" + bytes), which is what git itself would compute.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO = "nasa/NASA-3D-Resources"
MODEL = {"glb", "gltf", "stl", "obj", "fbx", "blend", "3ds", "lwo", "lws", "dae", "usdz", "ma", "mb", "max"}
IMAGE = {"png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp", "exr", "hdr", "gif"}
ARCHIVE = {"7z", "zip", "rar", "gz", "tgz", "tar"}
DOC = {"pdf", "txt", "md", "json", "csv"}


def kind_of(path: str) -> str:
    ext = path.rsplit("/", 1)[-1].lower().rsplit(".", 1)[-1]
    if re.fullmatch(r"\d{3}", ext) or ext in ARCHIVE:
        return "archive"
    return "model" if ext in MODEL else "image" if ext in IMAGE else "doc" if ext in DOC else "other"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "nasa3d-catalog/1.0", "Accept": "application/vnd.github+json"})
    tok = os.getenv("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def catalog(ref: str) -> dict:
    tree = json.loads(_get(f"https://api.github.com/repos/{REPO}/git/trees/{ref}?recursive=1"))
    if tree.get("truncated"):
        raise SystemExit("GitHub truncated the tree; catalogue would be incomplete")
    assets = []
    for e in tree["tree"]:
        if e["type"] != "blob" or "/" not in e["path"]:
            continue
        parts = e["path"].split("/")
        assets.append({"path": e["path"], "size": e.get("size", 0), "sha": e["sha"], "kind": kind_of(e["path"]), "category": parts[0],
                       "subject": parts[1] if len(parts) > 2 else parts[-1].rsplit(".", 1)[0]})
    by_kind: dict[str, int] = {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    return {"repo": REPO, "ref": ref, "assets": len(assets), "bytes": sum(a["size"] for a in assets), "by_kind": by_kind,
            "subjects": len({a["subject"] for a in assets}), "files": assets}


def verify(path: str, ref: str, sha: str | None) -> int:
    if sha is None:
        cat = catalog(ref)
        sha = next((f["sha"] for f in cat["files"] if f["path"] == path), None)
        if sha is None:
            print("not in the repository tree:", path)
            return 2
    data = _get(f"https://raw.githubusercontent.com/{REPO}/{ref}/{urllib.parse.quote(path)}")
    h = hashlib.sha1(usedforsecurity=False)
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    ok = h.hexdigest() == sha
    print(f"{'OK' if ok else 'MISMATCH'} {path} ({len(data)} bytes) blob {h.hexdigest()[:12]} expected {sha[:12]}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("catalog")
    c.add_argument("--ref", default="master")
    c.add_argument("--out", default="CATALOG.json")
    s = sub.add_parser("summary")
    s.add_argument("--catalog", default="CATALOG.json")
    v = sub.add_parser("verify")
    v.add_argument("path")
    v.add_argument("--ref", default="master")
    v.add_argument("--sha", default=None)
    args = ap.parse_args()
    if args.cmd == "catalog":
        cat = catalog(args.ref)
        with open(args.out, "w") as fh:
            json.dump(cat, fh, indent=1)
        print(f"{cat['assets']} files, {cat['bytes'] / 1e9:.2f} GB, {cat['subjects']} subjects, by kind {cat['by_kind']} -> {args.out}")
        return 0
    if args.cmd == "summary":
        with open(args.catalog) as fh:
            cat = json.load(fh)
        subjects: dict[str, dict[str, int]] = {}
        for f in cat["files"]:
            subjects.setdefault(f["subject"], {}).setdefault(f["kind"], 0)
            subjects[f["subject"]][f["kind"]] += 1
        missing_preview = [sname for sname, kinds in subjects.items() if kinds.get("model") and not kinds.get("image")]
        print(f"{len(subjects)} subjects; {len(missing_preview)} model subjects without a preview image:")
        for sname in missing_preview[:50]:
            print("  -", sname)
        return 0
    return verify(args.path, args.ref, args.sha)


if __name__ == "__main__":
    sys.exit(main())
