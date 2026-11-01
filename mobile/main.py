# /// script
# requires-python = ">=3.12"
# dependencies = ["pygame.base"]
# ///
# -*- coding: utf-8 -*-
"""Точка входа мобильной версии (pygame-web / pygbag).

pygbag запускает этот файл в браузере и требует, чтобы игра была
асинхронной: игровой цикл внутри game_app отдаёт управление браузеру
на каждом кадре. Десктопная версия — game.py.

Блок PEP 723 сверху обязателен: без него рантайм не знает, что нужен pygame.
Имя "pygame.base" — не опечатка: в site-packages лежит заглушка pygame
(только шрифты), и обычное "pygame" рантайм считает уже установленным.
Специальный случай в aio/pep0723.py как раз для "pygame.base" — он
принудительно ставит настоящее колесо pygame_ce.
"""
import asyncio

import pygame  # noqa: F401  — рантайм видит импорт и ставит колесо pygame

import game_app


asyncio.run(game_app.main())
