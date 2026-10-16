/**
 * Idempotency store for Telegram Stars payments and Webhook updates.
 * Prevents duplicate subscription upgrades and repeated execution on Telegram retries.
 */

interface PaymentRecord {
  chargeId: string;
  userId?: number;
  processedAt: number;
}

export class PaymentIdempotencyManager {
  private processedPayments = new Map<string, PaymentRecord>();
  private processedUpdates = new Map<number, number>(); // update_id -> timestamp
  private readonly paymentTtlMs: number;
  private readonly updateTtlMs: number;

  constructor(options?: { paymentTtlMs?: number; updateTtlMs?: number }) {
    // Retain payment charge records for 30 days by default
    this.paymentTtlMs = options?.paymentTtlMs ?? 30 * 24 * 60 * 60 * 1000;
    // Retain update_ids for 1 hour by default (Telegram retry window is usually <= 24h)
    this.updateTtlMs = options?.updateTtlMs ?? 60 * 60 * 1000;
  }

  /**
   * Attempts to claim and record a payment charge ID.
   * Returns true if newly claimed, false if this payment was already processed.
   */
  public claimPayment(chargeId: string, userId?: number): boolean {
    if (!chargeId) return true;

    const existing = this.processedPayments.get(chargeId);
    const now = Date.now();

    if (existing && now - existing.processedAt < this.paymentTtlMs) {
      return false; // Already processed
    }

    this.processedPayments.set(chargeId, {
      chargeId,
      userId,
      processedAt: now,
    });
    return true;
  }

  /**
   * Checks if an update was already received and processed.
   * Returns true if first time seeing this update_id, false if duplicate.
   */
  public claimUpdate(updateId: number): boolean {
    if (!updateId) return true;

    const existing = this.processedUpdates.get(updateId);
    const now = Date.now();

    if (existing && now - existing < this.updateTtlMs) {
      return false; // Duplicate update delivery
    }

    this.processedUpdates.set(updateId, now);
    return true;
  }

  public isPaymentProcessed(chargeId: string): boolean {
    const existing = this.processedPayments.get(chargeId);
    if (!existing) return false;
    if (Date.now() - existing.processedAt > this.paymentTtlMs) {
      this.processedPayments.delete(chargeId);
      return false;
    }
    return true;
  }

  public reset(): void {
    this.processedPayments.clear();
    this.processedUpdates.clear();
  }

  public cleanup(now = Date.now()): void {
    for (const [chargeId, record] of this.processedPayments.entries()) {
      if (now - record.processedAt > this.paymentTtlMs) {
        this.processedPayments.delete(chargeId);
      }
    }
    for (const [updateId, timestamp] of this.processedUpdates.entries()) {
      if (now - timestamp > this.updateTtlMs) {
        this.processedUpdates.delete(updateId);
      }
    }
  }
}

export const globalPaymentIdempotency = new PaymentIdempotencyManager();
