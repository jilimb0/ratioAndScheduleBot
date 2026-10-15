import crypto from 'node:crypto';
import { describe, expect, it, vi } from 'vitest';
import { createRatioBot } from '../src/bot';
import type { CompletedTask } from '../src/types';

describe('Ratio Bot with @tgwrapper/core', () => {
  const token = '123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ';
  const bot = createRatioBot({ token });

  it('handles /start command', async () => {
    vi.spyOn(bot.client, 'sendMessage').mockResolvedValue({} as any);

    const reply = await bot.handleMessage(12345, '/start');
    expect(reply).toContain('Привет! Я твой личный помощник');
    expect(bot.client.sendMessage).toHaveBeenCalledWith(
      12345,
      expect.stringContaining('Привет! Я твой личный помощник'),
      expect.objectContaining({ parse_mode: 'HTML' }),
    );
  });

  it('handles /ratio command with task data', async () => {
    vi.spyOn(bot.client, 'sendMessage').mockResolvedValue({} as any);

    const tasks: CompletedTask[] = [
      {
        id: '1',
        userId: 12345,
        category: 'work',
        durationMinutes: 180,
        completionDate: '2026-10-15',
      },
      {
        id: '2',
        userId: 12345,
        category: 'health',
        durationMinutes: 90,
        completionDate: '2026-10-15',
      },
    ];

    const reply = await bot.handleMessage(12345, '/ratio', tasks);
    expect(reply).toContain('Коэффициент Ratio:');
    expect(reply).toContain('2:1');
    expect(reply).toContain('Индекс баланса:');
  });

  it('handles /schedule command', async () => {
    vi.spyOn(bot.client, 'sendMessage').mockResolvedValue({} as any);

    const reply = await bot.handleMessage(12345, '/schedule');
    expect(reply).toContain('Ваше расписание на сегодня:');
    expect(reply).toContain('08:15');
    expect(reply).toContain('тренировки');
  });

  it('handles /settings command with timezone markup', async () => {
    vi.spyOn(bot.client, 'sendMessage').mockResolvedValue({} as any);

    const reply = await bot.handleMessage(12345, '/settings');
    expect(reply).toContain('Выберите ваш часовой пояс:');
    expect(bot.client.sendMessage).toHaveBeenCalledWith(
      12345,
      expect.stringContaining('часовой пояс'),
      expect.objectContaining({
        reply_markup: expect.objectContaining({
          inline_keyboard: expect.any(Array),
        }),
      }),
    );
  });

  it('handles /pro command with Stars payment button', async () => {
    vi.spyOn(bot.client, 'sendMessage').mockResolvedValue({} as any);

    const reply = await bot.handleMessage(12345, '/pro');
    expect(reply).toContain('Stars');
    expect(reply).toContain('150');
  });

  it('handles callback queries for timezones and Stars', async () => {
    const tzRes = await bot.handleCallbackQuery('settz_Europe/Moscow');
    expect(tzRes).toContain('Europe/Moscow');

    const starsRes = await bot.handleCallbackQuery('buy_pro_stars');
    expect(starsRes).toContain('150 Stars');
  });

  it('validates TMA initData with HMAC-SHA256 correctly', () => {
    // Generate valid initData query string
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(token).digest();
    const authDate = Math.floor(Date.now() / 1000).toString();
    const dataCheckString = `auth_date=${authDate}\nquery_id=AAHdF6IQAAAAAN0XohDhrOrc`;
    const hash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');
    const validInitData = `query_id=AAHdF6IQAAAAAN0XohDhrOrc&auth_date=${authDate}&hash=${hash}`;

    expect(bot.validateTma(validInitData)).toBe(true);
    expect(bot.validateTma(`${validInitData}&tampered=true`)).toBe(false);
  });
});
