# План SEO и защиты индексации: ratioAndScheduleBot

> **Текущий SEO-скор:** 20 / 100 (⚪ Внутренний WebApp инструмент)  
> **Дата аудита:** Октябрь 2026  
> **Роль в экосистеме:** Telegram-бот и визуальный таймлайн баланса работы и отдыха (Work/Rest Ratio)  
> **Стек:** Python + HTML5/CSS WebApp  
> **Глобальный план:** [GLOBAL_SEO_OPTIMIZATION_PLAN.md](file:///Users/jilimbo/Documents/Personal/GLOBAL_SEO_OPTIMIZATION_PLAN.md)

---

## 1. Специфика продукта и стратегия SEO

* **Природа продукта:** `webapp/index.html` — это интерфейс таймлайна, открываемый ботом через `tg.openLink` или WebApp кнопку в Telegram.
* **Текущая проблема:** Страница не имеет директивы `noindex`. Попадание этой технической страницы в публичный поисковый индекс Google бесполезно, так как без данных Telegram-пользователя она отображает пустое расписание.
* **Решение:** Проставить `noindex, nofollow`.

---

## 2. Пошаговый план внедрения (Action Plan)

- [x] **Шаг 1: Добавить метатег `noindex` в `webapp/index.html`**
  - Добавлен метатег `<meta name="robots" content="noindex, nofollow">`.
- [x] **Шаг 2: Создать `webapp/robots.txt`**
  - Создан файл с директивой `Disallow: /`.
