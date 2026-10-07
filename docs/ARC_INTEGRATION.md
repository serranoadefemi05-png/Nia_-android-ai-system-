# NIA + Arc Integration

## Principle

**Do not put ordinary Android functionality onchain.**

Arc is used only where blockchain provides a real product advantage:
- Verifiable, auditable task records
- Agent identity and attestations
- USDC payments with user-controlled spending policies
- Agent marketplace discovery

## Status

| Feature | v0.1 | v0.2 | Future |
|---|---|---|---|
| Arc service interface | Stub | Real | — |
| Agent identity (ERC-8004) | Prepared | Implement | — |
| Task attestations | Prepared | Implement | — |
| USDC payments | Off | Implement | — |
| Spending policies | Defined | Enforce | — |
| Agent marketplace | — | — | v0.3+ |
| Agent-to-agent interactions | — | — | v0.4+ |

## Architecture

```
NIA Core (v0.1)         Arc Layer (v0.2+)
───────────────    →    ────────────────────────────
ActionRegistry          ArcService.recordAttestation()
Orchestrator            ArcService.getAgentIdentity()
TaskHistory             ArcService.requestPayment()
MemoryService           ArcService.discoverServices()
```

## v0.2 Implementation Plan

### 1. Agent Identity
- Register NIA as an ERC-8004 agent on Arc Testnet.
- Store agent card: name, capabilities, service endpoints.
- Display agent ID in the settings screen.

### 2. Task Attestations
- After each completed tool execution, optionally record an attestation onchain.
- User can opt in per task type.
- Attestation includes: task_id, intent, tool_id, success, timestamp.
- Useful for: audit trails, verifiable agent history, agent reputation.

### 3. USDC Payments (Arc-native gas)
- Arc uses USDC as native gas — no ETH needed.
- NIA payment flow:
  1. User says "Pay [recipient] [amount] USDC for [reason]".
  2. Intent: `make_payment` (CRITICAL / RED).
  3. Confirmation: user must type "confirm" + approve spending policy check.
  4. ArcService.requestPayment() initiates the transaction.
  5. Wait for confirmation, record attestation.
  6. Confirm to user with tx hash.

### 4. Spending Policies
```python
@dataclass
class SpendingPolicy:
    enabled: bool
    max_single_payment_usdc: float
    max_daily_usdc: float
    allowed_recipients: List[str]
    require_confirmation_above_usdc: float
```
- User sets their own spending limits.
- NIA enforces them before initiating any payment.
- No autonomous spending ever — every payment requires explicit user confirmation.

## What Stays Off-Chain

Everything basic:
- Voice recognition
- Screenshot capture
- File search
- Reminders
- App launching
- Web search
- Conversation memory

These are faster, cheaper, and more private without a blockchain.
