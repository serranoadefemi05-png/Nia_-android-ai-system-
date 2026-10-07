"""
NIA — ArcService

Arc is Circle's blockchain where USDC is the native gas token.
This service is the ONLY place in the NIA backend that knows about Arc.

Architecture principle (from user specification):
  "Keep Arc behind an ArcService abstraction. Do NOT force blockchain
   into ordinary Android commands."

Current status: v0.1 — all methods are stubs that return sensible defaults.
The interfaces are defined so future Arc features can be added without
touching the orchestrator or the API layer.

Future Arc capabilities (interfaces defined, not implemented):
  - Agent identity    (ERC-8004 token → Nia gets a verifiable onchain identity)
  - Task attestations (tool execution results attested onchain)
  - USDC payments     (make_payment tool backed by Arc USDC transfer)
  - Agent economy     (Nia can receive and pay USDC for agent services)
  - Verifiable actions (actions signed and recorded onchain)
  - Agent-to-agent    (Nia can commission other Arc agents)

Configuration (all optional — Arc features degrade gracefully if unset):
  ARC_RPC_URL          Arc testnet RPC URL
  ARC_CHAIN_ID         Arc chain ID (int)
  ARC_WALLET_ADDRESS   Nia's Arc wallet address (set at deploy time)
  ARC_PRIVATE_KEY      Never in APK — backend only; stored in .env
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("nia.arc")


@dataclass
class ArcIdentity:
    """Nia's onchain agent identity on Arc."""
    agent_id: Optional[int]           # ERC-8004 token id
    wallet_address: Optional[str]     # Arc wallet address
    chain_id: Optional[int]


@dataclass
class ArcPaymentRequest:
    """A validated payment request before execution."""
    to_address: str
    amount_usdc: str                  # decimal string, e.g. "10.50"
    description: str
    estimated_gas_usdc: Optional[str] = None


@dataclass
class ArcPaymentResult:
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None


class ArcService:
    """
    Abstracts all Arc/blockchain functionality from the rest of the backend.

    The orchestrator calls this service by name only — it never imports
    Arc SDK or viem/ethers directly. This makes Arc optional and testable.
    """

    # ── Status ──────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """
        Return True only when Arc is fully configured and reachable.
        v0.1: always False — Arc is not yet active.
        """
        return False

    def status(self) -> Dict[str, Any]:
        """
        Return Arc configuration status for the health endpoint.
        Never expose private keys or wallet seeds.
        """
        from ..core.config import settings
        return {
            "available": self.is_available(),
            "rpc_configured": bool(getattr(settings, "ARC_RPC_URL", None)),
            "chain_id": getattr(settings, "ARC_CHAIN_ID", None),
            "features": {
                "payments": False,          # not yet
                "identity": False,          # not yet
                "attestations": False,      # not yet
                "agent_economy": False,     # not yet
            },
            "note": (
                "Arc integration is prepared but inactive in v0.1. "
                "Set ARC_RPC_URL and ARC_CHAIN_ID to enable future features."
            ),
        }

    # ── Identity (future) ────────────────────────────────────────────────────

    async def get_identity(self) -> Optional[ArcIdentity]:
        """
        Return Nia's onchain identity from the Arc ERC-8004 registry.
        Stub: returns None in v0.1.
        """
        logger.debug("ARC get_identity() called — stub returns None")
        return None

    async def register_identity(
        self,
        name: str,
        description: str,
        wallet_address: str,
    ) -> Optional[ArcIdentity]:
        """
        Register Nia as an ERC-8004 agent on Arc.
        Stub: not implemented in v0.1.
        """
        logger.warning("ARC register_identity() called — not yet implemented")
        return None

    # ── Payments (future) ────────────────────────────────────────────────────

    def validate_payment_request(
        self,
        to_address: str,
        amount_usdc: str,
        description: str,
    ) -> ArcPaymentRequest:
        """
        Validate a payment request before sending it to the confirmation layer.
        Raises ValueError on invalid input.

        This runs BEFORE the three-level confirmation check in the orchestrator.
        make_payment is CRITICAL level — it always requires explicit confirmation.
        """
        if not to_address or not to_address.strip():
            raise ValueError("Payment recipient address is required.")
        try:
            amount_float = float(amount_usdc)
            if amount_float <= 0:
                raise ValueError("Payment amount must be positive.")
            if amount_float > 10_000:
                raise ValueError("Payment amount exceeds the per-transaction limit (10,000 USDC).")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid payment amount: {exc}") from exc

        return ArcPaymentRequest(
            to_address=to_address.strip(),
            amount_usdc=amount_usdc.strip(),
            description=description.strip()[:200],
        )

    async def send_payment(
        self,
        request: ArcPaymentRequest,
    ) -> ArcPaymentResult:
        """
        Execute a USDC payment on Arc. Stub: not implemented in v0.1.
        """
        logger.warning("ARC send_payment() called — not yet implemented")
        return ArcPaymentResult(
            success=False,
            error=(
                "Arc payments are not yet active. "
                "This feature will be enabled in a future version."
            ),
        )

    # ── Task attestations (future) ────────────────────────────────────────────

    async def attest_tool_execution(
        self,
        tool_id: str,
        result_hash: str,
        user_id: str,
    ) -> Optional[str]:
        """
        Record a tool execution result onchain as a verifiable attestation.
        Stub: returns None in v0.1.
        """
        logger.debug("ARC attest_tool_execution() called — stub returns None")
        return None


# Module-level singleton
arc_service = ArcService()
