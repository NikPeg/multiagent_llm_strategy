from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup

from .admin_commands import (
    cmd_admin,
    add_admin,
    remove_admin,
    get_user_info,
    process_admin_callback,
    show_stats,
    AddAdminStates,
    RemoveAdminStates,
    UserInfoStates,
    admin_cb,
    stats_cb
)


def register_admin_handlers(dp: Dispatcher, admin_ids: list):
    """Регистрирует административные команды и callback'и"""

    # /admin – административная панель
    async def _cmd_admin_wrap(message: types.Message):
        await cmd_admin(message, admin_ids)

    dp.register_message_handler(
        _cmd_admin_wrap,
        Command("admin"),
        lambda msg: msg.from_user.id in admin_ids
    )

    # FSM: ожидание id пользователя для добавления администратора
    async def _add_admin_wrap(message: types.Message, state):
        await add_admin(message, state, admin_ids)

    dp.register_message_handler(
        _add_admin_wrap,
        lambda msg: msg.from_user.id in admin_ids,
        state=AddAdminStates.waiting_for_user_id
    )

    # FSM: ожидание id пользователя для удаления администратора
    async def _remove_admin_wrap(message: types.Message, state):
        await remove_admin(message, state, admin_ids)

    dp.register_message_handler(
        _remove_admin_wrap,
        lambda msg: msg.from_user.id in admin_ids,
        state=RemoveAdminStates.waiting_for_user_id
    )

    # FSM: ожидание id пользователя для просмотра информации
    dp.register_message_handler(
        get_user_info,
        lambda msg: msg.from_user.id in admin_ids,
        state=UserInfoStates.waiting_for_user_id
    )

    # Callback для административных кнопок (админ-панель)
    async def _process_admin_callback_wrap(call: types.CallbackQuery, callback_data: dict, state):
        await process_admin_callback(call, callback_data, state, admin_ids)

    dp.register_callback_query_handler(
        _process_admin_callback_wrap,
        admin_cb.filter(),  # callback_data['@'] == 'admin'
        state="*"
    )

    # Callback для показа статистики
    dp.register_callback_query_handler(
        show_stats,
        stats_cb.filter(),
        state="*"
    )
