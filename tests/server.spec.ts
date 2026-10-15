import { describe, expect, it } from 'vitest';
import { getContentType, loadConfig, resolveStaticFile } from '../src/server';

describe('server helpers', () => {
  it('loads config with defaults', () => {
    const config = loadConfig({ BOT_TOKEN: 'test-token' } as NodeJS.ProcessEnv);
    expect(config.botToken).toBe('test-token');
    expect(config.port).toBe(8000);
    expect(config.host).toBe('0.0.0.0');
    expect(config.useWebhook).toBe(false);
  });

  it('parses webhook mode', () => {
    const config = loadConfig({
      BOT_TOKEN: 't',
      USE_WEBHOOK: 'true',
      WEBHOOK_URL: 'https://example.com/',
      PORT: '9000',
    } as NodeJS.ProcessEnv);
    expect(config.useWebhook).toBe(true);
    expect(config.webhookUrl).toBe('https://example.com');
    expect(config.port).toBe(9000);
  });

  it('throws without BOT_TOKEN', () => {
    expect(() => loadConfig({} as NodeJS.ProcessEnv)).toThrow('BOT_TOKEN is required');
  });

  it('throws on invalid PORT', () => {
    expect(() => loadConfig({ BOT_TOKEN: 't', PORT: 'abc' } as NodeJS.ProcessEnv)).toThrow(
      'Invalid PORT',
    );
  });

  it('maps content types', () => {
    expect(getContentType('index.html')).toBe('text/html; charset=utf-8');
    expect(getContentType('app.js')).toBe('text/javascript; charset=utf-8');
    expect(getContentType('style.css')).toBe('text/css; charset=utf-8');
    expect(getContentType('icon.svg')).toBe('image/svg+xml');
    expect(getContentType('file.unknown')).toBe('application/octet-stream');
  });

  it('resolves static files and neutralizes traversal', () => {
    expect(resolveStaticFile('/srv/dist', '/assets/app.js')).toBe('/srv/dist/assets/app.js');
    expect(resolveStaticFile('/srv/dist', '/')).toBe('/srv/dist');
    // normalize() collapses ".." before join, so traversal stays inside staticDir
    expect(resolveStaticFile('/srv/dist', '/../etc/passwd')).toBe('/srv/dist/etc/passwd');
    expect(resolveStaticFile('/srv/dist', '/a/../../etc/passwd')).toBe('/srv/dist/etc/passwd');
  });
});
