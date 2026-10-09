import json
import logging
import random
from datetime import date, datetime, timedelta

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ContextTypes

from config import (
    CATEGORIES,
    COMMON_TIMEZONES,
    MESSAGES,
    PRO_PRICE_STARS,
    SCHEDULE,
    WEBAPP_URL,
)
from database import (
    activate_user_pro,
    add_user_task,
    delete_user_task,
    get_completion_rate,
    get_ratio_analytics,
    get_today_tasks_status,
    get_user_schedule,
    get_user_stats,
    get_user_streak,
    get_user_timezone,
    is_task_completed_today,
    is_user_pro,
    mark_task_completed,
    record_payment,
    register_user,
    set_user_timezone,
    skip_task,
    snooze_task,
    update_user_activity,
)

logger = logging.getLogger(__name__)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает основную клавиатуру с кнопками быстрого доступа."""
    keyboard = [
        [KeyboardButton("📊 Статус"), KeyboardButton("⚖️ Баланс (Ratio)")],
        [KeyboardButton("🗓 Расписание"), KeyboardButton("📈 Отчёт")],
        [KeyboardButton("🌅 Брифинг"), KeyboardButton("⭐ Pro (Stars)")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("ℹ️ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_timezone_inline_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки выбора часового пояса."""
    buttons = []
    row = []
    for tz_code, label in COMMON_TIMEZONES:
        row.append(InlineKeyboardButton(label, callback_data=f"settz_{tz_code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start и кнопки 'Помощь'."""
    user = update.effective_user
    if not user:
        return
    try:
        register_user(user_id=user.id, username=user.username, first_name=user.first_name)
        logger.info(f"Пользователь {user.id} ({user.username}) запустил/перезапустил бота.")

        await update.message.reply_text(
            MESSAGES.get("start", "Добро пожаловать!"),
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка в start_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Произошла ошибка при запуске. Попробуйте позже.")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус выполнения задач на сегодня и стрик."""
    user = update.effective_user
    if not user or not update.message:
        return
    try:
        update_user_activity(user.id)
        tasks_status = get_today_tasks_status(user.id)
        user_sched = get_user_schedule(user.id)
        sched_map = {item["task_key"]: item for item in user_sched}

        streak = get_user_streak(user.id)
        streak_line = f"🔥 Серия дней (Streak): **{streak} дн.**\n" if streak > 0 else ""

        if not tasks_status:
            await update.message.reply_text(
                f"{streak_line}📅 На сегодня задач нет. Добавьте задачу через /addtask!"
            )
            return

        status_lines = [f"{streak_line}📊 **Статус задач на сегодня:**"]
        completed_count = 0

        for task_key, is_completed in tasks_status.items():
            conf = sched_map.get(task_key) or SCHEDULE.get(task_key, {})
            title = conf.get("title") or conf.get("button_text", task_key).replace(" ✅", "")
            time_str = conf.get("time_str") or (
                conf.get("time").strftime("%H:%M") if conf.get("time") else "--:--"
            )
            cat_emoji = CATEGORIES.get(conf.get("category", ""), {}).get("emoji", "📌")

            if is_completed:
                completed_count += 1
                status_icon = "✅"
            else:
                status_icon = "⏳"

            status_lines.append(f"{status_icon} `{time_str}` {cat_emoji} {title}")

        completion_rate = get_completion_rate(user.id, days=7)
        status_lines.append(
            f"\n🎯 Выполнено сегодня: **{completed_count}/{len(tasks_status)}**"
            f"\n📈 Эффективность за неделю: **{completion_rate:.1f}%**"
        )

        await update.message.reply_text("\n".join(status_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка в status_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось получить статус. Попробуйте снова.")


async def ratio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Аналитика соотношения работы и отдыха за неделю в виде инфографики (Ratio Engine)."""
    user = update.effective_user
    if not user or not update.message:
        return
    try:
        update_user_activity(user.id)
        analytics = get_ratio_analytics(user.id, days=7)

        hours_total = analytics["total_hours"]
        tasks_total = analytics["total_tasks"]
        lines = [
            "⚖️ **Аналитика баланса времени (7 дней)**",
            f"Всего выполнено: **{tasks_total} задач** ({hours_total} ч.)\n",
            f"💼 Продуктивность (Работа/Учеба): **{round(analytics['work_minutes'] / 60, 1)} ч.**",
            f"🎮 Восстановление (Отдых/Спорт): **{round(analytics['rest_minutes'] / 60, 1)} ч.**",
            f"⚡ Соотношение Work / Rest: **{analytics['work_to_rest_ratio']} : 1**",
            f"🏆 Индекс жизненного баланса: **{analytics['balance_score']} / 100**\n",
            "📊 **Распределение по сферам жизни:**",
        ]

        if analytics["visual_bars"]:
            lines.extend(analytics["visual_bars"])
        else:
            lines.append("Нет данных за неделю. Отмечайте задачи для сбора инфографики!")

        lines.append(f"\n💡 _{analytics['recommendation']}_")

        keyboard_buttons = []
        keyboard_buttons.append(
            [InlineKeyboardButton("🚀 Поделиться карточкой", callback_data="share_card")]
        )
        if WEBAPP_URL:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        "📱 Интерактивный таймлайн", web_app=WebAppInfo(url=WEBAPP_URL)
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown", reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в ratio_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось сгенерировать аналитику баланса.")


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает отчёт о выполненных задачах за последнюю неделю по дням."""
    user = update.effective_user
    if not user or not update.message:
        return
    try:
        update_user_activity(user.id)
        stats = get_user_stats(user.id, days=7)

        if not stats:
            await update.message.reply_text("📊 За последние 7 дней данных для отчёта нет.")
            return

        report_lines = [MESSAGES.get("report_header", "Отчёт за 7 дней:")]
        sorted_dates = sorted(stats.keys(), reverse=True)

        for date_str in sorted_dates:
            tasks = stats[date_str]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            day_label = ""
            if date_obj == date.today():
                day_label = " (сегодня)"
            elif date_obj == date.today() - timedelta(days=1):
                day_label = " (вчера)"

            report_lines.append(f"\n📅 {date_obj.strftime('%d.%m.%Y')}{day_label}:")
            for task_item in tasks:
                if isinstance(task_item, dict):
                    t_name = task_item.get("task_name", "Задача")
                else:
                    t_name = str(task_item)
                report_lines.append(f"  ✅ {t_name}")

        completion_rate = get_completion_rate(user.id, days=7)
        report_lines.append(f"\n\n📊 Общая эффективность: {completion_rate:.1f}%")

        await update.message.reply_text("\n".join(report_lines))
    except Exception as e:
        logger.error(f"Ошибка в report_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось создать отчёт.")


async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает персональное расписание задач пользователя."""
    user = update.effective_user
    if not user or not update.message:
        return
    try:
        update_user_activity(user.id)
        user_tasks = get_user_schedule(user.id)

        schedule_lines = [MESSAGES.get("schedule_header", "Ваше расписание:")]

        if user_tasks:
            for task in user_tasks:
                time_str = task["time_str"]
                title = task["title"]
                is_completed = is_task_completed_today(user.id, task["task_key"])
                status_icon = "✅" if is_completed else "⏰"
                cat_emoji = CATEGORIES.get(task.get("category", ""), {}).get("emoji", "📌")
                dur = task.get("duration_minutes", 30)
                schedule_lines.append(f"{status_icon} `{time_str}` {cat_emoji} {title} ({dur} мин)")
        else:
            sorted_tasks = sorted(SCHEDULE.items(), key=lambda item: item[1].get("time"))
            for task_key, task_config in sorted_tasks:
                time_str = task_config.get("time").strftime("%H:%M")
                task_name = task_config.get("button_text", task_key).replace(" ✅", "")
                is_completed = is_task_completed_today(user.id, task_key)
                status_icon = "✅" if is_completed else "⏰"
                schedule_lines.append(f"{status_icon} `{time_str}` {task_name}")

        schedule_lines.append("\n💡 _Добавить привычку: /addtask <Имя> <HH:MM> [категория] [мин]_")
        await update.message.reply_text("\n".join(schedule_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка в schedule_handler для user_id {user.id}: {e}")
        await update.message.reply_text("Не удалось показать расписание.")


async def briefing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вызов утреннего брифинга по запросу пользователя."""
    user = update.effective_user
    if not user:
        return
    from scheduler import send_morning_briefing

    await send_morning_briefing(context.application, user.id)


async def tasks_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Интерфейс управления привычками и задачами."""
    user = update.effective_user
    if not user or not update.message:
        return
    tasks = get_user_schedule(user.id)
    text_lines = ["📋 **Управление привычками и расписанием:**\n"]

    for t in tasks:
        cat_emoji = CATEGORIES.get(t.get("category", ""), {}).get("emoji", "📌")
        text_lines.append(
            f"• `{t['task_key']}`: {cat_emoji} {t['title']} в `{t['time_str']}` "
            f"({t['duration_minutes']}м)"
        )

    text_lines.append("\n**Команды управления:**")
    text_lines.append("➕ `/addtask Чтение 21:00 study 30`")
    text_lines.append("➖ `/deltask <ключ_задачи>` (например `/deltask morning_workout`)")

    await update.message.reply_text("\n".join(text_lines), parse_mode="Markdown")


async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление новой задачи: /addtask <Название> <HH:MM> [категория] [длительность]."""
    user = update.effective_user
    if not user or not update.message:
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Формат команды:\n`/addtask Название HH:MM [категория] [длительность]`\n\n"
            "Пример:\n`/addtask Йога 07:30 health 45`\n"
            "Категории: `work`, `rest`, `health`, `study`, `routine`",
            parse_mode="Markdown",
        )
        return

    title = args[0]
    time_str = args[1]
    category = args[2] if len(args) > 2 and args[2] in CATEGORIES else "routine"
    try:
        duration = int(args[3]) if len(args) > 3 else 30
    except ValueError:
        duration = 30

    # Простая валидация формата времени
    try:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        clean_time_str = f"{hour:02d}:{minute:02d}"
    except Exception:
        await update.message.reply_text("Неверный формат времени! Используйте формат `HH:MM`.")
        return

    task_key = f"task_{int(datetime.now().timestamp())}_{random.randint(100, 999)}"
    add_user_task(
        user_id=user.id,
        task_key=task_key,
        title=title,
        time_str=clean_time_str,
        category=category,
        duration_minutes=duration,
    )
    cat_emoji = CATEGORIES[category]["emoji"]
    await update.message.reply_text(
        f"✅ Задача **{title}** успешно добавлена!\n"
        f"⏰ Время: `{clean_time_str}`\n"
        f"{cat_emoji} Категория: {CATEGORIES[category]['name']}\n"
        f"⏱ Длительность: {duration} мин.",
        parse_mode="Markdown",
    )


async def del_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление задачи: /deltask <task_key>."""
    user = update.effective_user
    if not user or not update.message:
        return
    if not context.args:
        await update.message.reply_text("Укажите ключ задачи: `/deltask <task_key>`")
        return

    task_key = context.args[0]
    success = delete_user_task(user.id, task_key)
    if success:
        await update.message.reply_text(f"🗑 Задача `{task_key}` удалена из вашего расписания.")
    else:
        await update.message.reply_text(f"Задача `{task_key}` не найдена.")


async def timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор часового пояса."""
    user = update.effective_user
    if not user or not update.message:
        return
    current_tz = get_user_timezone(user.id)
    await update.message.reply_text(
        f"🕒 Ваш текущий часовой пояс: **{current_tz}**\n\n"
        "Выберите ваш город для точной доставки утренних брифингов и напоминаний:",
        reply_markup=get_timezone_inline_keyboard(),
        parse_mode="Markdown",
    )


async def pro_subscription_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о подписке Pro и оплата через Telegram Stars."""
    user = update.effective_user
    if not user or not update.message:
        return
    pro_active = is_user_pro(user.id)
    status_text = "⭐ **Ваш статус: PRO активирован**" if pro_active else "🔓 **Тариф: Базовый**"

    text = (
        f"{status_text}\n\n"
        "🚀 **Возможности Ratio & Schedule PRO:**\n"
        "• Неограниченное число привычек и кастомных расписаний\n"
        "• Расширенная Work/Rest Ratio инфографика и Life Balance Score\n"
        "• Персональные утренние брифинги и вечерняя аналитика\n"
        "• Telegram WebApp визуальный таймлайн\n"
        "• Приоритетные умные напоминания (Snooze / Skip)\n\n"
        f"Стоимость: **{PRO_PRICE_STARS} ⭐ Telegram Stars** (~$2.99 / месяц)"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"⭐ Оформить Pro за {PRO_PRICE_STARS} Stars", callback_data="buy_pro"
                )
            ]
        ]
    )
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def share_card_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация виральной карточки продуктивности для шеринга в каналах и Stories."""
    user = update.effective_user
    if not user or not update.message:
        return
    analytics = get_ratio_analytics(user.id, days=7)
    streak = get_user_streak(user.id)
    rate = get_completion_rate(user.id, days=7)

    card = (
        "🏆 **Моя карточка продуктивности | Ratio & Schedule**\n\n"
        f"🔥 Текущий стрик: **{streak} дней подряд**\n"
        f"⚖️ Баланс работы и отдыха: **{analytics['work_to_rest_ratio']} : 1**\n"
        f"🎯 Эффективность за неделю: **{rate:.1f}%**\n"
        f"🌟 Life Balance Score: **{analytics['balance_score']}/100**\n\n"
        "Управляй днем и держи гармоничный баланс в @ratioAndScheduleBot!"
    )
    await update.message.reply_text(card, parse_mode="Markdown")


# --- Обработчик инлайн-кнопок ---


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user = query.from_user
    data = query.data or ""
    update_user_activity(user.id)

    try:
        if data.startswith("complete_"):
            task_key = data.replace("complete_", "")
            task_conf = SCHEDULE.get(task_key)
            task_title = task_conf.get("button_text", task_key) if task_conf else task_key

            if mark_task_completed(user.id, task_key, task_title):
                streak = get_user_streak(user.id)
                streak_msg = f" (Стрик: {streak} дн. 🔥)" if streak > 1 else ""
                msg = f"✅ Задача выполнена!{streak_msg}"
                await query.edit_message_text(msg)
                motivational = random.choice(MESSAGES.get("motivational", ["Отличная работа!"]))
                await context.bot.send_message(chat_id=user.id, text=motivational)
            else:
                await query.edit_message_text("ℹ️ Эта задача уже отмечена сегодня.")

        elif data.startswith("snooze_"):
            task_key = data.replace("snooze_", "")
            snooze_until = snooze_task(user.id, task_key, minutes=15)
            await query.edit_message_text(f"⏱ Задача отложена до {snooze_until.strftime('%H:%M')}.")

        elif data.startswith("skip_"):
            task_key = data.replace("skip_", "")
            skip_task(user.id, task_key)
            await query.edit_message_text("⏭ Задача пропущена на сегодня.")

        elif data.startswith("settz_"):
            tz_code = data.replace("settz_", "")
            set_user_timezone(user.id, tz_code)
            await query.edit_message_text(f"✅ Часовой пояс успешно установлен: **{tz_code}**")

        elif data == "buy_pro":
            # Отправка инвойса в Telegram Stars (валюта XTR)
            prices = [LabeledPrice(label="Pro доступ на 30 дней", amount=PRO_PRICE_STARS)]
            await context.bot.send_invoice(
                chat_id=user.id,
                title="Ratio & Schedule PRO",
                description="30 дней Pro: безлимитные привычки, Life Balance Score и WebApp.",
                payload=f"pro_sub_{user.id}_{int(datetime.now().timestamp())}",
                provider_token="",  # Для Stars provider_token оставляется пустым
                currency="XTR",
                prices=prices,
            )

        elif data == "share_card":
            await share_card_handler(update, context)

    except Exception as e:
        logger.error(f"Ошибка в button_handler для user {user.id} с data '{data}': {e}")
        await query.edit_message_text("Произошла ошибка при обработке действия.")


# --- Обработчики платежей Telegram Stars ---


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение готовности принять платеж Telegram Stars."""
    query: PreCheckoutQuery = update.pre_checkout_query
    if query:
        await query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешной оплаты Telegram Stars."""
    if not update.message or not update.message.successful_payment:
        return
    user = update.effective_user
    sp = update.message.successful_payment

    record_payment(
        user_id=user.id,
        telegram_charge_id=sp.telegram_payment_charge_id,
        provider_charge_id=sp.provider_payment_charge_id or "",
        amount_stars=sp.total_amount,
    )
    activate_user_pro(user.id, days=30)

    logger.info(f"Успешная оплата Stars пользователем {user.id}: {sp.total_amount} XTR")
    await update.message.reply_text(
        "🎉 **Поздравляем с переходом на PRO!**\n\n"
        "Вам открыты безлимитные привычки, глубокая аналитика баланса "
        "и полный доступ к функциям планирования на 30 дней. Спасибо за поддержку проекта! ⭐",
        parse_mode="Markdown",
    )


# --- Обработчик данных из Telegram WebApp ---


async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Прием обновлений расписания из Telegram WebApp."""
    user = update.effective_user
    if not update.message or not update.message.web_app_data:
        return

    try:
        raw_data = update.message.web_app_data.data
        data = json.loads(raw_data)
        action = data.get("action")

        if action == "add_task":
            title = data.get("title", "Задача")
            time_str = data.get("time_str", "12:00")
            category = data.get("category", "routine")
            duration = int(data.get("duration", 30))
            task_key = f"t_{int(datetime.now().timestamp())}_{random.randint(10, 99)}"
            add_user_task(user.id, task_key, title, time_str, category, duration)
            await update.message.reply_text(
                f"📱 WebApp: Задача **{title}** сохранена в расписании!"
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке WebApp данных: {e}")
        await update.message.reply_text("Не удалось сохранить изменения из WebApp.")


# --- Обработчик текстовых сообщений меню ---


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений, включая нажатия на Reply-кнопки."""
    user = update.effective_user
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower().strip()

    clean_text = (
        text.replace("📊 ", "")
        .replace("📈 ", "")
        .replace("🗓 ", "")
        .replace("ℹ️ ", "")
        .replace("⚖️ ", "")
        .replace("🌅 ", "")
        .replace("⭐ ", "")
        .replace("⚙️ ", "")
    )

    try:
        if clean_text in ["статус", "status"]:
            await status_handler(update, context)
        elif clean_text in ["баланс (ratio)", "баланс", "ratio"]:
            await ratio_handler(update, context)
        elif clean_text in ["отчёт", "отчет", "report"]:
            await report_handler(update, context)
        elif clean_text in ["расписание", "schedule"]:
            await schedule_handler(update, context)
        elif clean_text in ["брифинг", "briefing"]:
            await briefing_handler(update, context)
        elif clean_text in ["pro (stars)", "pro"]:
            await pro_subscription_handler(update, context)
        elif clean_text in ["настройки", "settings"]:
            await timezone_handler(update, context)
        elif clean_text in ["помощь", "help"]:
            await start_handler(update, context)
        else:
            await update.message.reply_text(
                MESSAGES.get("unknown_message", "Я вас не понимаю."),
                reply_markup=get_main_keyboard(),
            )
    except Exception as e:
        logger.error(f"Ошибка в message_handler для user {user.id} ('{text}'): {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего сообщения.")
