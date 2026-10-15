import { CATEGORIES } from './config';
import type { CategoryKey, CompletedTask, RatioAnalytics } from './types';

export function calculateRatioAnalytics(tasks: CompletedTask[], _days = 7): RatioAnalytics {
  const categories: RatioAnalytics['categories'] = {
    work: {
      name: CATEGORIES.work.name,
      emoji: CATEGORIES.work.emoji,
      minutes: 0,
      count: 0,
      percentage: 0,
    },
    rest: {
      name: CATEGORIES.rest.name,
      emoji: CATEGORIES.rest.emoji,
      minutes: 0,
      count: 0,
      percentage: 0,
    },
    health: {
      name: CATEGORIES.health.name,
      emoji: CATEGORIES.health.emoji,
      minutes: 0,
      count: 0,
      percentage: 0,
    },
    study: {
      name: CATEGORIES.study.name,
      emoji: CATEGORIES.study.emoji,
      minutes: 0,
      count: 0,
      percentage: 0,
    },
    routine: {
      name: CATEGORIES.routine.name,
      emoji: CATEGORIES.routine.emoji,
      minutes: 0,
      count: 0,
      percentage: 0,
    },
  };

  let totalMinutes = 0;
  let totalTasks = 0;

  for (const task of tasks) {
    const cat = categories[task.category] || categories.routine;
    cat.minutes += task.durationMinutes;
    cat.count += 1;
    totalMinutes += task.durationMinutes;
    totalTasks += 1;
  }

  if (totalMinutes > 0) {
    for (const key of Object.keys(categories) as CategoryKey[]) {
      categories[key].percentage = Number(
        ((categories[key].minutes / totalMinutes) * 100).toFixed(1),
      );
    }
  }

  const workMinutes = categories.work.minutes + categories.study.minutes;
  const restMinutes = categories.rest.minutes + categories.health.minutes;

  let workToRestRatio: number;
  if (restMinutes > 0) {
    workToRestRatio = Number((workMinutes / restMinutes).toFixed(2));
  } else if (workMinutes > 0) {
    workToRestRatio = 9.99;
  } else {
    workToRestRatio = 1.0;
  }

  let balanceScore = 80;
  let recommendation = '👍 Стабильный темп. Продолжайте фиксировать привычки.';

  if (totalMinutes === 0) {
    balanceScore = 0;
    recommendation = 'За выбранный период пока нет выполненных задач. Начните с первой привычки!';
  } else if (workToRestRatio >= 1.2 && workToRestRatio <= 2.5 && restMinutes > 0) {
    balanceScore = 92;
    recommendation = '🌟 Прекрасный баланс! Нагрузка и восстановление гармонично сбалансированы.';
  } else if (workToRestRatio > 3.0) {
    balanceScore = Math.max(40, 100 - Math.round(workToRestRatio * 15));
    recommendation =
      '⚠️ Высокий риск перегрузки! Время работы значительно превышает отдых. Запланируйте паузы.';
  } else if (workToRestRatio < 0.8) {
    balanceScore = 70;
    recommendation =
      '💡 Много времени на восстановление. Отличное время добавить важные рабочие цели!';
  }

  // Generate visual progress bar (e.g. 10 blocks: 💼💼💼🎮🎮...)
  const barBlocks = 10;
  let progressBar = '';
  if (totalMinutes > 0) {
    const workBlocks = Math.round((workMinutes / totalMinutes) * barBlocks);
    const restBlocks = Math.round((restMinutes / totalMinutes) * barBlocks);
    const routineBlocks = Math.max(0, barBlocks - workBlocks - restBlocks);
    progressBar = '💼'.repeat(workBlocks) + '🎮'.repeat(restBlocks) + '🍳'.repeat(routineBlocks);
  } else {
    progressBar = '▫️'.repeat(barBlocks);
  }

  return {
    categories,
    totalMinutes,
    totalTasks,
    workMinutes,
    restMinutes,
    workToRestRatio,
    balanceScore,
    recommendation,
    progressBar,
  };
}

export function formatRatioAnalyticsMessage(analytics: RatioAnalytics): string {
  if (analytics.totalMinutes === 0) {
    return `⚖️ <b>Баланс времени (Work / Rest Ratio)</b>\n\n${analytics.recommendation}`;
  }

  const workHours = (analytics.workMinutes / 60).toFixed(1);
  const restHours = (analytics.restMinutes / 60).toFixed(1);

  return `⚖️ <b>Баланс времени (Work / Rest Ratio)</b>

🎯 <b>Коэффициент Ratio:</b> <code>${analytics.workToRestRatio}:1</code>
📊 <b>Индекс баланса:</b> <b>${analytics.balanceScore}/100</b>
${analytics.progressBar}

💼 <b>Работа & Учеба:</b> ${workHours} ч. (${analytics.categories.work.percentage + analytics.categories.study.percentage}%)
🎮 <b>Отдых & Здоровье:</b> ${restHours} ч. (${analytics.categories.rest.percentage + analytics.categories.health.percentage}%)

💡 <b>Рекомендация:</b>
${analytics.recommendation}`;
}
