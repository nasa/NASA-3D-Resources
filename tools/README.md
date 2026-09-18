# tools

`nasa3d_catalog.py` (Python 3.9+, standard library only) keeps `CATALOG.json` current and lets a user verify a download:

    python3 tools/nasa3d_catalog.py catalog --out tools/CATALOG.json   # regenerate from the GitHub tree API (seconds, no clone)
    python3 tools/nasa3d_catalog.py summary --catalog tools/CATALOG.json
    python3 tools/nasa3d_catalog.py verify "3D Models/TOPEX-Poseidon/TOPEX-Poseidon.lwo"   # git blob id of the fetched bytes vs the tree

`CATALOG.json` lists every file with its path, size, git blob id, kind (model, image, archive, doc, other) and subject
folder, so someone who needs one model does not have to clone the whole repository.
