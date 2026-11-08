import sys
from pathlib import Path

# Ensure Task 3 root is first on sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
