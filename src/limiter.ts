/**
 * Token Bucket Rate Limiter to protect against Telegram 429 Flood Wait
 * and user command spam in Webhook & Long Polling.
 */

export interface RateLimitOptions {
  capacity: number; // Maximum burst tokens
  refillRatePerSec: number; // Tokens added per second
  ttlMs?: number; // How long inactive bucket stays before cleanup
}

interface Bucket {
  tokens: number;
  lastRefill: number;
}

export class TokenBucketLimiter {
  private buckets = new Map<string, Bucket>();
  private readonly capacity: number;
  private readonly refillRatePerSec: number;
  private readonly ttlMs: number;

  constructor(options: RateLimitOptions) {
    this.capacity = options.capacity;
    this.refillRatePerSec = options.refillRatePerSec;
    this.ttlMs = options.ttlMs ?? 60_000;
  }

  public consume(
    key: string,
    tokensToConsume = 1,
  ): { allowed: boolean; remaining: number; retryAfterMs: number } {
    const now = Date.now();
    let bucket = this.buckets.get(key);

    if (!bucket) {
      bucket = { tokens: this.capacity, lastRefill: now };
      this.buckets.set(key, bucket);
    } else {
      // Calculate token refill
      const elapsedSec = (now - bucket.lastRefill) / 1000;
      const refilledTokens = elapsedSec * this.refillRatePerSec;
      bucket.tokens = Math.min(this.capacity, bucket.tokens + refilledTokens);
      bucket.lastRefill = now;
    }

    if (bucket.tokens >= tokensToConsume) {
      bucket.tokens -= tokensToConsume;
      return {
        allowed: true,
        remaining: Math.floor(bucket.tokens),
        retryAfterMs: 0,
      };
    }

    const deficit = tokensToConsume - bucket.tokens;
    const retryAfterMs = Math.ceil((deficit / this.refillRatePerSec) * 1000);

    return {
      allowed: false,
      remaining: Math.floor(bucket.tokens),
      retryAfterMs,
    };
  }

  public reset(key?: string): void {
    if (key) {
      this.buckets.delete(key);
    } else {
      this.buckets.clear();
    }
  }

  public cleanup(now = Date.now()): void {
    for (const [key, bucket] of this.buckets.entries()) {
      if (now - bucket.lastRefill > this.ttlMs) {
        this.buckets.delete(key);
      }
    }
  }
}

// Default limiter configured for Telegram bot user interactions (max 5 burst, 1 req/sec)
export const globalFloodLimiter = new TokenBucketLimiter({
  capacity: 5,
  refillRatePerSec: 1,
  ttlMs: 5 * 60_000,
});
