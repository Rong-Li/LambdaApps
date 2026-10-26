"""Ad-hoc runner for the monthly re-aggregation batch job.

Usage (from the project root):
    python scripts/run_monthly_reaggregation.py

The script loads environment variables from the project-root .env file
before invoking the batch function, so no manual export is needed.
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that 'service.*' imports resolve
# whether the package is installed in editable mode or not.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Load .env from the project root (mirrors Lambda environment variables).
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]

    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f'[runner] Loaded environment from {env_file}')
    else:
        print(f'[runner] WARNING: .env not found at {env_file}')
except ModuleNotFoundError:
    # python-dotenv is not installed – fall back to manual parsing so the
    # script still works without it.
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        import os

        with open(env_file) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip())
        print(f'[runner] Loaded environment from {env_file} (manual fallback)')

# ---------------------------------------------------------------------------
# Run the batch function.
# ---------------------------------------------------------------------------
from service.batch.monthly_reaggregation import run_monthly_reaggregation  # noqa: E402

if __name__ == '__main__':
    print('[runner] Starting monthly re-aggregation ...\n')
    try:
        result = run_monthly_reaggregation()
    except Exception as exc:
        print(f'[runner] ERROR: {exc}')
        raise SystemExit(1) from exc

    print('\n[runner] Completed successfully.')
    print('[runner] Result:')
    print(json.dumps(result, indent=2, default=str))
