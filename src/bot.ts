import {
  type BotClient,
  createBotClient,
  type InlineKeyboardMarkup,
  validateInitData,
} from '@tgwrapper/core';
import { COMMON_TIMEZONES, DEFAULT_SCHEDULE, MESSAGES, PRO_PRICE_STARS } from './config';
import { calculateRatioAnalytics, formatRatioAnalyticsMessage } from './engine';
import type { CompletedTask } from './types';

export interface RatioBotOptions {
  token: string;
  botUsername?: string;
}

export function createRatioBot(options: RatioBotOptions): {
  client: BotClient;
  handleMessage: (
    chatId: number | string,
    text: string,
    userTasks?: CompletedTask[],
  ) => Promise<string>;
  handleCallbackQuery: (callbackData: string) => Promise<string>;
  validateTma: (initData: string) => boolean;
} {
  const client = createBotClient({ token: options.token });

  const getSettingsKeyboard = (): InlineKeyboardMarkup => ({
    inline_keyboard: COMMON_TIMEZONES.slice(0, 6).map((tz) => [
      {
        text: tz.label,
        callback_data: `settz_${tz.code}`,
      },
    ]),
  });

  const getProKeyboard = (): InlineKeyboardMarkup => ({
    inline_keyboard: [
      [
        {
          text: `⭐ Оплатить ${PRO_PRICE_STARS} Telegram Stars`,
          callback_data: 'buy_pro_stars',
        },
      ],
    ],
  });

  const handleMessage = async (
    chatId: number | string,
    text: string,
    userTasks: CompletedTask[] = [],
  ): Promise<string> => {
    const trimmed = text.trim();

    if (trimmed.startsWith('/start') || trimmed === 'ℹ️ Помощь') {
      await client.sendMessage(chatId, MESSAGES.start, {
        parse_mode: 'HTML',
      });
      return MESSAGES.start;
    }

    if (trimmed.startsWith('/ratio') || trimmed.includes('Баланс')) {
      const analytics = calculateRatioAnalytics(userTasks);
      const msg = formatRatioAnalyticsMessage(analytics);
      await client.sendMessage(chatId, msg, { parse_mode: 'HTML' });
      return msg;
    }

    if (trimmed.startsWith('/schedule') || trimmed.includes('Расписание')) {
      const lines = DEFAULT_SCHEDULE.map(
        (slot) => `• <b>${slot.time}</b> — ${slot.message} (<i>${slot.durationMinutes} мин</i>)`,
      );
      const msg = `🗓 <b>Ваше расписание на сегодня:</b>\n\n${lines.join('\n')}`;
      await client.sendMessage(chatId, msg, { parse_mode: 'HTML' });
      return msg;
    }

    if (trimmed.startsWith('/status') || trimmed.includes('Статус')) {
      const msg = `${MESSAGES.status_header}\n\n✅ Выполнено задач: <b>${userTasks.length}</b>\n🔥 Стрик: <b>3 дня подряд</b>`;
      await client.sendMessage(chatId, msg, { parse_mode: 'HTML' });
      return msg;
    }

    if (trimmed.startsWith('/briefing') || trimmed.includes('Брифинг')) {
      const msg = `🌅 <b>Утренний брифинг продуктивности</b>\n\nСегодня запланировано <b>${DEFAULT_SCHEDULE.length}</b> активностей.\nНе забудьте сбалансировать работу перерывами каждые 90 минут! ✨`;
      await client.sendMessage(chatId, msg, { parse_mode: 'HTML' });
      return msg;
    }

    if (trimmed.startsWith('/settings') || trimmed.includes('Настройки')) {
      const msg = '⚙️ <b>Выберите ваш часовой пояс:</b>';
      await client.sendMessage(chatId, msg, {
        parse_mode: 'HTML',
        reply_markup: getSettingsKeyboard(),
      });
      return msg;
    }

    if (trimmed.startsWith('/pro') || trimmed.startsWith('/stars_pay') || trimmed.includes('Pro')) {
      const msg = `${MESSAGES.pro_title}\n\n${MESSAGES.pro_description}\n\nСтоимость подписки: <b>${PRO_PRICE_STARS} ⭐ Stars</b>`;
      await client.sendMessage(chatId, msg, {
        parse_mode: 'HTML',
        reply_markup: getProKeyboard(),
      });
      return msg;
    }

    const fallback = '🤔 Не понял команду. Введите /start или выберите действие в меню.';
    await client.sendMessage(chatId, fallback);
    return fallback;
  };

  const handleCallbackQuery = async (callbackData: string): Promise<string> => {
    if (callbackData.startsWith('settz_')) {
      const tzCode = callbackData.replace('settz_', '');
      return `Часовой пояс успешно изменен на ${tzCode} ✅`;
    }
    if (callbackData === 'buy_pro_stars') {
      return `Счет на ${PRO_PRICE_STARS} Stars сформирован! 🚀`;
    }
    return 'Действие выполнено';
  };

  const validateTma = (initData: string): boolean => {
    return validateInitData(initData, options.token);
  };

  return {
    client,
    handleMessage,
    handleCallbackQuery,
    validateTma,
  };
}
