import type { CategoryInfo, CategoryKey, ScheduleSlot } from './types';

export const CATEGORIES: Record<CategoryKey, CategoryInfo> = {
  work: { name: 'Работа', emoji: '💼' },
  rest: { name: 'Отдых', emoji: '🎮' },
  health: { name: 'Здоровье и спорт', emoji: '🏃' },
  study: { name: 'Обучение', emoji: '📚' },
  routine: { name: 'Рутина и быт', emoji: '🍳' },
};

export const DEFAULT_SCHEDULE: ScheduleSlot[] = [
  {
    id: 'morning_workout',
    time: '08:15',
    message: '🏃‍♂️ Время утренней тренировки! Готов к активному старту дня?',
    buttonText: 'Тренировка выполнена ✅',
    category: 'health',
    durationMinutes: 45,
  },
  {
    id: 'breakfast',
    time: '09:00',
    message: '🍳 Время завтрака! Не забудь правильно питаться.',
    buttonText: 'Завтрак готов ✅',
    category: 'routine',
    durationMinutes: 30,
  },
  {
    id: 'lunch',
    time: '13:00',
    message: '🥗 Время обеда! Пора подкрепиться.',
    buttonText: 'Обед готов ✅',
    category: 'routine',
    durationMinutes: 45,
  },
  {
    id: 'language_study',
    time: '16:00',
    message: '📚 Время изучения языка! Не пропускай занятия.',
    buttonText: 'Язык изучен ✅',
    category: 'study',
    durationMinutes: 60,
  },
  {
    id: 'dinner',
    time: '19:00',
    message: '🍽️ Время ужина! Завершаем день вкусно.',
    buttonText: 'Ужин готов ✅',
    category: 'routine',
    durationMinutes: 45,
  },
  {
    id: 'daily_report',
    time: '21:00',
    message: '📊 Время подготовить отчёт о дне! Как дела?',
    buttonText: 'Отчёт готов ✅',
    category: 'work',
    durationMinutes: 30,
  },
];

export const PRO_PRICE_STARS = 150;

export const COMMON_TIMEZONES = [
  { code: 'Europe/Moscow', label: '🇷🇺 Москва (UTC+3)' },
  { code: 'Asia/Yekaterinburg', label: '🇷🇺 Екатеринбург (UTC+5)' },
  { code: 'Asia/Almaty', label: '🇰🇿 Алматы (UTC+5)' },
  { code: 'Asia/Tashkent', label: '🇺🇿 Ташкент (UTC+5)' },
  { code: 'Asia/Tbilisi', label: '🇬🇪 Тбилиси (UTC+4)' },
  { code: 'Asia/Yerevan', label: '🇦🇲 Ереван (UTC+4)' },
  { code: 'Asia/Dubai', label: '🇦🇪 Дубай (UTC+4)' },
  { code: 'Europe/Kyiv', label: '🇺🇦 Киев (UTC+2/3)' },
  { code: 'Europe/Berlin', label: '🇩🇪 Берлин (UTC+1/2)' },
  { code: 'Europe/London', label: '🇬🇧 Лондон (UTC+0/1)' },
  { code: 'UTC', label: '🌐 UTC (+0)' },
];

export const MESSAGES = {
  start: `🤖 <b>Привет! Я твой личный помощник по распорядку дня и балансу времени.</b>

📋 <b>Доступные команды:</b>
• /status — текущий статус задач на сегодня
• /ratio — инфографика соотношения работы и отдыха
• /schedule — персональное расписание дня
• /briefing — утренний брифинг
• /settings — выбор часового пояса
• /pro — подписка за Telegram Stars

Я помогу держать баланс между делами и отдыхом! 💪`,
  task_completed: '✅ Отлично! Задача выполнена.',
  status_header: '📊 <b>Статус задач на сегодня:</b>',
  pro_title: '⭐ <b>Ratio & Schedule PRO</b>',
  pro_description:
    'Безлимитная аналитика, кастомные привычки, интеграция с Google Calendar и Telegram Mini App!',
};
