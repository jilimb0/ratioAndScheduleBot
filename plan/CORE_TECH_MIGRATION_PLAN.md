# План миграции ratioAndScheduleBot на кор-технологии (@tgwrapper & @ui-construction-library)

> **Проект:** `lifestyle-productivity/ratioAndScheduleBot`  
> **Роль в экосистеме:** Бот баланса работы и отдыха (Work/Rest Ratio) с Telegram Mini App и оплатой Telegram Stars  
> **Приоритет миграции:** 🎯 **Tier 3 (Средний)**  

---

## 1. Текущий технологический срез (As-Is)

### Telegram & TMA:
* **Что используется сейчас:** Бот написан на **Python** (библиотека `python-telegram-bot` + SQLite, 8 модулей кода).
* **Связь с `@tgwrapper`:** В рамках этапа синергии создан модуль `tma_validator.py`, который строго воспроизводит спецификацию HMAC-SHA256 криптографии `@tgwrapper/core/tma` на Python.
* **Несоответствие целевому стандарту:** Сам бот работает не на фреймворке `@tgwrapper` (TypeScript/Node), а в отдельной среде Python.

### Web & UI:
* **Что используется сейчас:** `webapp/index.html` — легковесный ванильный HTML5/CSS/JS файл для редактирования расписания в Telegram Mini App.
* **Статус `@ui-construction-library`:** ❌ Не используется (чистый ванильный CSS).

---

## 2. Целевая архитектура (To-Be)

1. **Портирование бота на TypeScript & `@tgwrapper/core@0.20.1`:**
   - Для выполнения глобального правила экосистемы (*«Все боты на TGWrapper»*) бот переписывается на TypeScript с использованием `@tgwrapper/core`. Небольшой объем кодовой базы (8 питоновских файлов) позволяет перенести логику за 1-2 дня.
2. **Перевод `webapp` на React 19 + `@ui-construction-library/core@0.9.0`:**
   - Замена ванильного `index.html` на современный Vite/React Mini App.
   - Использование компонентов `Slider` (баланс работы/отдыха), `Card` (слоты дня), `Badge` (коэффициент Ratio) и `Button` из `@ui-construction-library`.

---

## 3. Пошаговый план перехода

### Шаг 1. Инициализация TypeScript-проекта бота
- [x] Добавить `package.json` и настроить pnpm + Biome:
  ```json
  {
    "name": "ratio-and-schedule-bot",
    "dependencies": {
      "@tgwrapper/core": "^0.20.1"
    }
  }
  ```
- [x] Перенос обработчиков команд (`/start`, `/ratio`, `/schedule`, `/settings`, `/stars_pay`) из `handlers.py` в TypeScript роутер `@tgwrapper`.
- [x] Перенос логики расчета коэффициента из `engine.py` (реализовано в `src/engine.ts`).

### Шаг 2. Разработка TMA на `@ui-construction-library`
- [x] Настроить Vite + React 19 в проекте.
- [x] Подключить `@ui-construction-library/core` и `@ui-construction-library/icons`.
- [x] Собрать экран конфигуратора:
  - Ползунок «Часы работы vs Отдыха»: `Slider`.
  - Индикатор коэффициента Ratio: `Badge` + `Progress`.
  - Модалка покупки Pro-тарифа за Telegram Stars: `Card` + `Button` (default).

### Шаг 3. Верификация
- [x] Настройка Biome линтера (`pnpm check:ci`).
- [x] Написание тестов на Vitest (11 тестов engine & bot + 31 тест pytest).
- [x] Запуск CI/CD пайплайна (чистый билд Vite, 0 lint errors, 0 type errors).

---

## 4. Оценка трудоёмкости
* **Telegram-слой:** 1.5 дня (портирование логики с Python на TS + @tgwrapper).
* **UI-слой:** 1 день (создание React TMA на @ui-construction-library).
* **Суммарно:** 2.5 рабочих дня.
