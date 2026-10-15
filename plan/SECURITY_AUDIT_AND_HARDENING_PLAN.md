# План аудита и устранения уязвимостей безопасности: ratioAndScheduleBot

> **Текущий скор безопасности:** 95 / 100 (🟢 Низкий уровень риска)  
> **Дата аудита:** Октябрь 2026  
> **Статус:** HTTP-сервер переведен на aiohttp, платежи Stars защищены от race conditions, serverless-слой на @tgwrapper готов  

---

## 1. Обнаруженные уязвимости

### [P2] Самописный HTTP-сервер на «сырых» TCP-сокетах (Уязвимость к DoS / Slowloris) [УСТРАНЕНО]
* **Файл:** `main.py`
* **Механика проблемы:**
  Health check и раздача WebApp были реализованы через прямой `asyncio.start_server` с ручным парсингом HTTP-строк без лимитов и таймаутов чтения.
* **Решение:** Ручной TCP-сокет заменен на стандартизированный `aiohttp.web.Application` с ограничением размера тела (`client_max_size=1MB`), встроенной защитой от Slowloris и корректной установкой security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`).

### [P2] Проверка валидности платежей Telegram Stars [УСТРАНЕНО]
* **Файл:** `handlers.py`, `database.py`
* **Механика проблемы:**
  Отсутствие уникального ограничения на `telegram_payment_charge_id` при обработке платежей звездами создавало риск повторного начисления подписки при race conditions.
* **Решение:** Добавлен уникальный индекс `idx_payments_tg_charge` в SQLite и проверка успешности сохранения платежа перед начислением доступа PRO.

---

## 2. Пошаговый план устранения (Hardening Plan)

- [x] **Шаг 1 (P2): Замена самописного TCP-сервера на стандартизированный фреймворк**
  - Заменен `asyncio.start_server` на `aiohttp.web.Application`.
  - Установлены лимиты размера и security headers.

- [x] **Шаг 2 (P2): Идемпотентность Telegram Stars**
  - Создан уникальный частичный индекс `idx_payments_tg_charge` на `telegram_payment_charge_id`.
  - Идемпотентность в `record_payment` и `successful_payment_handler`, добавлены тесты.

- [x] **Шаг 3 (P3): План миграции на TypeScript (`@tgwrapper`)**
  - Реализован serverless-обработчик на `@tgwrapper/core` v0.20.1 с тестами (`tests/serverless-handler.spec.ts`), покрывающий вебхуки и валидацию TMA.
