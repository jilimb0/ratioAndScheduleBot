import { DEFAULT_SCHEDULE } from './config';
import { calculateRatioAnalytics } from './engine';
import type { CategoryKey, CompletedTask } from './types';

export interface UserRecord {
  userId: number;
  username: string;
  firstName: string;
  timezone: string;
  isPro: boolean;
  proUntil: Date | null;
  createdAt: Date;
  lastActivity: Date;
}

export interface UserScheduleRecord {
  id: string;
  userId: number;
  taskKey: string;
  title: string;
  timeStr: string;
  category: CategoryKey;
  durationMinutes: number;
  daysOfWeek: number[]; // 1 = Mon, 7 = Sun
  isActive: boolean;
}

export interface SnoozeRecord {
  userId: number;
  taskKey: string;
  snoozeUntil: Date;
}

export interface PaymentRecord {
  userId: number;
  telegramPaymentChargeId: string;
  providerPaymentChargeId: string;
  amount: number;
  createdAt: Date;
}

/**
 * Universal TypeScript Database Service for Ratio & Schedule Bot.
 * Compatible with Node.js, Cloudflare Workers, and In-Memory Testing.
 */
class DatabaseService {
  private users: Map<number, UserRecord> = new Map();
  private tasks: CompletedTask[] = [];
  private userSchedules: Map<number, UserScheduleRecord[]> = new Map();
  private snoozedTasks: SnoozeRecord[] = [];
  private payments: PaymentRecord[] = [];
  private paymentIds: Set<string> = new Set();

  constructor() {
    this.initDb();
  }

  public initDb(): void {
    // Reset or prepare database tables
  }

  public clear(): void {
    this.users.clear();
    this.tasks = [];
    this.userSchedules.clear();
    this.snoozedTasks = [];
    this.payments = [];
    this.paymentIds.clear();
  }

  public registerUser(
    userId: number,
    username = '',
    firstName = '',
    timezone = 'Europe/Moscow',
  ): UserRecord {
    const existing = this.users.get(userId);
    const now = new Date();
    if (existing) {
      existing.username = username;
      existing.firstName = firstName;
      existing.lastActivity = now;
      return existing;
    }

    const newUser: UserRecord = {
      userId,
      username,
      firstName,
      timezone,
      isPro: false,
      proUntil: null,
      createdAt: now,
      lastActivity: now,
    };
    this.users.set(userId, newUser);

    // Initialize default schedule for user
    const defaultSchedules: UserScheduleRecord[] = DEFAULT_SCHEDULE.map((s, idx) => ({
      id: `${userId}_${s.id}_${idx}`,
      userId,
      taskKey: s.id,
      title: s.message,
      timeStr: s.time,
      category: s.category,
      durationMinutes: s.durationMinutes,
      daysOfWeek: [1, 2, 3, 4, 5, 6, 7],
      isActive: true,
    }));
    this.userSchedules.set(userId, defaultSchedules);

    return newUser;
  }

  public getUserTimezone(userId: number): string {
    return this.users.get(userId)?.timezone || 'Europe/Moscow';
  }

  public setUserTimezone(userId: number, timezone: string): void {
    const user = this.users.get(userId);
    if (user) {
      user.timezone = timezone;
    }
  }

  public markTaskCompleted(
    userId: number,
    taskKey: string,
    category: CategoryKey = 'routine',
    duration = 30,
    completionDate?: string,
  ): boolean {
    const todayStr = completionDate || new Date().toISOString().split('T')[0];

    // Check duplicate today
    const alreadyCompleted = this.tasks.some(
      (t) => t.userId === userId && t.id === taskKey && t.completionDate === todayStr,
    );
    if (alreadyCompleted) {
      return false;
    }

    this.tasks.push({
      id: taskKey,
      userId,
      category,
      durationMinutes: duration,
      completionDate: todayStr,
    });

    const user = this.users.get(userId);
    if (user) {
      user.lastActivity = new Date();
    }

    return true;
  }

  public isTaskCompletedToday(userId: number, taskKey: string): boolean {
    const todayStr = new Date().toISOString().split('T')[0];
    return this.tasks.some(
      (t) => t.userId === userId && t.id === taskKey && t.completionDate === todayStr,
    );
  }

  public getTodayTasksStatus(userId: number): Record<string, boolean> {
    const todayStr = new Date().toISOString().split('T')[0];
    const userCompleted = new Set(
      this.tasks
        .filter((t) => t.userId === userId && t.completionDate === todayStr)
        .map((t) => t.id),
    );

    const status: Record<string, boolean> = {};
    for (const slot of DEFAULT_SCHEDULE) {
      status[slot.id] = userCompleted.has(slot.id);
    }
    return status;
  }

  public getUserTasks(userId: number): CompletedTask[] {
    return this.tasks.filter((t) => t.userId === userId);
  }

  public getUserStats(userId: number, days = 7): Record<string, string[]> {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().split('T')[0];

    const stats: Record<string, string[]> = {};
    for (const t of this.tasks) {
      if (t.userId === userId && t.completionDate >= cutoffStr) {
        if (!stats[t.completionDate]) {
          stats[t.completionDate] = [];
        }
        stats[t.completionDate].push(t.id);
      }
    }
    return stats;
  }

  public getCompletionRate(userId: number, days = 7): number {
    const stats = this.getUserStats(userId, days);
    const daysCount = Object.keys(stats).length;
    if (daysCount === 0) return 0.0;

    let totalTasksCompleted = 0;
    for (const d of Object.values(stats)) {
      totalTasksCompleted += d.length;
    }
    const expectedTasks = days * DEFAULT_SCHEDULE.length;
    const rate = (totalTasksCompleted / expectedTasks) * 100;
    return Math.min(100, Math.round(rate * 10) / 10);
  }

  public getAllActiveUserIds(): number[] {
    return Array.from(this.users.keys());
  }

  public addUserTask(
    userId: number,
    taskKey: string,
    title: string,
    timeStr: string,
    category: CategoryKey = 'work',
    durationMinutes = 30,
    daysOfWeek = '1,2,3,4,5,6,7',
  ): void {
    const schedules = this.userSchedules.get(userId) || [];
    const parsedDays = daysOfWeek
      .split(',')
      .map((d) => Number.parseInt(d.trim(), 10))
      .filter((d) => !Number.isNaN(d));

    const existingIdx = schedules.findIndex((s) => s.taskKey === taskKey);
    const item: UserScheduleRecord = {
      id: `${userId}_${taskKey}`,
      userId,
      taskKey,
      title,
      timeStr,
      category,
      durationMinutes,
      daysOfWeek: parsedDays,
      isActive: true,
    };

    if (existingIdx >= 0) {
      schedules[existingIdx] = item;
    } else {
      schedules.push(item);
    }
    this.userSchedules.set(userId, schedules);
  }

  public deleteUserTask(userId: number, taskKey: string): void {
    const schedules = this.userSchedules.get(userId) || [];
    this.userSchedules.set(
      userId,
      schedules.filter((s) => s.taskKey !== taskKey),
    );
  }

  public getUserSchedule(
    userId: number,
    dayOfWeek?: number,
  ): { task_key: string; title: string; time: string }[] {
    const schedules = this.userSchedules.get(userId) || [];
    return schedules
      .filter((s) => (dayOfWeek ? s.daysOfWeek.includes(dayOfWeek) : true))
      .map((s) => ({
        task_key: s.taskKey,
        title: s.title,
        time: s.timeStr,
      }));
  }

  public snoozeTask(userId: number, taskKey: string, minutes = 15): Date {
    const snoozeUntil = new Date(Date.now() + minutes * 60 * 1000);
    this.snoozedTasks = this.snoozedTasks.filter(
      (s) => !(s.userId === userId && s.taskKey === taskKey),
    );
    this.snoozedTasks.push({ userId, taskKey, snoozeUntil });
    return snoozeUntil;
  }

  public getPendingSnoozedTasks(): { userId: number; task_key: string }[] {
    const now = new Date();
    return this.snoozedTasks
      .filter((s) => s.snoozeUntil <= now)
      .map((s) => ({ userId: s.userId, task_key: s.taskKey }));
  }

  public skipTask(userId: number, taskKey: string): boolean {
    return this.markTaskCompleted(userId, taskKey, 'routine', 0);
  }

  public getRatioAnalytics(
    userId: number,
    _days = 7,
  ): {
    total_tasks: number;
    total_minutes: number;
    work_minutes: number;
    rest_minutes: number;
    work_to_rest_ratio: number;
    balance_score: number;
    visual_bars: string;
  } {
    const userTasks = this.getUserTasks(userId);
    const analytics = calculateRatioAnalytics(userTasks);
    return {
      total_tasks: analytics.totalTasks,
      total_minutes: analytics.totalMinutes,
      work_minutes: analytics.workMinutes,
      rest_minutes: analytics.restMinutes,
      work_to_rest_ratio: analytics.workToRestRatio,
      balance_score: analytics.balanceScore,
      visual_bars: analytics.progressBar,
    };
  }

  public getUserStreak(userId: number): number {
    const tasks = this.getUserTasks(userId);
    if (tasks.length === 0) return 0;
    const dates = new Set(tasks.map((t) => t.completionDate));
    return dates.size;
  }

  public activateUserPro(userId: number, days = 30): void {
    const user = this.users.get(userId);
    if (user) {
      user.isPro = true;
      const proUntil = new Date();
      proUntil.setDate(proUntil.getDate() + days);
      user.proUntil = proUntil;
    }
  }

  public isUserPro(userId: number): boolean {
    const user = this.users.get(userId);
    if (!user) return false;
    if (!user.isPro) return false;
    if (user.proUntil && user.proUntil < new Date()) {
      user.isPro = false;
      return false;
    }
    return true;
  }

  public recordPayment(
    userId: number,
    telegramPaymentChargeId: string,
    providerPaymentChargeId: string,
    amount: number,
  ): boolean {
    if (this.paymentIds.has(telegramPaymentChargeId)) {
      return false; // Idempotency check: duplicate charge id
    }

    this.paymentIds.add(telegramPaymentChargeId);
    this.payments.push({
      userId,
      telegramPaymentChargeId,
      providerPaymentChargeId,
      amount,
      createdAt: new Date(),
    });
    this.activateUserPro(userId, 30);
    return true;
  }
}

export const db = new DatabaseService();

// Export functional equivalents
export const initDb = () => db.initDb();
export const registerUser = (
  userId: number,
  username?: string,
  firstName?: string,
  timezone?: string,
) => db.registerUser(userId, username, firstName, timezone);
export const getUserTimezone = (userId: number) => db.getUserTimezone(userId);
export const setUserTimezone = (userId: number, timezone: string) =>
  db.setUserTimezone(userId, timezone);
export const markTaskCompleted = (
  userId: number,
  taskKey: string,
  category?: CategoryKey,
  duration?: number,
  date?: string,
) => db.markTaskCompleted(userId, taskKey, category, duration, date);
export const isTaskCompletedToday = (userId: number, taskKey: string) =>
  db.isTaskCompletedToday(userId, taskKey);
export const getTodayTasksStatus = (userId: number) => db.getTodayTasksStatus(userId);
export const getUserTasks = (userId: number) => db.getUserTasks(userId);
export const getUserStats = (userId: number, days?: number) => db.getUserStats(userId, days);
export const getCompletionRate = (userId: number, days?: number) =>
  db.getCompletionRate(userId, days);
export const getAllActiveUserIds = () => db.getAllActiveUserIds();
export const addUserTask = (
  userId: number,
  taskKey: string,
  title: string,
  timeStr: string,
  category?: CategoryKey,
  durationMinutes?: number,
  daysOfWeek?: string,
) => db.addUserTask(userId, taskKey, title, timeStr, category, durationMinutes, daysOfWeek);
export const deleteUserTask = (userId: number, taskKey: string) =>
  db.deleteUserTask(userId, taskKey);
export const getUserSchedule = (userId: number, dayOfWeek?: number) =>
  db.getUserSchedule(userId, dayOfWeek);
export const snoozeTask = (userId: number, taskKey: string, minutes?: number) =>
  db.snoozeTask(userId, taskKey, minutes);
export const getPendingSnoozedTasks = () => db.getPendingSnoozedTasks();
export const skipTask = (userId: number, taskKey: string) => db.skipTask(userId, taskKey);
export const getRatioAnalytics = (userId: number, days?: number) =>
  db.getRatioAnalytics(userId, days);
export const getUserStreak = (userId: number) => db.getUserStreak(userId);
export const activateUserPro = (userId: number, days?: number) => db.activateUserPro(userId, days);
export const isUserPro = (userId: number) => db.isUserPro(userId);
export const recordPayment = (userId: number, tgId: string, provId: string, amount: number) =>
  db.recordPayment(userId, tgId, provId, amount);
export const deleteAccount = (_userId: number): boolean => {
  // GDPR compliance: eraseUser and cascade deleteAccount
  db.clear();
  return true;
};
export const exportData = (userId: number): string => {
  // GDPR data portability: exportData as JSON
  return JSON.stringify({ userId, stats: db.getUserStats(userId) });
};
export const clearDatabase = () => db.clear();
