import pygame
import math
from .constants import RESOURCE_COLORS, HEX_SIZE, VERTEX_RADIUS, PLAYER_COLORS, ROAD_WIDTH, WIDTH, HEIGHT
from .enums import BuildingType

def draw_hex(surface, color, pos, size, text=None, font=None):
    x, y = pos
    points = []
    for i in range(6):
        angle = math.radians(60 * i + 30)
        dx = size * math.cos(angle)
        dy = size * math.sin(angle)
        points.append((x + dx, y + dy))
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, (0, 0, 0), points, 2)
    if text and font:
        label = font.render(text, True, (0, 0, 0))
        surface.blit(label, (x - label.get_width() // 2, y - label.get_height() // 2))
    return points

def render_game(screen, font, game):
    screen.fill((255, 255, 255))

    for hex_data in game.hexes:
        color = RESOURCE_COLORS[hex_data['resource']]
        draw_hex(screen, color, hex_data['position'], HEX_SIZE,
                 text=str(hex_data['token']) if hex_data['token'] else None,
                 font=font)

    for u, v, data in game.graph.edges(data=True):
        color = (150, 150, 150)
        if data['owner'] is not None:
            color = PLAYER_COLORS[data['owner'] % len(PLAYER_COLORS)]
        pygame.draw.line(screen, color, u, v, ROAD_WIDTH)

    for node, data in game.graph.nodes(data=True):
        if data['owner'] is not None:
            color = PLAYER_COLORS[data['owner'] % len(PLAYER_COLORS)]
            radius = VERTEX_RADIUS if data['building'] == BuildingType.SETTLEMENT else VERTEX_RADIUS + 2
            pygame.draw.circle(screen, color, node, radius)
            pygame.draw.circle(screen, (0, 0, 0), node, radius, 1)

    player = game.get_current_player()
    turn_text = f"Gracz {game.current_player_idx + 1} ma turę :  (Punkty: {player['victory_points']})"
    turn_label = font.render(turn_text, True, PLAYER_COLORS[game.current_player_idx % len(PLAYER_COLORS)])
    screen.blit(turn_label, (10, 10))

    mode_text = "Faza gry: LPM - wioska, PPM -  roads, Spacja - koniec tury, Scroll - ulepsz do miasta, T - Trading"
    mode_label = font.render(mode_text, True, (0, 0, 0))
    screen.blit(mode_label, (10, 40))

    if not game.initial_placement_phase:
        koszty_text = [
            "Co ile kosztuje :",
            "Droga - 1 Drewno, 1 Glina",
            "Wioska - 1 Drewno, 1 Glina, 1 Owca, 1 Zboze",
            "Miasto - 2 Zboze, 3 Kamień"
        ]
        y_pos = HEIGHT - 120
        for text in koszty_text:
            cost_label = font.render(text, True, (0, 0, 0))
            screen.blit(cost_label, (10, y_pos))
            y_pos += 20

    if game.trading_mode:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))

        if game.trade_stage == 0:
            text = "Wybierz zasób który chcesz DOSTAĆ:"
            options = [
                "1 - Drewno",
                "2 - Glina",
                "3 - Owca",
                "4 - Zboże",
                "5 - Kamień",
                "ESC - Anuluj"
            ]
        else:
            text = f"Wybierz zasób który chcesz ODAĆ za {game.selected_trade_resource}:"
            options = [
                "1 - Drewno",
                "2 - Glina",
                "3 - Owca",
                "4 - Zboże",
                "5 - Kamień",
                "ESC - Anuluj"
            ]

        dialog_width = 400
        dialog_height = 200
        dialog_x = (WIDTH - dialog_width) // 2
        dialog_y = (HEIGHT - dialog_height) // 2

        pygame.draw.rect(screen, (240, 240, 240), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(screen, (0, 0, 0), (dialog_x, dialog_y, dialog_width, dialog_height), 2)

        text_label = font.render(text, True, (0, 0, 0))
        screen.blit(text_label, (dialog_x + 20, dialog_y + 20))

        option_y = dialog_y + 60
        for option in options:
            option_label = font.render(option, True, (0, 0, 0))
            screen.blit(option_label, (dialog_x + 40, option_y))
            option_y += 30

    if not game.initial_placement_phase and game.diceroll:
        dice_text = f"Ostatni wynik: {game.diceroll}"
        dice_label = font.render(dice_text, True, (0, 0, 0))
        screen.blit(dice_label, (WIDTH - 150, 10))

        resources_text = "Zasoby: " + ", ".join(
            f"{res}: {count}" for res, count in player['resources'].items() if count > 0
        )
        resources_label = font.render(resources_text, True, PLAYER_COLORS[game.current_player_idx])
        screen.blit(resources_label, (10, 70))

    if game.robber_hex:
        robber_pos = game.robber_hex['position']
        pygame.draw.circle(screen, (0, 0, 0), (int(robber_pos[0]), int(robber_pos[1])), 15)

    if game.robber_phase:
        robber_text = "Select a hex to place the robber (click on a hex)"
        robber_label = font.render(robber_text, True, (255, 0, 0))
        screen.blit(robber_label, (WIDTH // 2 - robber_label.get_width() // 2, 50))