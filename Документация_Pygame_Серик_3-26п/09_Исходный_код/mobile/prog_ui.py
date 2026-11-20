# -*- coding: utf-8 -*-
"""Совместимость: HUD и «Депо» переехали в taran/ui/hud.py.

game.py и мобильная сборка по-прежнему делают `import prog_ui as UI`,
поэтому этот файл остаётся тонким реэкспортом. Новый код должен
импортировать taran.ui.hud напрямую.
"""
from taran.ui.hud import *  # noqa: F401,F403
# приватные раскладки нужны старым тестам (_meta_test.py)
from taran.ui.hud import (  # noqa: F401
    _ach_rects, _contract_rects, _nav_rects, _relic_choice_rects,
    _relic_owned_rects, _tree_rects,
)
