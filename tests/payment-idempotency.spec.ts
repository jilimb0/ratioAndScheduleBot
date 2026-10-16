import { describe, expect, it } from 'vitest';
import { PaymentIdempotencyManager } from '../src/payment-idempotency';

describe('PaymentIdempotencyManager', () => {
  it('deduplicates payments by chargeId', () => {
    const manager = new PaymentIdempotencyManager();
    const chargeId = 'stars_charge_abc123';

    expect(manager.claimPayment(chargeId, 999)).toBe(true);
    // Duplicate attempt fails
    expect(manager.claimPayment(chargeId, 999)).toBe(false);
    expect(manager.isPaymentProcessed(chargeId)).toBe(true);
  });

  it('deduplicates incoming telegram update IDs', () => {
    const manager = new PaymentIdempotencyManager();
    const updateId = 8812345;

    expect(manager.claimUpdate(updateId)).toBe(true);
    // Replay/retry of same update is ignored
    expect(manager.claimUpdate(updateId)).toBe(false);

    // Different update is accepted
    expect(manager.claimUpdate(updateId + 1)).toBe(true);
  });

  it('resets correctly', () => {
    const manager = new PaymentIdempotencyManager();
    const chargeId = 'charge_999';

    expect(manager.claimPayment(chargeId)).toBe(true);
    manager.reset();
    expect(manager.claimPayment(chargeId)).toBe(true);
  });
});
