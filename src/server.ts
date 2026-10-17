import { randomUUID } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { dirname, extname, join, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { handleServerlessWebhook, type ServerlessEnv } from './serverless-handler';

const TELEGRAM_API = 'https://api.telegram.org';
const MAX_BODY_BYTES = 1024 * 1024;

export interface ServerConfig {
  botToken: string;
  port: number;
  host: string;
  useWebhook: boolean;
  webhookUrl?: string;
  secretToken?: string;
  staticDir: string;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): ServerConfig {
  const botToken = (env.BOT_TOKEN ?? '').trim();
  if (!botToken) {
    throw new Error('BOT_TOKEN is required');
  }
  const port = Number.parseInt(env.PORT ?? '8000', 10);
  if (!Number.isSafeInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`Invalid PORT: ${env.PORT}`);
  }
  const webhookUrl = (env.WEBHOOK_URL ?? '').trim().replace(/\/$/, '') || undefined;
  return {
    botToken,
    port,
    host: (env.HOST ?? '0.0.0.0').trim() || '0.0.0.0',
    useWebhook: (env.USE_WEBHOOK ?? 'false').trim().toLowerCase() === 'true',
    webhookUrl,
    secretToken: (env.BOT_SECRET_TOKEN ?? env.WEBHOOK_SECRET ?? '').trim() || undefined,
    staticDir:
      (env.STATIC_DIR ?? '').trim() || join(dirname(fileURLToPath(import.meta.url)), '..', 'dist'),
  };
}

const MIME_TYPES: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json',
  '.txt': 'text/plain; charset=utf-8',
};

export function getContentType(filePath: string): string {
  return MIME_TYPES[extname(filePath).toLowerCase()] ?? 'application/octet-stream';
}

/** Resolve a URL path to a file inside staticDir. Returns null on traversal attempts. */
export function resolveStaticFile(staticDir: string, urlPath: string): string | null {
  const pathname = normalize(urlPath.split('?')[0]);
  const relative = pathname.replace(/^\/+/, '');
  const resolved = join(staticDir, relative);
  if (resolved !== staticDir && !resolved.startsWith(staticDir + sep)) {
    return null;
  }
  return resolved;
}

async function readBody(req: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk as Uint8Array);
    size += buf.length;
    if (size > MAX_BODY_BYTES) {
      throw new Error('Request body too large');
    }
    chunks.push(buf);
  }
  return Buffer.concat(chunks);
}

function toWebRequest(req: IncomingMessage, body: Buffer): Request {
  const headers = new Headers();
  for (const [name, value] of Object.entries(req.headers)) {
    if (value === undefined) continue;
    if (Array.isArray(value)) {
      for (const v of value) headers.append(name, v);
    } else {
      headers.set(name, value);
    }
  }
  headers.delete('host');
  headers.delete('content-length');
  const init: RequestInit = { method: req.method ?? 'GET', headers };
  if (body.length > 0 && req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = body.buffer.slice(
      body.byteOffset,
      body.byteOffset + body.byteLength,
    ) as ArrayBuffer;
    if (!headers.has('content-type')) {
      headers.set('content-type', 'application/octet-stream');
    }
  }
  return new Request(`http://localhost${req.url ?? '/'}`, init);
}

async function sendWebResponse(webRes: Response, res: ServerResponse): Promise<void> {
  res.statusCode = webRes.status;
  webRes.headers.forEach((value, name) => {
    res.setHeader(name, value);
  });
  const bytes = new Uint8Array(await webRes.arrayBuffer());
  res.end(Buffer.from(bytes));
}

async function telegramCall(
  botToken: string,
  method: string,
  params: Record<string, unknown>,
): Promise<{ ok: boolean; description?: string }> {
  const res = await fetch(`${TELEGRAM_API}/bot${botToken}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return (await res.json()) as { ok: boolean; description?: string };
}

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

export function createEnv(config: ServerConfig): ServerlessEnv {
  return {
    BOT_TOKEN: config.botToken,
    BOT_SECRET_TOKEN: config.secretToken,
  };
}

/** Long-polling loop (USE_WEBHOOK=false). Feeds updates through the webhook handler. */
export async function runPolling(
  config: ServerConfig,
  signal: AbortSignal,
  onUpdate?: (action: unknown) => void,
): Promise<void> {
  const drop = await telegramCall(config.botToken, 'deleteWebhook', {
    drop_pending_updates: true,
  }).catch((err) => ({ ok: false as const, description: String(err) }));
  if (!drop.ok) {
    console.error(`[polling] deleteWebhook failed, continuing anyway: ${drop.description}`);
  }
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (config.secretToken) {
    headers['x-telegram-bot-api-secret-token'] = config.secretToken;
  }
  let offset = 0;
  let failures = 0;
  while (!signal.aborted) {
    try {
      const res = await fetch(`${TELEGRAM_API}/bot${config.botToken}/getUpdates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offset, timeout: 30 }),
        signal,
      });
      const data = (await res.json()) as {
        ok: boolean;
        result?: { update_id: number }[];
        description?: string;
      };
      if (!data.ok) {
        throw new Error(`getUpdates failed: ${data.description ?? 'unknown error'}`);
      }
      failures = 0;
      for (const update of data.result ?? []) {
        offset = update.update_id + 1;
        const webReq = new Request('http://localhost/webhook', {
          method: 'POST',
          headers,
          body: JSON.stringify(update),
        });
        const webRes = await handleServerlessWebhook(webReq, createEnv(config));
        onUpdate?.(await webRes.json().catch(() => null));
      }
    } catch (err) {
      if (signal.aborted) break;
      failures += 1;
      console.error(`[polling] error (${failures}):`, err instanceof Error ? err.message : err);
      await sleep(Math.min(1000 * 2 ** Math.min(failures, 5), 30000));
    }
  }
}

export async function registerWebhook(config: ServerConfig): Promise<void> {
  if (!config.webhookUrl) {
    throw new Error('WEBHOOK_URL is required when USE_WEBHOOK=true');
  }
  const params: Record<string, unknown> = { url: `${config.webhookUrl}/webhook` };
  if (config.secretToken) {
    params.secret_token = config.secretToken;
  }
  const result = await telegramCall(config.botToken, 'setWebhook', params);
  if (!result.ok) {
    throw new Error(`setWebhook failed: ${result.description ?? 'unknown error'}`);
  }
  console.log(`[webhook] registered: ${params.url}`);
}

export function createHttpServer(config: ServerConfig) {
  const env = createEnv(config);
  return createServer(async (req: IncomingMessage, res: ServerResponse) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const rawCorrelationId = req.headers['x-correlation-id'] || req.headers['x-request-id'];
      const correlationId = Array.isArray(rawCorrelationId)
        ? rawCorrelationId[0]
        : rawCorrelationId || randomUUID();
      res.setHeader('X-Correlation-ID', correlationId);
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('X-Frame-Options', 'DENY');
      res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');

      if (
        url.pathname === '/health' ||
        url.pathname === '/healthz' ||
        url.pathname === '/api/health' ||
        url.pathname === '/api/healthz' ||
        url.pathname === '/webhook' ||
        (url.pathname.startsWith('/api/') && req.method === 'POST')
      ) {
        const webRes = await handleServerlessWebhook(toWebRequest(req, await readBody(req)), env);
        await sendWebResponse(webRes, res);
        return;
      }

      let filePath = resolveStaticFile(config.staticDir, url.pathname);
      if (filePath === null) {
        res.statusCode = 403;
        res.end('Forbidden');
        return;
      }
      try {
        const fileStat = await stat(filePath);
        if (fileStat.isDirectory()) {
          filePath = join(filePath, 'index.html');
          await stat(filePath);
        }
      } catch {
        filePath = join(config.staticDir, 'index.html');
      }
      try {
        const data = await readFile(filePath);
        res.statusCode = 200;
        res.setHeader('Content-Type', getContentType(filePath));
        res.end(data);
      } catch {
        res.statusCode = 404;
        res.end('Not found');
      }
    } catch (err) {
      console.error('[http] request failed:', err instanceof Error ? err.message : err);
      if (!res.headersSent) {
        res.statusCode = 500;
        res.end('Internal error');
      }
    }
  });
}

async function main(): Promise<void> {
  const config = loadConfig();
  if (config.useWebhook) {
    try {
      await registerWebhook(config);
    } catch (err) {
      console.error('[webhook] registration failed, serving anyway:', err);
    }
  }
  const server = createHttpServer(config);
  const aborter = new AbortController();
  let polling: Promise<void> | null = null;
  if (!config.useWebhook) {
    polling = runPolling(config, aborter.signal);
  }

  const shutdown = (sig: string): void => {
    console.log(`[${sig}] shutting down...`);
    aborter.abort();
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 5000).unref();
  };
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));

  server.listen(config.port, config.host, () => {
    console.log(
      `[ready] listening on ${config.host}:${config.port} (mode: ${config.useWebhook ? 'webhook' : 'polling'})`,
    );
  });
  await polling;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error('[fatal]', err instanceof Error ? err.message : err);
    process.exit(1);
  });
}
