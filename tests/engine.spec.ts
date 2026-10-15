import { describe, expect, it } from 'vitest';
import { calculateRatioAnalytics, formatRatioAnalyticsMessage } from '../src/engine';
import type { CompletedTask } from '../src/types';

describe('Ratio Engine', () => {
  it('handles empty task list gracefully', () => {
    const analytics = calculateRatioAnalytics([]);
    expect(analytics.totalMinutes).toBe(0);
    expect(analytics.balanceScore).toBe(0);
    expect(analytics.workToRestRatio).toBe(1.0);
    expect(analytics.recommendation).toContain('нет выполненных задач');
  });

  it('calculates balanced ratio correctly (e.g. 1.5:1 to 2.5:1)', () => {
    const tasks: CompletedTask[] = [
      { id: '1', userId: 1, category: 'work', durationMinutes: 120, completionDate: '2026-10-15' },
      { id: '2', userId: 1, category: 'study', durationMinutes: 60, completionDate: '2026-10-15' },
      { id: '3', userId: 1, category: 'health', durationMinutes: 60, completionDate: '2026-10-15' },
      { id: '4', userId: 1, category: 'rest', durationMinutes: 30, completionDate: '2026-10-15' },
      {
        id: '5',
        userId: 1,
        category: 'routine',
        durationMinutes: 30,
        completionDate: '2026-10-15',
      },
    ];

    // work = 180 mins, rest = 90 mins -> ratio = 2.0
    const analytics = calculateRatioAnalytics(tasks);
    expect(analytics.workMinutes).toBe(180);
    expect(analytics.restMinutes).toBe(90);
    expect(analytics.workToRestRatio).toBe(2.0);
    expect(analytics.balanceScore).toBe(92);
    expect(analytics.recommendation).toContain('Прекрасный баланс');
    expect(analytics.progressBar).toContain('💼');
  });

  it('detects high burnout risk when work heavily exceeds rest', () => {
    const tasks: CompletedTask[] = [
      { id: '1', userId: 1, category: 'work', durationMinutes: 360, completionDate: '2026-10-15' },
      { id: '2', userId: 1, category: 'rest', durationMinutes: 30, completionDate: '2026-10-15' },
    ];

    const analytics = calculateRatioAnalytics(tasks);
    expect(analytics.workToRestRatio).toBe(12.0);
    expect(analytics.recommendation).toContain('Высокий риск перегрузки');
  });

  it('formats analytics telegram message properly', () => {
    const tasks: CompletedTask[] = [
      { id: '1', userId: 1, category: 'work', durationMinutes: 120, completionDate: '2026-10-15' },
      { id: '2', userId: 1, category: 'health', durationMinutes: 60, completionDate: '2026-10-15' },
    ];
    const analytics = calculateRatioAnalytics(tasks);
    const msg = formatRatioAnalyticsMessage(analytics);

    expect(msg).toContain('Баланс времени');
    expect(msg).toContain('Коэффициент Ratio:');
    expect(msg).toContain('Работа & Учеба:');
  });
});
