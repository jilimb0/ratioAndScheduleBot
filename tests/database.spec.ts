import { beforeEach, describe, expect, it } from 'vitest';
import { DEFAULT_SCHEDULE } from '../src/config';
import {
  activateUserPro,
  addUserTask,
  clearDatabase,
  deleteUserTask,
  getAllActiveUserIds,
  getCompletionRate,
  getPendingSnoozedTasks,
  getRatioAnalytics,
  getTodayTasksStatus,
  getUserSchedule,
  getUserStats,
  getUserStreak,
  getUserTimezone,
  initDb,
  isTaskCompletedToday,
  isUserPro,
  markTaskCompleted,
  recordPayment,
  registerUser,
  setUserTimezone,
  skipTask,
  snoozeTask,
} from '../src/database';

describe('DatabaseService (TypeScript)', () => {
  beforeEach(() => {
    clearDatabase();
    initDb();
  });

  it('initDb should run without error', () => {
    expect(() => initDb()).not.toThrow();
  });

  it('registerUser should create user record', () => {
    registerUser(1, 'testuser', 'Test');
    const status = getTodayTasksStatus(1);
    expect(status).toBeDefined();
    expect(typeof status).toBe('object');
  });

  it('registerUser updates existing user info', () => {
    registerUser(1, 'oldname', 'Old');
    const updated = registerUser(1, 'newname', 'New');
    expect(updated.username).toBe('newname');
    expect(updated.firstName).toBe('New');
  });

  it('markTaskCompleted returns true and false on duplicate', () => {
    const res1 = markTaskCompleted(1, 'morning_workout');
    expect(res1).toBe(true);
    const res2 = markTaskCompleted(1, 'morning_workout');
    expect(res2).toBe(false);
  });

  it('getTodayTasksStatus shows correct status', () => {
    markTaskCompleted(1, 'morning_workout');
    const status = getTodayTasksStatus(1);
    expect(status.morning_workout).toBe(true);
    expect(status.breakfast).toBe(false);
  });

  it('getTodayTasksStatus returns false for all pending', () => {
    const status = getTodayTasksStatus(1);
    for (const slot of DEFAULT_SCHEDULE) {
      expect(status[slot.id]).toBe(false);
    }
  });

  it('getUserStats returns tasks by date', () => {
    markTaskCompleted(1, 'morning_workout');
    markTaskCompleted(1, 'breakfast');
    const stats = getUserStats(1, 7);
    const todayStr = new Date().toISOString().split('T')[0];
    expect(stats[todayStr]).toBeDefined();
    expect(stats[todayStr].length).toBe(2);
  });

  it('getUserStats empty for unknown user', () => {
    const stats = getUserStats(999, 7);
    expect(Object.keys(stats).length).toBe(0);
  });

  it('getCompletionRate returns float percentage', () => {
    markTaskCompleted(1, 'morning_workout');
    const rate = getCompletionRate(1, 7);
    expect(typeof rate).toBe('number');
    expect(rate).toBeGreaterThanOrEqual(0);
    expect(rate).toBeLessThanOrEqual(100);
  });

  it('getCompletionRate returns 0 for no activity', () => {
    const rate = getCompletionRate(999, 7);
    expect(rate).toBe(0);
  });

  it('isTaskCompletedToday checks correctly', () => {
    expect(isTaskCompletedToday(1, 'morning_workout')).toBe(false);
    markTaskCompleted(1, 'morning_workout');
    expect(isTaskCompletedToday(1, 'morning_workout')).toBe(true);
    expect(isTaskCompletedToday(999, 'morning_workout')).toBe(false);
  });

  it('getAllActiveUserIds returns all registered users', () => {
    registerUser(1, 'test1');
    registerUser(2, 'test2');
    const users = getAllActiveUserIds();
    expect(users).toContain(1);
    expect(users).toContain(2);
  });

  it('multiple users have independent stats', () => {
    markTaskCompleted(1, 'morning_workout');
    expect(isTaskCompletedToday(2, 'morning_workout')).toBe(false);
    markTaskCompleted(2, 'morning_workout');
    expect(isTaskCompletedToday(1, 'morning_workout')).toBe(true);
    expect(isTaskCompletedToday(2, 'morning_workout')).toBe(true);
  });

  it('timezone getter and setter', () => {
    registerUser(1, 'tzuser');
    setUserTimezone(1, 'Asia/Almaty');
    expect(getUserTimezone(1)).toBe('Asia/Almaty');
  });

  it('user schedules CRUD and day-of-week filtering', () => {
    registerUser(1, 'scheduser');
    const sched = getUserSchedule(1);
    expect(sched.length).toBeGreaterThan(0);

    addUserTask(1, 'deep_work', 'Глубокая работа', '10:00', 'work', 90, '1,2,3,4,5');
    const schedUpdated = getUserSchedule(1);
    const keys = schedUpdated.map((s) => s.task_key);
    expect(keys).toContain('deep_work');

    // Friday = 5, Sunday = 7
    const fridayTasks = getUserSchedule(1, 5).map((t) => t.task_key);
    const sundayTasks = getUserSchedule(1, 7).map((t) => t.task_key);
    expect(fridayTasks).toContain('deep_work');
    expect(sundayTasks).not.toContain('deep_work');

    deleteUserTask(1, 'deep_work');
    const schedAfter = getUserSchedule(1).map((s) => s.task_key);
    expect(schedAfter).not.toContain('deep_work');
  });

  it('snooze and skip task functionality', () => {
    registerUser(1, 'snoozer');
    const snoozeUntil = snoozeTask(1, 'morning_workout', -1);
    expect(snoozeUntil).toBeDefined();

    const pending = getPendingSnoozedTasks();
    expect(pending.some((p) => p.task_key === 'morning_workout')).toBe(true);

    const skipped = skipTask(1, 'breakfast');
    expect(skipped).toBe(true);
    expect(isTaskCompletedToday(1, 'breakfast')).toBe(true);
  });

  it('ratio analytics computation', () => {
    registerUser(1, 'ratiouser');
    markTaskCompleted(1, 'study_task', 'study', 60);
    markTaskCompleted(1, 'health_task', 'health', 45);

    const analytics = getRatioAnalytics(1, 7);
    expect(analytics.total_tasks).toBe(2);
    expect(analytics.total_minutes).toBe(105);
    expect(analytics.work_minutes).toBe(60);
    expect(analytics.rest_minutes).toBe(45);
    expect(analytics.work_to_rest_ratio).toBeGreaterThan(0);
    expect(analytics.balance_score).toBeGreaterThanOrEqual(0);
    expect(analytics.balance_score).toBeLessThanOrEqual(100);
  });

  it('user streak tracking', () => {
    registerUser(1, 'streakuser');
    expect(getUserStreak(1)).toBe(0);

    markTaskCompleted(1, 'morning_workout');
    expect(getUserStreak(1)).toBe(1);
  });

  it('pro activation and idempotent payments', () => {
    registerUser(1, 'prouser');
    expect(isUserPro(1)).toBe(false);

    activateUserPro(1, 30);
    expect(isUserPro(1)).toBe(true);

    const res1 = recordPayment(1, 'tg_123', 'prov_123', 150);
    expect(res1).toBe(true);
    expect(isUserPro(1)).toBe(true);

    // Idempotency: duplicate payment charge_id returns false
    const res2 = recordPayment(1, 'tg_123', 'prov_123', 150);
    expect(res2).toBe(false);
  });
});
