import {
  ApiClient,
  type BotClient,
  parseInitData,
  type Update,
  validateInitData,
} from '@tgwrapper/core';
import { createRatioBot } from './bot';
import { DEFAULT_SCHEDULE } from './config';
import { globalFloodLimiter, type TokenBucketLimiter } from './limiter';
import { globalPaymentIdempotency, type PaymentIdempotencyManager } from './payment-idempotency';
import type { CompletedTask } from './types';

export interface ServerlessEnv {
  BOT_TOKEN: string;
  BOT_SECRET_TOKEN?: string;
  WEBHOOK_SECRET?: string;
  client?: BotClient;
  apiClient?: ApiClient;
  floodLimiter?: TokenBucketLimiter;
  paymentIdempotency?: PaymentIdempotencyManager;
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
  if (
    url.pathname === '/health' ||
    url.pathname === '/healthz' ||
    url.pathname === '/api/health' ||
    url.pathname === '/api/healthz'
  ) {
    const correlationId =
      request.headers.get('x-correlation-id') || request.headers.get('x-request-id');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
    };
    if (correlationId) {
      headers['X-Correlation-ID'] = correlationId;
    }
    return new Response(
      JSON.stringify({ ok: true, status: 'healthy', runtime: 'telegram-serverless' }),
      {
        status: 200,
        headers,
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
    } catch (err) {
      console.warn('[Serverless-Payload-Error]', err);
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
    const paymentIdempotency = env.paymentIdempotency ?? globalPaymentIdempotency;
    const floodLimiter = env.floodLimiter ?? globalFloodLimiter;

    const updateObj = update as Record<string, unknown>;

    // 1. Webhook Update Deduplication
    if (typeof update.update_id === 'number') {
      if (!paymentIdempotency.claimUpdate(update.update_id)) {
        return new Response(JSON.stringify({ ok: true, action: 'duplicate_update_ignored' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // 2. Flood Control Rate Limiting (Token Bucket per chat/user)
    const senderId =
      update.message?.from?.id ??
      update.message?.chat?.id ??
      update.callback_query?.from?.id ??
      (updateObj.inline_query as { from?: { id?: number } })?.from?.id;

    if (senderId) {
      const limitResult = floodLimiter.consume(String(senderId));
      if (!limitResult.allowed) {
        return new Response(
          JSON.stringify({
            ok: false,
            error: 'Too Many Requests (Flood Control)',
            retryAfterMs: limitResult.retryAfterMs,
          }),
          {
            status: 429,
            headers: {
              'Content-Type': 'application/json',
              'Retry-After': String(Math.ceil(limitResult.retryAfterMs / 1000)),
            },
          },
        );
      }
    }

    // Handle pre_checkout_query for Stars
    if (updateObj.pre_checkout_query) {
      const pcq = updateObj.pre_checkout_query as { id: string };
      const clientAny = bot.client as unknown as {
        callApiUnsafe?: (m: string, p: unknown) => Promise<unknown>;
      };
      if (typeof clientAny.callApiUnsafe === 'function') {
        try {
          await clientAny.callApiUnsafe('answerPreCheckoutQuery', {
            pre_checkout_query_id: pcq.id,
            ok: true,
          });
        } catch (err) {
          console.warn('[PreCheckout-Failed]', err);
        }
      }
      return new Response(JSON.stringify({ ok: true, action: 'pre_checkout_query_handled' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Handle inline_query
    if (updateObj.inline_query) {
      const iq = updateObj.inline_query as { id: string; query?: string };
      const clientAny = bot.client as unknown as {
        callApiUnsafe?: (m: string, p: unknown) => Promise<unknown>;
      };
      if (typeof clientAny.callApiUnsafe === 'function') {
        try {
          const results = [
            {
              type: 'article',
              id: 'ratio-analytics',
              title: '⚖️ Ratio & Schedule: Баланс дня',
              description: 'Узнать текущее соотношение работы и отдыха (Work/Rest)',
              input_message_content: {
                message_text: `⚖️ <b>Ratio & Schedule Status</b>\nТекущий баланс: <b>2.0:1 (Гармония)</b>\nЗапланировано слотов: ${DEFAULT_SCHEDULE.length}\nЗапустите Mini App для настройки расписания!`,
                parse_mode: 'HTML',
              },
            },
          ];
          await clientAny.callApiUnsafe('answerInlineQuery', {
            inline_query_id: iq.id,
            results,
            cache_time: 10,
          });
        } catch (err) {
          console.warn('[InlineQuery-Failed]', err);
        }
      }
      return new Response(JSON.stringify({ ok: true, action: 'inline_query_handled' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Handle inline callback queries
    if (update.callback_query) {
      const cq = update.callback_query;
      const data = String(cq.data || '');
      const resultText = await bot.handleCallbackQuery(data);

      try {
        await bot.client.answerCallbackQuery(cq.id, { text: resultText });
      } catch (err) {
        console.warn('[AnswerCallbackQuery-Failed]', err);
      }

      if (cq.message?.chat?.id) {
        await bot.client.sendMessage(cq.message.chat.id, resultText);
      }

      return new Response(JSON.stringify({ ok: true, action: 'callback_query_handled' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Handle successful_payment with Idempotency
    const msgObj = update.message as Record<string, unknown> | undefined;
    if (msgObj?.successful_payment && update.message?.chat?.id) {
      const sp = msgObj.successful_payment as {
        telegram_payment_charge_id?: string;
        provider_payment_charge_id?: string;
      };
      const chargeId = sp.telegram_payment_charge_id || sp.provider_payment_charge_id || '';
      const userId = update.message.from?.id;

      if (chargeId && !paymentIdempotency.claimPayment(chargeId, userId)) {
        return new Response(
          JSON.stringify({
            ok: true,
            action: 'payment_already_handled',
            chargeId,
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          },
        );
      }

      await bot.client.sendMessage(
        update.message.chat.id,
        '🌟 <b>Подписка PRO активирована!</b>\nСпасибо за оплату через Telegram Stars! Теперь вам доступны умные напоминания и неограниченный анализ.',
      );
      return new Response(JSON.stringify({ ok: true, action: 'payment_handled' }), {
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
    env.apiClient ??
    (env.client ? (env.client as unknown as ApiClient) : new ApiClient({ token: env.BOT_TOKEN }));
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
    } catch (err) {
      console.warn('[Briefing-Dispatch-Failed]', err);
      failed++;
    }
  }

  return { dispatched, failed };
}
