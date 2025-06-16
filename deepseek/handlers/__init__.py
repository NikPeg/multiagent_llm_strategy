from . import user_commands
from . import registration
from . import admin
from . import cancel
from . import game
from . import game_callbacks

def register_handlers(dp):
    user_commands.register(dp)
    registration.register(dp)
    admin.register(dp)
    cancel.register(dp)
    game.register(dp)
    game_callbacks.register(dp)
