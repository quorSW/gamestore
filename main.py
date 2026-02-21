"""
Админ-панель @gamestoren_bot (бот-версия)

Команды:
  /admin    — главное меню
  /ban ID   — заблокировать пользователя
  /unban ID — разблокировать
  /cancel   — отмена текущего действия

Промокоды создаются ТОЛЬКО через @cosmicclicker_bot — здесь только просмотр.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


def _adm(uid: int, config) -> bool:
    return uid in config.ADMIN_IDS


class AdminStates(StatesGroup):
    broadcast_text = State()
    addkeys_values = State()


# ── /admin ──────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(message: Message, config):
    if not _adm(message.from_user.id, config):
        return
    await _menu(message, config, edit=False)


async def _menu(msg_or_cb, config, edit=True):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика",      callback_data="adm_stats")],
        [InlineKeyboardButton(text="👥 Пользователи",    callback_data="adm_users_0")],
        [InlineKeyboardButton(text="📢 Рассылка",        callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🎁 Промокоды",       callback_data="adm_promos")],
        [InlineKeyboardButton(text="🔑 Добавить ключи",  callback_data="adm_addkeys")],
    ])
    text = "🛠 <b>Панель администратора</b>"
    if edit:
        await msg_or_cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await msg_or_cb.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Статистика ───────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_stats")
async def adm_stats(cb: CallbackQuery, db, config):
    if not _adm(cb.from_user.id, config): return
    s  = await db.get_stats()
    ps = await db.get_promo_stats()
    await cb.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{s['users']}</b>  (+{s['new_today']} сегодня)\n"
        f"✅ Выполнено заказов: <b>{s['orders']}</b>\n"
        f"💰 Общая выручка: <b>{int(s['revenue'])}₽</b>\n"
        f"📅 Сегодня: <b>{int(s['today_revenue'])}₽</b>\n\n"
        f"🎁 Промокоды: всего {ps['total']}, "
        f"использовано {ps['used']}, "
        f"доступно <b>{ps['available']}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")]
        ]),
        parse_mode="HTML"
    )


# ── Пользователи (с пагинацией) ─────────────────────────────────────
PAGE_SIZE = 15

@router.callback_query(F.data.startswith("adm_users_"))
async def adm_users(cb: CallbackQuery, db, config):
    if not _adm(cb.from_user.id, config): return
    page = int(cb.data.split("_")[-1])
    users = await db.get_all_users()
    total = len(users)
    chunk = users[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    lines = []
    for u in chunk:
        name  = (u.get("full_name") or "Без имени")[:20]
        uname = f"@{u['username']}" if u.get("username") else "—"
        spent = int(u.get("total_spent", 0))
        ban   = " 🚫" if u.get("is_banned") else ""
        lines.append(f"• <b>{name}</b> {uname}{ban}\n  ID: <code>{u['tg_id']}</code> | {spent}₽ | {str(u.get('joined_at',''))[:10]}")

    text = f"👥 <b>Пользователи</b> ({total} всего, стр. {page+1})\n\n" + "\n\n".join(lines)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm_users_{page-1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm_users_{page+1}"))

    kb = []
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")])

    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")


# ── Рассылка ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_start(cb: CallbackQuery, state: FSMContext, config):
    if not _adm(cb.from_user.id, config): return
    await state.set_state(AdminStates.broadcast_text)
    await cb.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Напиши текст — поддерживается HTML (<b>жирный</b>, <i>курсив</i>, <code>код</code>).\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML"
    )


@router.message(AdminStates.broadcast_text)
async def adm_broadcast_send(message: Message, state: FSMContext, db, config):
    if not _adm(message.from_user.id, config): return
    await state.clear()
    users = await db.get_all_users(not_banned=True)
    text  = message.text or message.caption or ""
    sent = failed = 0
    prog = await message.answer(f"📤 Рассылаем {len(users)} пользователям...")
    for u in users:
        try:
            await message.bot.send_message(u["tg_id"], text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await prog.edit_text(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"✔️ Доставлено: {sent}\n❌ Ошибок: {failed}",
        parse_mode="HTML"
    )


# ── Промокоды (только просмотр) ──────────────────────────────────────
@router.callback_query(F.data == "adm_promos")
async def adm_promos(cb: CallbackQuery, db, config):
    if not _adm(cb.from_user.id, config): return
    ps     = await db.get_promo_stats()
    promos = await db.get_all_promos()

    lines = []
    for p in promos[:25]:
        icon = "✅" if not p["is_used"] else "❌"
        lines.append(f"{icon} <code>{p['code']}</code> — {p['discount_percent']}%")

    text = (
        f"🎁 <b>Промокоды</b>\n"
        f"Всего: {ps['total']} | Использовано: {ps['used']} | "
        f"Доступно: <b>{ps['available']}</b>\n\n"
        f"Промокоды создаются <b>только через @cosmicclicker_bot</b>.\n\n"
        + ("\n".join(lines) if lines else "Промокодов пока нет")
    )
    await cb.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")]
        ]),
        parse_mode="HTML"
    )


# ── Ключи ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "adm_addkeys")
async def adm_addkeys_list(cb: CallbackQuery, db, config):
    if not _adm(cb.from_user.id, config): return
    products = await db.get_products()
    rows = []
    for p in products[:20]:
        cnt = await db.count_available_keys(p["id"])
        rows.append([InlineKeyboardButton(
            text=f"{p['emoji']} {p['name']}  [{cnt} ключей]",
            callback_data=f"adm_keys_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back")])
    await cb.message.edit_text(
        "🔑 <b>Добавить ключи</b>\n\nВыбери товар:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_keys_"))
async def adm_addkeys_select(cb: CallbackQuery, state: FSMContext, config):
    if not _adm(cb.from_user.id, config): return
    pid = int(cb.data[9:])
    await state.update_data(product_id=pid)
    await state.set_state(AdminStates.addkeys_values)
    await cb.message.edit_text(
        "🔑 Отправь ключи, каждый с новой строки:\n\n"
        "<code>XXXX-YYYY-ZZZZ\nAAAA-BBBB-CCCC</code>",
        parse_mode="HTML"
    )


@router.message(AdminStates.addkeys_values)
async def adm_addkeys_save(message: Message, state: FSMContext, db, config):
    if not _adm(message.from_user.id, config): return
    data = await state.get_data()
    await state.clear()
    keys = [k.strip() for k in message.text.strip().splitlines() if k.strip()]
    if not keys:
        await message.answer("❌ Не нашёл ключи")
        return
    await db.add_keys(data["product_id"], keys)
    await message.answer(f"✅ Добавлено <b>{len(keys)}</b> ключей", parse_mode="HTML")


# ── Ban / Unban ───────────────────────────────────────────────────────
@router.message(Command("ban"))
async def cmd_ban(message: Message, db, config):
    if not _adm(message.from_user.id, config): return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /ban <tg_id>"); return
    try:
        await db.ban_user(int(parts[1]))
        await message.answer(f"✅ Пользователь {parts[1]} заблокирован")
    except ValueError:
        await message.answer("❌ Неверный ID")


@router.message(Command("unban"))
async def cmd_unban(message: Message, db, config):
    if not _adm(message.from_user.id, config): return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /unban <tg_id>"); return
    try:
        await db.unban_user(int(parts[1]))
        await message.answer(f"✅ Пользователь {parts[1]} разблокирован")
    except ValueError:
        await message.answer("❌ Неверный ID")


@router.callback_query(F.data == "adm_back")
async def adm_back(cb: CallbackQuery, config):
    if not _adm(cb.from_user.id, config): return
    await _menu(cb, config, edit=True)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, config):
    if not _adm(message.from_user.id, config): return
    await state.clear()
    await message.answer("✅ Отменено")
