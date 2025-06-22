from . import user_commands
from . import registration
from . import admin
from . import cancel
from . import game_aspects_buttons

def register_handlers(dp):
    user_commands.register(dp)
    registration.register(dp)
    admin.register(dp)
    cancel.register(dp)
    game_aspects_buttons.register(dp)
