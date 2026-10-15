export type CategoryKey = 'work' | 'rest' | 'health' | 'study' | 'routine';

export interface CategoryInfo {
  name: string;
  emoji: string;
}

export interface ScheduleSlot {
  id: string;
  time: string;
  message: string;
  buttonText: string;
  category: CategoryKey;
  durationMinutes: number;
}

export interface CompletedTask {
  id: string;
  userId: number;
  category: CategoryKey;
  durationMinutes: number;
  completionDate: string; // YYYY-MM-DD
}

export interface CategoryStat {
  name: string;
  emoji: string;
  minutes: number;
  count: number;
  percentage: number;
}

export interface RatioAnalytics {
  categories: Record<CategoryKey, CategoryStat>;
  totalMinutes: number;
  totalTasks: number;
  workMinutes: number;
  restMinutes: number;
  workToRestRatio: number;
  balanceScore: number;
  recommendation: string;
  progressBar: string;
}
