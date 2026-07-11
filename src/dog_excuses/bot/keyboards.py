from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from dog_excuses.bot.callbacks import ActionCallback, LevelCallback, SituationCallback
from dog_excuses.catalog import LEVELS, SITUATIONS


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐕 Придумать отмазку", callback_data="a:choose")]
        ]
    )


def situations_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for situation in SITUATIONS:
        builder.button(
            text=f"{situation.emoji} {situation.title}",
            callback_data=SituationCallback(situation_id=situation.id),
        )
    builder.adjust(2)
    return builder.as_markup()


def levels_keyboard(situation_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in LEVELS.values():
        builder.button(
            text=f"{level.emoji} {level.label}",
            callback_data=LevelCallback(situation_id=situation_id, level_id=level.id.value),
        )
    builder.button(text="⬅️ Ситуации", callback_data=ActionCallback(action="choose"))
    builder.adjust(1)
    return builder.as_markup()


def result_keyboard(share_query: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Ещё отмазку", callback_data="a:reroll")],
            [
                InlineKeyboardButton(text="🎭 Сменить наглость", callback_data="a:levels"),
                InlineKeyboardButton(text="📋 Сменить ситуацию", callback_data="a:choose"),
            ],
            [InlineKeyboardButton(text="📨 Поделиться", switch_inline_query=share_query)],
        ]
    )
