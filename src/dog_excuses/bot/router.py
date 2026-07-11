import hashlib

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dog_excuses.bot.callbacks import ActionCallback, LevelCallback, SituationCallback
from dog_excuses.bot.keyboards import (
    levels_keyboard,
    result_keyboard,
    situations_keyboard,
    start_keyboard,
)
from dog_excuses.bot.rendering import decode_share, encode_share, render_result
from dog_excuses.catalog import SITUATIONS_BY_ID
from dog_excuses.db.repository import UserRepository, hash_user_id, increment_metric
from dog_excuses.domain import LevelId
from dog_excuses.services.generation import GenerationService

WELCOME = (
    "<b>Собачьи отмазки</b> 🐕\n\n"
    "Выбери, что случилось, и уровень наглости. Собака обеспечит алиби, "
    "а бот — процент правдоподобности.\n\n"
    '🐾 Бот создан проектом <a href="https://t.me/gafusRu">Гафус</a>.\n\n'
    "⚠️ Отмазки не предназначены для реальных ситуаций. Если сработало — это магия, "
    "если нет — мы предупреждали. Создатели не несут ответственности за последствия отправки."
)
HELP = (
    "Нажми «Придумать отмазку», выбери ситуацию и уровень наглости. "
    "Бот собирает историю из трёх согласованных фрагментов без нейросети. "
    "Кнопка «Поделиться» отправит результат в выбранный чат."
)
PRIVACY = (
    "Бот не хранит имя, username, сообщения или историю отмазок. "
    "Telegram ID сохраняется только как необратимый HMAC-хеш. "
    "Для работы защиты от повторов хранится техническое состояние, "
    "а для статистики — обезличенные дневные счётчики."
)


def create_router(
    factory: async_sessionmaker[AsyncSession], secret: str, bot_username: str
) -> Router:
    router = Router()
    service = GenerationService(factory)

    def identity(user_id: int) -> str:
        return hash_user_id(user_id, secret)

    async def safely_edit(
        callback: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup
    ) -> None:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    async def selection(callback: CallbackQuery) -> tuple[str | None, LevelId | None]:
        if callback.from_user is None:
            return None, None
        return await UserRepository(factory, identity(callback.from_user.id)).get_selection()

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        if message.from_user:
            await increment_metric(factory, "start")
        await message.answer(WELCOME, reply_markup=start_keyboard())

    @router.message(Command("excuse"))
    async def excuse(message: Message) -> None:
        await message.answer("<b>Что случилось?</b>", reply_markup=situations_keyboard())

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(HELP)

    @router.message(Command("privacy"))
    async def privacy(message: Message) -> None:
        await message.answer(PRIVACY)

    @router.callback_query(ActionCallback.filter(F.action == "choose"))
    async def choose(callback: CallbackQuery) -> None:
        await safely_edit(callback, "<b>Что случилось?</b>", situations_keyboard())

    @router.callback_query(SituationCallback.filter())
    async def choose_situation(callback: CallbackQuery, callback_data: SituationCallback) -> None:
        if callback.from_user is None or callback_data.situation_id not in SITUATIONS_BY_ID:
            await callback.answer("Эта кнопка устарела. Начнём заново.", show_alert=True)
            return
        repository = UserRepository(factory, identity(callback.from_user.id))
        await repository.set_selection(callback_data.situation_id, None)
        await increment_metric(factory, "choose_situation", callback_data.situation_id)
        title = SITUATIONS_BY_ID[callback_data.situation_id].title
        await safely_edit(
            callback,
            f"<b>{title}</b>\n\nТеперь выбери уровень наглости:",
            levels_keyboard(callback_data.situation_id),
        )

    async def show_result(
        callback: CallbackQuery, situation_id: str, level_id: LevelId, event: str
    ) -> None:
        if callback.from_user is None:
            return
        result = await service.generate(
            identity(callback.from_user.id), situation_id, level_id, event
        )
        await safely_edit(callback, render_result(result), result_keyboard(encode_share(result)))

    @router.callback_query(LevelCallback.filter())
    async def choose_level(callback: CallbackQuery, callback_data: LevelCallback) -> None:
        try:
            level_id = LevelId(callback_data.level_id)
            if callback_data.situation_id not in SITUATIONS_BY_ID:
                raise ValueError
        except ValueError:
            await callback.answer("Эта кнопка устарела. Начнём заново.", show_alert=True)
            return
        await show_result(callback, callback_data.situation_id, level_id, "choose_level")

    @router.callback_query(ActionCallback.filter(F.action == "reroll"))
    async def reroll(callback: CallbackQuery) -> None:
        situation_id, level_id = await selection(callback)
        if situation_id is None or level_id is None:
            await callback.answer("Выбор устарел. Выбери ситуацию заново.", show_alert=True)
            if isinstance(callback.message, Message):
                await callback.message.edit_text(
                    "<b>Что случилось?</b>", reply_markup=situations_keyboard()
                )
            return
        await show_result(callback, situation_id, level_id, "reroll")

    @router.callback_query(ActionCallback.filter(F.action == "levels"))
    async def change_level(callback: CallbackQuery) -> None:
        situation_id, _ = await selection(callback)
        if situation_id is None or situation_id not in SITUATIONS_BY_ID:
            await safely_edit(callback, "<b>Что случилось?</b>", situations_keyboard())
            return
        await safely_edit(
            callback,
            "<b>Выбери новый уровень наглости:</b>",
            levels_keyboard(situation_id),
        )

    @router.inline_query()
    async def inline_share(query: InlineQuery) -> None:
        result = decode_share(query.query.strip())
        if result is None:
            await query.answer([], cache_time=1, is_personal=True)
            return
        await increment_metric(factory, "share", result.situation_id, result.level_id)
        rendered = render_result(result)
        article = InlineQueryResultArticle(
            id=hashlib.sha256(query.query.encode()).hexdigest()[:32],
            title="Отправить собачью отмазку",
            description=f"{result.score}% — {result.verdict}",
            input_message_content=InputTextMessageContent(message_text=rendered),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🐕 Придумать свою",
                            url=f"https://t.me/{bot_username}?start=share",
                        )
                    ]
                ]
            ),
        )
        await query.answer([article], cache_time=1, is_personal=True)

    @router.callback_query()
    async def stale_callback(callback: CallbackQuery) -> None:
        await callback.answer("Эта кнопка устарела. Начнём заново.", show_alert=True)
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "<b>Что случилось?</b>", reply_markup=situations_keyboard()
            )

    return router
