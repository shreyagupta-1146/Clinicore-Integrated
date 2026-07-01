#!/usr/bin/env bash
# infrastructure/vault/pqc_setup.sh
#
# One-time provisioning of ML-KEM-768 keypair in Vault.
# Run ONCE before the first deployment (or on key rotation).
# Requires: vault CLI authenticated, liboqs-python installed.
#
# Usage:
#   export VAULT_ADDR=http://localhost:8200
#   export VAULT_TOKEN=<your-token>
#   bash infrastructure/vault/pqc_setup.sh

set -euo pipefail

echo "[pqc_setup] Provisioning ML-KEM-768 keypair via Python + liboqs..."

python3 - <<'PYEOF'
import sys
import os

# Verify liboqs is available before touching Vault
try:
    import oqs
except ImportError:
    print("ERROR: liboqs-python not installed. Run: pip install liboqs-python", file=sys.stderr)
    sys.exit(1)

# Verify Vault connectivity
try:
    import hvac
    vault = hvac.Client(
        url=os.environ.get("VAULT_ADDR", "http://localhost:8200"),
        token=os.environ.get("VAULT_TOKEN", ""),
    )
    if not vault.is_authenticated():
        print("ERROR: Vault authentication failed. Check VAULT_ADDR and VAULT_TOKEN.", file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Cannot connect to Vault: {e}", file=sys.stderr)
    sys.exit(1)

# Generate ML-KEM-768 keypair
with oqs.KeyEncapsulation("Kyber768") as kem:
    pubkey_bytes = kem.generate_keypair()
    seckey_bytes = kem.export_secret_key()

mount = os.environ.get("VAULT_MOUNT", "clinicore")

# Store public key
vault.secrets.kv.v2.create_or_update_secret(
    path="pqc/kyber768-pubkey",
    secret={"value": pubkey_bytes.hex()},
    mount_point=mount,
)
print(f"[pqc_setup] Stored ML-KEM-768 public key at {mount}/pqc/kyber768-pubkey")

# Store secret key (restrict access to this path in production Vault policy)
vault.secrets.kv.v2.create_or_update_secret(
    path="pqc/kyber768-seckey",
    secret={"value": seckey_bytes.hex()},
    mount_point=mount,
)
print(f"[pqc_setup] Stored ML-KEM-768 secret key at {mount}/pqc/kyber768-seckey")
print("[pqc_setup] IMPORTANT: Restrict read access to the seckey path to decryption services only.")
print("[pqc_setup] ML-KEM-768 keypair provisioned successfully.")
PYEOF

echo "[pqc_setup] Done."
