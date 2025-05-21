from aiogram import Dispatcher
from aiogram.dispatcher.filters import Text, Command, CommandStart
from aiogram.dispatcher.filters.state import State, StatesGroup

from .admin_handlers import register_admin_handlers
from .chat_handlers import register_chat_handlers
from .game_handlers import register_game_handlers
from .user_handlers import register_user_handlers
from .callback_handlers import register_callback_handlers

from commands import (
    cmd_start,
    cmd_help,
    cmd_subscribe,
    cmd_unsubscribe,
    cmd_status,
    cmd_broadcast,
    process_broadcast_message,
    confirm_broadcast,
    cancel_broadcast,
    process_other_message
)

from admin_commands import (
    cmd_admin,
    add_admin,
    remove_admin,
    get_user_info,
    update_user_activity,
    AddAdminStates,
    RemoveAdminStates,
    UserInfoStates
)

from callbacks import (
    cmd_settings,
    cmd_menu,
    process_callback
)

from chat_commands import (
    cmd_who,
    cmd_future,
    cmd_goal,
    cmd_stat
)

from game_actions import (
    cmd_action,
    process_action_input,
    direct_action_processing,
    cmd_history,
    cmd_action_result,
    cmd_report,
    process_action_confirmation,
    ActionStates
)

from broadcast import BroadcastStates


def register_all_handlers(dp: Dispatcher, admin_ids: list):
    """
    Регистрирует все обработчики команд и сообщений

    Args:
        dp: Диспетчер бота
        admin_ids: Список ID администраторов
    """
    # Регистрация всех модулей обработчиков
    register_admin_handlers(dp, admin_ids)
    register_chat_handlers(dp)
    register_game_handlers(dp)
    register_user_handlers(dp)
    register_callback_handlers(dp, admin_ids)

    # Регистрация базовых команд
    dp.register_message_handler(cmd_start, CommandStart())
    dp.register_message_handler(cmd_help, Command("help"))
    dp.register_message_handler(cmd_subscribe, Command("subscribe"))
    dp.register_message_handler(cmd_unsubscribe, Command("unsubscribe"))
    dp.register_message_handler(cmd_status, Command("status"))
    dp.register_message_handler(cmd_menu, Command("menu"))
    dp.register_message_handler(cmd_settings, Command("settings"))

    # Административные команды
    dp.register_message_handler(
        cmd_admin,
        lambda msg: msg.from_user.id in admin_ids,
        Command("admin")
    )
    dp.register_message_handler(
        cmd_broadcast,
        lambda msg: msg.from_user.id in admin_ids,
        Command("broadcast")
    )

    # Обработчики состояний для административных команд
    dp.register_message_handler(
        add_admin,
        lambda msg: msg.from_user.id in admin_ids,
        state=AddAdminStates.waiting_for_user_id
    )
    dp.register_message_handler(
        remove_admin,
        lambda msg: msg.from_user.id in admin_ids,
        state=RemoveAdminStates.waiting_for_user_id
    )
    dp.register_message_handler(
        get_user_info,
        lambda msg: msg.from_user.id in admin_ids,
        state=UserInfoStates.waiting_for_user_id
    )

    # Обработчики состояний для рассылки
    dp.register_message_handler(
        process_broadcast_message,
        lambda msg: msg.from_user.id in admin_ids,
        state=BroadcastStates.waiting_for_message
    )
    dp.register_message_handler(
        confirm_broadcast,
        lambda msg: msg.from_user.id in admin_ids,
        Command("confirm"),
        state=BroadcastStates.waiting_for_message
    )
    dp.register_message_handler(
        cancel_broadcast,
        lambda msg: msg.from_user.id in admin_ids,
        Command("cancel"),
        state=BroadcastStates.waiting_for_message
    )
    dp.register_message_handler(
        process_other_message,
        lambda msg: msg.from_user.id in admin_ids,
        state=BroadcastStates.waiting_for_message
    )

    # Команды для чатов
    dp.register_message_handler(
        cmd_who,
        lambda msg: msg.chat.type != 'private',
        Command("who")
    )
    dp.register_message_handler(
        cmd_future,
        lambda msg: msg.chat.type != 'private',
        Command("future")
    )
    dp.register_message_handler(
        cmd_goal,
        lambda msg: msg.chat.type != 'private',
        Command("goal")
    )
    dp.register_message_handler(
        cmd_stat,
        lambda msg: msg.chat.type != 'private',
        Command("stat")
    )

    # Игровые команды
    dp.register_message_handler(cmd_action, Command("action"))
    dp.register_message_handler(process_action_input, state=ActionStates.waiting_for_action)
    dp.register_message_handler(cmd_history, Command("history"))
    dp.register_message_handler(cmd_report, Command("report"))

    # Регистрация обработчика результатов действий
    dp.register_message_handler(
        cmd_action_result,
        lambda msg: msg.text.startswith("/result_")
    )

    # Отслеживание активности пользователей
    dp.register_message_handler(
        update_user_activity,
        lambda msg: True,
        content_types=["text"]
    )

    # Обработка прямых сообщений как потенциальных приказов (только в личных сообщениях)
    dp.register_message_handler(
        direct_action_processing,
        lambda msg: msg.chat.type == 'private',
        content_types=["text"]
    )

    # Регистрация обработчиков callback-запросов
    dp.register_callback_query_handler(process_action_confirmation, Text(equals=["confirm_action", "cancel_action"]))
    dp.register_callback_query_handler(process_callback, lambda c: True)
