"""
__init__.py для модуля game_logic.

Экспортирует основные компоненты игровой логики для использования в других модулях.
Предоставляет доступ к функциям управления игроками, экономикой, дипломатией и военными действиями.
"""

from .player import (
    Player,
    PlayerManager,
    get_player,
    get_player_by_username,
    get_all_players,
    reload_player
)

from .stats_manager import (
    init_stats,
    distribute_points,
    reset_stats,
    validate_stats,
    analyze_stats,
    format_stats_for_display,
    get_effective_stats,
    modify_stat
)

from .project_manager import (
    create_project,
    get_projects,
    update_projects_progress,
    handle_project_completion,
    extract_potential_projects,
    confirm_project_creation,
    get_project_details
)

from .events_generator import (
    generate_random_event,
    generate_event,
    apply_event,
    should_generate_event,
    get_recent_events,
    generate_global_event
)

from .combat_system import (
    initiate_conflict,
    get_conflict_details,
    get_country_conflicts
)

from .economy import (
    extract_resources,
    calculate_income_expenses,
    update_resources,
    initiate_trade
)

from .diplomacy import (
    get_relations,
    change_relations,
    create_treaty,
    respond_to_treaty,
    get_active_treaties,
    analyze_diplomatic_position
)

__all__ = [
    # Player management
    'Player',
    'PlayerManager',
    'get_player',
    'get_player_by_username',
    'get_all_players',
    'reload_player',

    # Stats management
    'init_stats',
    'distribute_points',
    'reset_stats',
    'validate_stats',
    'analyze_stats',
    'format_stats_for_display',
    'get_effective_stats',
    'modify_stat',

    # Projects management
    'create_project',
    'get_projects',
    'update_projects_progress',
    'handle_project_completion',
    'extract_potential_projects',
    'confirm_project_creation',
    'get_project_details',

    # Events management
    'generate_random_event',
    'generate_event',
    'apply_event',
    'should_generate_event',
    'get_recent_events',
    'generate_global_event',

    # Combat system
    'initiate_conflict',
    'get_conflict_details',
    'get_country_conflicts',

    # Economy management
    'extract_resources',
    'calculate_income_expenses',
    'update_resources',
    'initiate_trade',

    # Diplomacy management
    'get_relations',
    'change_relations',
    'create_treaty',
    'respond_to_treaty',
    'get_active_treaties',
    'analyze_diplomatic_position'
]
