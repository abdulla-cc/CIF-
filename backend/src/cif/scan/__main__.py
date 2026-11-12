"""Usage: python -m cif.scan URL  (prints the scan result as JSON)."""

import json
import sys

from cif.scan.axe import scan_url

if len(sys.argv) != 2:
    sys.exit(__doc__)
print(json.dumps(scan_url(sys.argv[1]), indent=2))
