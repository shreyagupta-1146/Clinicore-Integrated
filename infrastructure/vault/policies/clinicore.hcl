# infrastructure/vault/policies/clinicore.hcl
#
# HashiCorp Vault policy for the Clinicore/RelayMed backend services.
# Applied with: vault policy write clinicore infrastructure/vault/policies/clinicore.hcl
#
# Principle of least privilege:
#   - Backends can read/write secrets under clinicore/data/
#   - Backends can use the Transit engine for encrypt/decrypt only — they cannot
#     export or delete keys (keys never leave Vault)
#   - Only Vault admins can create/delete keys or policies

# KV v2 secrets (connection strings, API keys, etc.)
path "clinicore/data/*" {
  capabilities = ["create", "read", "update"]
}

path "clinicore/metadata/*" {
  capabilities = ["read", "list"]
}

# Transit engine — encrypt/decrypt (AES-256-GCM)
# Key name: phi-aes (for PHI field-level encryption)
path "transit/encrypt/phi-aes" {
  capabilities = ["update"]
}

path "transit/decrypt/phi-aes" {
  capabilities = ["update"]
}

# Transit engine — HMAC for audit chain signing key integrity check
path "transit/hmac/audit-chain-hmac" {
  capabilities = ["update"]
}

# Audit chain signing key — read-only (backend reads but cannot rotate)
path "clinicore/data/audit/chain-signing-key" {
  capabilities = ["read", "create", "update"]
}

# Deny all other paths
path "*" {
  capabilities = ["deny"]
}
