from aiogram.filters.callback_data import CallbackData


class SituationCallback(CallbackData, prefix="s"):
    situation_id: str


class LevelCallback(CallbackData, prefix="l"):
    situation_id: str
    level_id: str


class ActionCallback(CallbackData, prefix="a"):
    action: str
