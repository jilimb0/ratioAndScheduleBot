import crypto from 'node:crypto';
import { MockBotClient } from '@tgwrapper/core';
import { describe, expect, it } from 'vitest';
import {
  handleScheduledBriefings,
  handleServerlessWebhook,
  type ServerlessEnv,
} from '../src/serverless-handler';

describe('Serverless Handler for ratioAndScheduleBot', () => {
  const mockClient = new MockBotClient();

  const env: ServerlessEnv = {
    BOT_TOKEN: '123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ',
    BOT_SECRET_TOKEN: 'super-secret-token-123',
    client: mockClient,
  };

  it('responds with 200 on /health', async () => {
    const req = new Request('https://worker.test/health', { method: 'GET' });
    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.status).toBe('healthy');
  });

  it('rejects invalid secret tokens with 401', async () => {
    const req = new Request('https://worker.test/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-telegram-bot-api-secret-token': 'wrong-token',
      },
      body: JSON.stringify({ update_id: 1 }),
    });

    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(401);
    const data = await res.json();
    expect(data.error).toContain('Unauthorized');
  });

  it('processes incoming Telegram message with valid secret token', async () => {
    const req = new Request('https://worker.test/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-telegram-bot-api-secret-token': 'super-secret-token-123',
      },
      body: JSON.stringify({
        update_id: 101,
        message: {
          message_id: 1,
          date: Math.floor(Date.now() / 1000),
          chat: { id: 98765, type: 'private' },
          text: '/start',
        },
      }),
    });

    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    if (!data.ok) console.log('DEBUG DATA ERROR:', data);
    expect(data.ok).toBe(true);
    expect(data.action).toBe('message_handled');
  });

  it('processes incoming callback_query and answers it', async () => {
    const req = new Request('https://worker.test/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-telegram-bot-api-secret-token': 'super-secret-token-123',
      },
      body: JSON.stringify({
        update_id: 102,
        callback_query: {
          id: 'cq_999',
          from: { id: 98765, is_bot: false, first_name: 'Alex' },
          chat_instance: 'test_inst',
          data: 'settz_Europe/Warsaw',
          message: {
            message_id: 2,
            date: Math.floor(Date.now() / 1000),
            chat: { id: 98765, type: 'private' },
          },
        },
      }),
    });

    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.action).toBe('callback_query_handled');
  });

  it('validates TMA initData on /api/validate endpoint', async () => {
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(env.BOT_TOKEN).digest();
    const authDate = Math.floor(Date.now() / 1000).toString();
    const dataCheckString = `auth_date=${authDate}\nquery_id=AAHdF6IQAAAAAN0XohDhrOrc`;
    const hash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');
    const validInitData = `query_id=AAHdF6IQAAAAAN0XohDhrOrc&auth_date=${authDate}&hash=${hash}`;

    const validReq = new Request('https://worker.test/api/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData: validInitData }),
    });

    const res = await handleServerlessWebhook(validReq, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.valid).toBe(true);
  });

  it('dispatches scheduled morning briefings to target users', async () => {
    const result = await handleScheduledBriefings(env, [12345, 67890]);
    expect(result.dispatched + result.failed).toBe(2);
  });

  it('handles pre_checkout_query update', async () => {
    const req = new Request('https://worker.test/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-telegram-bot-api-secret-token': 'super-secret-token-123',
      },
      body: JSON.stringify({
        update_id: 103,
        pre_checkout_query: { id: 'pcq_123', from: { id: 1 }, currency: 'XTR', total_amount: 50 },
      }),
    });

    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.action).toBe('pre_checkout_query_handled');
  });

  it('handles inline_query update', async () => {
    const req = new Request('https://worker.test/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-telegram-bot-api-secret-token': 'super-secret-token-123',
      },
      body: JSON.stringify({
        update_id: 104,
        inline_query: { id: 'iq_123', query: 'schedule' },
      }),
    });

    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.action).toBe('inline_query_handled');
  });

  it('handles successful_payment message update', async () => {
    const req = new Request('https://worker.test/webhook', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-telegram-bot-api-secret-token': 'super-secret-token-123',
      },
      body: JSON.stringify({
        update_id: 105,
        message: {
          message_id: 5,
          chat: { id: 98765 },
          successful_payment: { currency: 'XTR', total_amount: 50 },
        },
      }),
    });

    const res = await handleServerlessWebhook(req, env);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.action).toBe('payment_handled');
  });
});
