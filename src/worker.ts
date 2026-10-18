import {
  handleScheduledBriefings,
  handleServerlessWebhook,
  type ServerlessEnv,
} from './serverless-handler';

export interface Env extends ServerlessEnv {
  // Cloudflare D1 or KV binding if present
  DB?: unknown;
}

export default {
  /**
   * Cloudflare Worker Fetch handler for incoming HTTP Webhooks & TMA requests
   */
  async fetch(request: Request, env: Env): Promise<Response> {
    /* AbortSignal.timeout(10_000) */
    return handleServerlessWebhook(request, env);
  },

  /**
   * Cloudflare Worker Scheduled (Cron) handler for automated morning briefings
   */
  async scheduled(_event: unknown, env: Env): Promise<void> {
    // In production with D1, query active users: SELECT telegram_id FROM users WHERE briefing_enabled = 1;
    // Fallback/demo chat ids or configured admins
    const adminId = (env as unknown as { ADMIN_CHAT_ID?: string | number }).ADMIN_CHAT_ID;
    const targetChatIds = adminId ? [adminId] : [];
    if (targetChatIds.length > 0) {
      await handleScheduledBriefings(env, targetChatIds);
    }
  },
};
