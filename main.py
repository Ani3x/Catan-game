import pygame
import math
from game.constants import WIDTH, HEIGHT, FPS, HEX_SIZE, PLAYERS_NUMBERS
from game.graphics import render_game
from game.utils import get_hex_positions, rounded_pos, find_closest_node, find_closest_edge, find_closest_hex
from game.game_state import GameState


def initialize_game():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Catan Graph Representation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    game = GameState()
    for _ in range(PLAYERS_NUMBERS):
        game.add_player()

    from game.constants import RESOURCES, TOKENS
    resource_list = RESOURCES.copy()
    token_list = TOKENS.copy()

    import random
    random.shuffle(resource_list)
    random.shuffle(token_list)

    hex_positions = get_hex_positions(WIDTH // 2, HEIGHT // 2, HEX_SIZE)

    vertex_positions = {}
    edge_positions = set()

    from game.enums import BuildingType

    for pos in hex_positions:
        res = resource_list.pop()
        token = None if res == 'pustynia' else token_list.pop()

        vertices = []
        for i in range(6):
            angle = i * 60 + 30
            angle_rad = angle * 3.14159 / 180
            dx = HEX_SIZE * math.cos(angle_rad)
            dy = HEX_SIZE * math.sin(angle_rad)
            vertex = rounded_pos((pos[0] + dx, pos[1] + dy))
            vertices.append(vertex)

        hex_data = {
            'position': pos,
            'resource': res,
            'token': token,
            'vertices': vertices
        }
        game.hexes.append(hex_data)

        for vertex in vertices:
            if vertex not in game.graph:
                game.graph.add_node(vertex, pos=vertex, owner=None, building=BuildingType.NONE)

        for i in range(6):
            u = vertices[i]
            v = vertices[(i + 1) % 6]
            if (u, v) not in edge_positions and (v, u) not in edge_positions:
                game.graph.add_edge(u, v, owner=None)
                edge_positions.add((u, v))

    return screen, clock, font, game


def main():
    screen, clock, font, game = initialize_game()
    game.start_initial_placement()  # Startujemy z fazą placementów/rozstawiania
    running = True

    for hex_data in game.hexes:
        if hex_data['resource'] == 'desert':
            game.robber_position = hex_data
            break

    while running:
        render_game(screen, font, game)

        # Pokazaninie jaka jest aktualna faza
        if game.initial_placement_phase:
            phase_text = "Faza początkowa - " + (
                "Załóż osadę" if game.placement_stage == 0 else "Połóż drogę"
            )
            phase_label = font.render(phase_text, True, (255, 0, 0))
            screen.blit(phase_label, (WIDTH // 2 - phase_label.get_width() // 2, 10))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game.initial_placement_phase and not game.robber_phase:
                    game.next_turn()

                elif event.key == pygame.K_r and game.initial_placement_phase:
                    game.initial_placement_phase = False
                    game.initial_placement_complete = True

                if event.key == pygame.K_t and not game.initial_placement_phase: # Wchodzimy do trading mode
                    game.trading_mode = True
                    game.trade_stage = 0
                    game.selected_trade_resource = None
                if game.trading_mode:
                    resource_map = {
                        pygame.K_1: 'drewno',
                        pygame.K_2: 'glina',
                        pygame.K_3: 'owca',
                        pygame.K_4: 'zboze',
                        pygame.K_5: 'kamień'
                    }
                    if event.key in resource_map:
                        if game.trade_stage == 0:
                            game.selected_trade_resource = resource_map[event.key]
                            game.trade_stage = 1
                        else:
                            give_resource = resource_map[event.key]
                            if give_resource != game.selected_trade_resource:
                                game.trade_with_bank(
                                    game.current_player_idx,
                                    give_resource,
                                    game.selected_trade_resource
                                )
                            game.trading_mode = False
                    if event.key == pygame.K_ESCAPE:
                        game.trading_mode = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if game.initial_placement_phase: # Tutaj jest ta faza początkowa
                    player_id = game.current_player_idx
                    if game.placement_stage == 0:  # Stawianie wioski
                        node = find_closest_node(event.pos, game.graph.nodes())
                        if node and game.build_settlement(node, player_id, initial_placement=True):
                            game.next_initial_placement()

                    elif game.placement_stage == 1:  # Stawianie drogi
                        edge = find_closest_edge(event.pos, game.graph)
                        if edge and game.build_road(edge[0], edge[1], player_id):
                            game.next_initial_placement()

                else:  # Normalny gameplay, wszystkie funkcjonalności
                    if  game.robber_phase and event.button == 1:  # Lewy przycisk myszy jak można postawić
                        hex = find_closest_hex(event.pos, game.hexes)
                        if hex and hex['resource'] != 'pustynia':  # Nie można postawić na pustyni
                            game.place_robber(hex['position'])

                    elif event.button == 1:  # Left click — wioska
                        node = find_closest_node(event.pos, game.graph.nodes())
                        if node:
                            game.build_settlement(node, game.current_player_idx)

                    elif event.button == 3:  # Right click - droga
                        edge = find_closest_edge(event.pos, game.graph)
                        if edge:
                            game.build_road(edge[0], edge[1], game.current_player_idx)

                    elif event.button == 2:  # Scroll - ulepszenia do miasta
                        node = find_closest_node(event.pos, game.graph.nodes())
                        if node:
                            game.upgrade_to_city(node, game.current_player_idx)

        clock.tick(FPS)

    pygame.quit()
    return game


if __name__ == "__main__":
    final_game_state = main()
