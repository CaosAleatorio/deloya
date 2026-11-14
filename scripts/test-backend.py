"""Run tests against a dedicated PostgreSQL database without exposing credentials."""
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


workspace = Path(__file__).resolve().parents[1]
load_dotenv(workspace / ".env")
configured = os.environ.get("TEST_DATABASE_URL")
if not configured:
    development_url = os.environ.get("DATABASE_URL")
    if not development_url:
        raise SystemExit("Configure .env com DATABASE_URL e crie primeiro a base PostgreSQL deloya_test.")
    parsed = make_url(development_url)
    configured = parsed.set(database=f"{parsed.database}_test").render_as_string(hide_password=False)
target = make_url(configured)
if not target.drivername.startswith("postgresql") or not target.database or not target.database.endswith("_test"):
    raise SystemExit("Os testes exigem uma base PostgreSQL dedicada cujo nome termina em _test.")
os.environ["TEST_DATABASE_URL"] = configured
os.environ["ENVIRONMENT"] = "test"
os.environ["PAYMENT_MODE"] = "demo"
print(f"Testes na base dedicada {target.database}; as tabelas desta base serão limpas.", flush=True)
raise SystemExit(subprocess.run([sys.executable, "-m", "pytest", *(sys.argv[1:] or ["-q"])],
                               cwd=workspace / "backend", env=os.environ).returncode)
