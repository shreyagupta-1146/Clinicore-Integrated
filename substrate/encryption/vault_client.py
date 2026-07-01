"""
platform/encryption/vault_client.py

HashiCorp Vault client wrapper for the platform.

Responsibilities:
- KV secrets (API keys, audit chain signing key, etc.)
- Transit encryption (Vault-managed AES-256-GCM for application-layer encryption)
- Dynamic secrets (Vault generates short-lived DB credentials on demand)

Why Vault instead of local key management:
- Key is never in app memory longer than needed
- Automatic key rotation without redeployment
- Full secret access audit log inside Vault
- HSM backend available for production (PKCS#11)
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Optional

import hvac  # HashiCorp Vault Python client

logger = logging.getLogger(__name__)


class VaultClient:
    """
    Async-compatible wrapper around the synchronous hvac client.
    All blocking calls are run in an executor.
    """

    def __init__(self, url: str, token: str, mount_path: str = "clinicore"):
        self._url = url
        self._token = token
        self._mount = mount_path
        self._client: Optional[hvac.Client] = None

    def _connect(self) -> hvac.Client:
        if self._client is None or not self._client.is_authenticated():
            self._client = hvac.Client(url=self._url, token=self._token)
            if not self._client.is_authenticated():
                raise VaultAuthError(f"Vault at {self._url!r} rejected token.")
        return self._client

    # ── KV secrets ───────────────────────────────────────────────────────────

    async def get_secret(self, path: str) -> Optional[str]:
        """Read a KV v2 secret value at the given path. Returns None if absent."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_secret_sync, path)

    def _get_secret_sync(self, path: str) -> Optional[str]:
        client = self._connect()
        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self._mount
            )
            return response["data"]["data"].get("value")
        except hvac.exceptions.InvalidPath:
            return None
        except Exception as exc:
            logger.error("vault_get_secret failed path=%s error=%s", path, exc)
            raise

    async def set_secret(self, path: str, value: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._set_secret_sync, path, value)

    def _set_secret_sync(self, path: str, value: str) -> None:
        client = self._connect()
        client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret={"value": value},
            mount_point=self._mount,
        )

    # ── Transit (Vault-managed encryption) ───────────────────────────────────

    async def encrypt(self, plaintext: bytes, key_name: str = "phi-aes") -> str:
        """
        Encrypt bytes using Vault Transit (AES-256-GCM).
        Returns a Vault ciphertext blob (vault:v1:...).
        The encryption key never leaves Vault.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encrypt_sync, plaintext, key_name)

    def _encrypt_sync(self, plaintext: bytes, key_name: str) -> str:
        client = self._connect()
        b64 = base64.b64encode(plaintext).decode("utf-8")
        result = client.secrets.transit.encrypt_data(name=key_name, plaintext=b64)
        return result["data"]["ciphertext"]

    async def decrypt(self, ciphertext: str, key_name: str = "phi-aes") -> bytes:
        """Decrypt a Vault Transit ciphertext blob. Returns the original bytes."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._decrypt_sync, ciphertext, key_name)

    def _decrypt_sync(self, ciphertext: str, key_name: str) -> bytes:
        client = self._connect()
        result = client.secrets.transit.decrypt_data(name=key_name, ciphertext=ciphertext)
        return base64.b64decode(result["data"]["plaintext"])

    # ── Hybrid PQC wrapper for long-lived data at rest ────────────────────────
    # NIST FIPS 203 (ML-KEM-768 / Kyber768) via liboqs.
    #
    # Threat model: "harvest now, decrypt later" — an adversary captures
    # today's ciphertext and stores it, hoping to decrypt with a future
    # quantum computer. Classical AES-256-GCM is safe against classical
    # computers but would be broken by Grover's algorithm on a CRQC.
    # Wrapping the AES key with ML-KEM-768 adds a quantum-resistant layer.
    #
    # Construction (hybrid — classical + PQC):
    #   1. ML-KEM-768 KEM encap → (kem_ciphertext, kem_shared_secret)
    #   2. HKDF-SHA256(kem_shared_secret) → wrapping_key (256-bit)
    #   3. AES-256-GCM(wrapping_key, aes_key) → encrypted_aes_key
    #   4. Output: kem_ciphertext | iv | encrypted_aes_key | tag
    #
    # Key storage: the ML-KEM keypair is stored in Vault KV at:
    #   clinicore/pqc/kyber768-pubkey  (hex-encoded)
    #   clinicore/pqc/kyber768-seckey  (hex-encoded, access restricted)
    # Run infrastructure/vault/pqc_setup.sh to provision these on first deploy.

    _PQC_PUBKEY_PATH = "pqc/kyber768-pubkey"
    _PQC_SECKEY_PATH = "pqc/kyber768-seckey"

    async def pqc_wrap_key(self, aes_key: bytes) -> bytes:
        """
        Wrap a 256-bit AES key using ML-KEM-768.
        Returns opaque bytes: kem_ciphertext | iv | encrypted_aes_key | gcm_tag
        Install: pip install liboqs-python
        """
        loop = asyncio.get_event_loop()
        pubkey_hex = await self.get_secret(self._PQC_PUBKEY_PATH)
        if not pubkey_hex:
            raise RuntimeError(
                "ML-KEM-768 public key not found in Vault. "
                "Run infrastructure/vault/pqc_setup.sh first."
            )
        return await loop.run_in_executor(
            None, self._pqc_wrap_sync, aes_key, bytes.fromhex(pubkey_hex)
        )

    def _pqc_wrap_sync(self, aes_key: bytes, pubkey_bytes: bytes) -> bytes:
        try:
            import oqs
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives import hashes
            import os

            # ML-KEM encapsulate: generates a shared secret using the recipient's pubkey
            with oqs.KeyEncapsulation("Kyber768") as kem:
                kem_ciphertext, kem_shared_secret = kem.encap_secret(pubkey_bytes)

            # HKDF to derive a 256-bit wrapping key from the KEM shared secret
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"clinicore-pqc-wrap-v1",
            )
            wrapping_key = hkdf.derive(kem_shared_secret)

            # AES-256-GCM encrypt the AES key with the wrapping key
            iv = os.urandom(12)
            aesgcm = AESGCM(wrapping_key)
            encrypted_aes_key = aesgcm.encrypt(iv, aes_key, associated_data=b"clinicore-pqc-wrap-v1")

            # Pack: len(kem_ciphertext) as 2 bytes | kem_ciphertext | iv | encrypted_aes_key
            kem_ct_len = len(kem_ciphertext).to_bytes(2, "big")
            return kem_ct_len + kem_ciphertext + iv + encrypted_aes_key

        except ImportError as exc:
            raise RuntimeError(
                f"PQC dependency missing: {exc}. "
                "Install with: pip install liboqs-python cryptography"
            ) from exc

    async def pqc_unwrap_key(self, wrapped: bytes) -> bytes:
        """
        Unwrap an AES key produced by pqc_wrap_key.
        Retrieves the secret key from Vault and decapsulates.
        """
        loop = asyncio.get_event_loop()
        seckey_hex = await self.get_secret(self._PQC_SECKEY_PATH)
        if not seckey_hex:
            raise RuntimeError("ML-KEM-768 secret key not found in Vault.")
        return await loop.run_in_executor(
            None, self._pqc_unwrap_sync, wrapped, bytes.fromhex(seckey_hex)
        )

    def _pqc_unwrap_sync(self, wrapped: bytes, seckey_bytes: bytes) -> bytes:
        try:
            import oqs
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives import hashes

            # Unpack
            kem_ct_len = int.from_bytes(wrapped[:2], "big")
            kem_ciphertext = wrapped[2: 2 + kem_ct_len]
            iv = wrapped[2 + kem_ct_len: 2 + kem_ct_len + 12]
            encrypted_aes_key = wrapped[2 + kem_ct_len + 12:]

            # ML-KEM decapsulate: recover the shared secret
            with oqs.KeyEncapsulation("Kyber768", secret_key=seckey_bytes) as kem:
                kem_shared_secret = kem.decap_secret(kem_ciphertext)

            # HKDF to recover wrapping key
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"clinicore-pqc-wrap-v1",
            )
            wrapping_key = hkdf.derive(kem_shared_secret)

            # AES-256-GCM decrypt
            aesgcm = AESGCM(wrapping_key)
            return aesgcm.decrypt(iv, encrypted_aes_key, associated_data=b"clinicore-pqc-wrap-v1")

        except ImportError as exc:
            raise RuntimeError(f"PQC dependency missing: {exc}") from exc

    async def pqc_provision_keypair(self) -> None:
        """
        Generate and store a new ML-KEM-768 keypair in Vault.
        Run ONCE at initial deployment (or key rotation).
        Requires the calling token to have write access to the seckey path.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._pqc_provision_sync)

    def _pqc_provision_sync(self) -> None:
        try:
            import oqs
        except ImportError as exc:
            raise RuntimeError("liboqs-python not installed") from exc

        with oqs.KeyEncapsulation("Kyber768") as kem:
            pubkey = kem.generate_keypair()
            seckey = kem.export_secret_key()

        self._set_secret_sync(self._PQC_PUBKEY_PATH, pubkey.hex())
        self._set_secret_sync(self._PQC_SECKEY_PATH, seckey.hex())
        logger.warning(
            "ML-KEM-768 keypair provisioned in Vault. "
            "Restrict access to %s in production.", self._PQC_SECKEY_PATH
        )


class VaultAuthError(Exception):
    pass
