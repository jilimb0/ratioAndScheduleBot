import { describe, expect, it } from 'vitest';
import { TokenBucketLimiter } from '../src/limiter';

describe('TokenBucketLimiter', () => {
  it('allows consumption within token capacity', () => {
    const limiter = new TokenBucketLimiter({
      capacity: 3,
      refillRatePerSec: 1,
    });

    const user = 'user_1';
    expect(limiter.consume(user).allowed).toBe(true);
    expect(limiter.consume(user).allowed).toBe(true);
    expect(limiter.consume(user).allowed).toBe(true);

    // 4th consumption exceeds capacity
    const exceeded = limiter.consume(user);
    expect(exceeded.allowed).toBe(false);
    expect(exceeded.retryAfterMs).toBeGreaterThan(0);
  });

  it('isolates different users', () => {
    const limiter = new TokenBucketLimiter({
      capacity: 1,
      refillRatePerSec: 1,
    });

    expect(limiter.consume('alice').allowed).toBe(true);
    expect(limiter.consume('alice').allowed).toBe(false);

    // bob should still have full quota
    expect(limiter.consume('bob').allowed).toBe(true);
  });

  it('resets correctly on manual reset', () => {
    const limiter = new TokenBucketLimiter({
      capacity: 1,
      refillRatePerSec: 1,
    });

    expect(limiter.consume('alice').allowed).toBe(true);
    expect(limiter.consume('alice').allowed).toBe(false);

    limiter.reset('alice');
    expect(limiter.consume('alice').allowed).toBe(true);
  });
});
