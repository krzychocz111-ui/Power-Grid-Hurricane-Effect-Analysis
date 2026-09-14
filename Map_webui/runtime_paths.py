"""Find the bundled LibreOffice runtime without machine-specific paths."""
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

def libreoffice_program():
    bundled = PROJECT_DIR / 'runtime' / 'LibreOffice' / 'program'
    candidates = [bundled]
    if os.environ.get('LIBREOFFICE_PROGRAM'):
        candidates.append(Path(os.environ['LIBREOFFICE_PROGRAM']))
    candidates.append(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'LibreOffice' / 'program')
    for program in candidates:
        if (program / 'python.exe').is_file() and (program / 'soffice.exe').is_file():
            return program
    raise RuntimeError('LibreOffice runtime not found. Start the project with Start Dashboard.cmd to unpack the bundled runtime.')
