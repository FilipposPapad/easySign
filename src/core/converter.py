import os
import subprocess
import time
import shutil
import platform
import zipfile
import tempfile

from pathlib import Path

from utils.helpers import get_documents_from_folder


def convert_doc_to_pdf(
    src: str, dest: str = None, timeout: int = 10, profile_dir: str = None
) -> str:
    src_path = Path(src).resolve()

    if not src_path.exists():
        raise FileNotFoundError(f"Source file not found: {src_path}")

    dest_path = Path(dest or src_path.with_suffix(".pdf")).resolve()

    if dest_path.exists():
        raise FileExistsError(f"File already exists: {dest_path}")

    soffice_path = _find_soffice()

    if profile_dir is None:
        profile = (
            Path(tempfile.gettempdir()) / f"lo_profile_{os.getpid()}_{int(time.time())}"
        )
        profile.mkdir(parents=True, exist_ok=True)
    else:
        profile = Path(profile_dir).resolve()

    profile_url = profile.as_uri()

    cmd = [
        soffice_path,
        "--headless",
        f"-env:UserInstallation={profile_url}",
        "--convert-to",
        "pdf",
        str(src_path),
        "--outdir",
        str(dest_path.parent),
        "--nodefault",
        "--nologo",
        "--nolockcheck",
        "--invisible",
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        start_time = time.time()

        while time.time() - start_time <= timeout:
            if dest_path.exists() and dest_path.stat().st_size > 0:
                return str(dest_path)
            time.sleep(0.2)

        raise TimeoutError(f"PDF conversion timed out for: {src_path}")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"LibreOffice failed:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        )

    finally:
        # Cleanup
        if profile_dir is None:
            try:
                shutil.rmtree(profile, ignore_errors=True)
            except Exception:
                pass


def convert_folder_docs_to_pdfs(folder_path):
    extensions = {".doc", ".docx", ".odt", ".rtf"}
    documents = get_documents_from_folder(folder_path, extensions)

    success = []
    fail = []
    ignore = []

    tmp_profile = (
        Path(tempfile.gettempdir()) / f"lo_profile_{os.getpid()}_{int(time.time())}"
    )
    tmp_profile.mkdir(parents=True, exist_ok=True)

    for document in documents:
        if is_doc_file(document):
            try:
                convert_doc_to_pdf(src=document, profile_dir=tmp_profile)
                success.append(document)
            except FileExistsError as er:
                ignore.append(document)
            except:
                fail.append(document)
            # time.sleep(0.1)
        else:
            ignore.append(document)

    result = {"success": success, "fail": fail, "ignore": ignore}

    return result

    # ---------------- Helpers ----------------


def is_doc_file(filepath):
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)

        # 1. Έλεγχος για RTF αρχεία
        if header.startswith(b"{\\rtf1"):
            return True

        # Έλεγχος για παλιά .doc αρχεία
        if header == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return True

        # 2. Έλεγχος αν είναι ZIP (για .docx ή .odt)
        if header.startswith(b"PK\x03\x04"):
            with zipfile.ZipFile(filepath, "r") as z:
                files = set(z.namelist())

                # Έλεγχος για MS Word (.docx)
                if "word/document.xml" in files:
                    return True

                # Έλεγχος για OpenDocument (.odt)
                if "mimetype" in files:
                    with z.open("mimetype") as m:
                        if m.read(100).startswith(
                            b"application/vnd.oasis.opendocument.text"
                        ):
                            return True

    except (OSError, zipfile.BadZipFile):
        return False

    return False


def _find_soffice() -> str:
    system = platform.system()

    if system == "Windows":
        paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        raise FileNotFoundError("LibreOffice not found on Windows")

    else:
        soffice = shutil.which("soffice")
        if soffice:
            return soffice

        # fallback paths (Linux/macOS)
        common_paths = [
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/snap/bin/libreoffice",
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p

        raise FileNotFoundError("LibreOffice (soffice) not found in PATH")
