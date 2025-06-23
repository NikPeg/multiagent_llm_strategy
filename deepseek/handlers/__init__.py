from . import admin, cancel, game_aspects_buttons, game_logic, registration, user_commands


def register_handlers(dp):
    user_commands.register(dp)
    registration.register(dp)
    admin.register(dp)
    cancel.register(dp)
    game_aspects_buttons.register(dp)
    game_logic.register(dp)
