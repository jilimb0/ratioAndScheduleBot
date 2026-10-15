import {
  ApiClient,
  type BotClient,
  parseInitData,
  type Update,
  validateInitData,
} from '@tgwrapper/core';
import { createRatioBot } from './bot';
import { DEFAULT_SCHEDULE } from './config';
import type { CompletedTask } from './types';

export interface ServerlessEnv {
  BOT_TOKEN: string;
  BOT_SECRET_TOKEN?: string;
  WEBHOOK_SECRET?: string;
  client?: BotClient;
  apiClient?: ApiClient;
}

export interface WebhookResult {
  ok: boolean;
  handled?: boolean;
  action?: string;
  error?: string;
}

/**
 * Universal Serverless Handler for Telegram Webhook and TMA API.
 * Works seamlessly across Cloudflare Workers, Vercel Edge, AWS Lambda, and Node.js Fetch.
 */
export async function handleServerlessWebhook(
  request: Request,
  env: ServerlessEnv,
  userTasks: CompletedTask[] = [],
): Promise<Response> {
  const url = new URL(request.url);

  // 1. Health check
  if (url.pathname === '/health' || url.pathname === '/api/health') {
    return new Response(
      JSON.stringify({ ok: true, status: 'healthy', runtime: 'telegram-serverless' }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  }

  // 2. TMA InitData Validation Endpoint
  if (url.pathname === '/api/validate' || url.pathname === '/api/tma/validate') {
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ ok: false, error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    try {
      const body = (await request.json()) as { initData?: string };
      const initData = body.initData || '';
      const isValid = validateInitData(initData, env.BOT_TOKEN);
      const parsed = isValid ? parseInitData(initData) : null;

      return new Response(
        JSON.stringify({ ok: true, valid: isValid, user: parsed?.user ?? null }),
        {
          status: isValid ? 200 : 401,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    } catch {
      return new Response(JSON.stringify({ ok: false, error: 'Invalid payload' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // 3. Telegram Webhook Processing
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ ok: false, error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Secret Token Authentication
  const expectedSecret = env.BOT_SECRET_TOKEN || env.WEBHOOK_SECRET;
  if (expectedSecret) {
    const receivedSecret =
      request.headers.get('x-telegram-bot-api-secret-token') ||
      request.headers.get('x-telegram-bot-secret-token');

    if (receivedSecret !== expectedSecret) {
      return new Response(
        JSON.stringify({ ok: false, error: 'Unauthorized: invalid secret token' }),
        {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        },
      );
    }
  }

  try {
    const update = (await request.json()) as Update;
    const bot = createRatioBot({ token: env.BOT_TOKEN, client: env.client });

    // Handle inline callback queries
    if (update.callback_query) {
      const cq = update.callback_query;
      const data = String(cq.data || '');
      const resultText = await bot.handleCallbackQuery(data);

      try {
        await bot.client.answerCallbackQuery(cq.id, { text: resultText });
      } catch {
        // Non-blocking if Telegram answer fails
      }

      if (cq.message?.chat?.id) {
        await bot.client.sendMessage(cq.message.chat.id, resultText);
      }

      return new Response(JSON.stringify({ ok: true, action: 'callback_query_handled' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Handle normal text messages
    if (update.message?.chat?.id && update.message.text) {
      const chatId = update.message.chat.id;
      const text = String(update.message.text);

      await bot.handleMessage(chatId, text, userTasks);

      return new Response(JSON.stringify({ ok: true, action: 'message_handled' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({ ok: true, action: 'ignored' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    return new Response(JSON.stringify({ ok: false, error: message }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Serverless Scheduled Cron Handler for Morning Briefings.
 * Replaces legacy APScheduler daemon with zero-idle-cost Cloudflare / Vercel Cron.
 */
export async function handleScheduledBriefings(
  env: ServerlessEnv,
  targetChatIds: (string | number)[],
): Promise<{ dispatched: number; failed: number }> {
  const client =
    env.apiClient ?? (env.client ? (env.client as any) : new ApiClient({ token: env.BOT_TOKEN }));
  let dispatched = 0;
  let failed = 0;

  const briefingText =
    `🌅 <b>Утренний брифинг продуктивности</b>\n\n` +
    `Сегодня запланировано активностей: <b>${DEFAULT_SCHEDULE.length}</b>.\n` +
    `Соблюдайте баланс работы и восстановления: <i>Ratio 3:1</i>!\n\n` +
    `Для проверки расписания введите /schedule или откройте WebApp ✨`;

  for (const chatId of targetChatIds) {
    try {
      await client.sendMessage(chatId, briefingText, { parse_mode: 'HTML' });
      dispatched++;
    } catch {
      failed++;
    }
  }

  return { dispatched, failed };
}
