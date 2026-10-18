import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

try:
    from backend.app.main import app
    print(f"SUCCESS: FastAPI app '{app.title}' (v{app.version}) imported and initialized cleanly!")
    print(f"Registered routes: {len(app.routes)}")
except Exception as e:
    print(f"ERROR initializing app: {e}")
    sys.exit(1)
