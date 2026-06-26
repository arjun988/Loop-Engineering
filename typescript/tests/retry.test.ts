import { retryAsync } from '../src/retry.js';

describe('retryAsync', () => {
  it('succeeds on first try', async () => {
    let count = 0;
    const result = await retryAsync(async () => {
      count++;
      return 'ok';
    });
    expect(result).toBe('ok');
    expect(count).toBe(1);
  });

  it('retries after failures', async () => {
    let count = 0;
    const result = await retryAsync(
      async () => {
        count++;
        if (count < 3) throw new Error('not yet');
        return 'ok';
      },
      { maxAttempts: 3, baseDelay: 10 }
    );
    expect(result).toBe('ok');
    expect(count).toBe(3);
  });

  it('throws after max attempts', async () => {
    await expect(
      retryAsync(async () => {
        throw new Error('always fails');
      }, { maxAttempts: 2, baseDelay: 10 })
    ).rejects.toThrow('always fails');
  });
});
