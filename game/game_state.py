import random
import networkx as nx
from collections import defaultdict
from .constants import PLAYER_COLORS
from .enums import BuildingType

class GameState:
    def __init__(self):
        self.graph = nx.Graph()
        self.players = []
        self.current_player_idx = 0
        self.hexes = []
        self.initial_placement_phase = True
        self.initial_placement_order = []  # np. [1,2,3,4,4,3,2,1] jak w Catanie
        self.placement_stage = 0  # 0 = settlement, 1 = road
        self.initial_placement_complete = False # Czy faza jest skończona
        self.diceroll = None
        self.robber_position = None # Pozycja tegop hexa, na którym jest złodziej
        self.robber_phase = False # Dodatkowa flaga
        self.robber_hex = None  # To jest hex, na którym jest aktualnie złodziej
        self.longest_road_length = 4
        self.trading_mode = False
        self.trade_stage = 0  # 0 wybieramy zasób który chcemy, 1 - zasób które chcemy wymienić
        self.selected_trade_resource = None

    def add_player(self):
        player_id = len(self.players)
        self.players.append({
            'id': player_id,
            'color': PLAYER_COLORS[player_id % len(PLAYER_COLORS)],
            'resources': defaultdict(int),
            'victory_points': 0,
            'longest_road': False
        })
        return player_id

    def start_initial_placement(self):
        self.initial_placement_order = (
                [i for i in range(len(self.players))] +  # 0,1,2,3
                [i for i in reversed(range(len(self.players)))]  # 3,2,1,0
        )
        self.current_player_idx = self.initial_placement_order.pop(0)

    def next_initial_placement(self):
        if self.placement_stage == 0:
            # Just placed a settlement, now place a road
            self.placement_stage = 1
        else:
            # Just placed a road
            if not self.initial_placement_order:
                # No more players left, but wait until road is placed
                self.initial_placement_phase = False
                self.placement_stage = 0
            else:
                # Move to next player's settlement
                self.placement_stage = 0
                self.current_player_idx = self.initial_placement_order.pop(0)

    def get_current_player(self):
        return self.players[self.current_player_idx]

    def next_turn(self):
        if not self.initial_placement_phase:
            dice_roll = self.roll_dice()
            print(f"Gracz {self.current_player_idx + 1} wyrzucił: {dice_roll}")
            if dice_roll == 7: # Jak się wyrzuciło 7 to jeszcze nie idź do następnego gracza
                self.handle_robber()
                return
            else:
                self.distribute_resources(dice_roll)

        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    def build_settlement(self, node_id, player_id, initial_placement=False):
        if node_id not in self.graph.nodes:
            return False

        if not initial_placement and not self.can_afford_settlement(player_id):
            print("Nie stać cię na wioskę biedaku")
            return False

        # Inne zasady dla fazy początkowej
        if initial_placement:
            if self.graph.nodes[node_id]['owner'] is not None:
                return False
            for neighbor in self.graph.neighbors(node_id):
                if self.graph.nodes[neighbor]['owner'] is not None:
                    return False
        else:
            # Normal rules - check distance and adjacent settlements
            if self.graph.nodes[node_id]['owner'] is not None:
                return False
            for neighbor in self.graph.neighbors(node_id):
                if self.graph.nodes[neighbor]['owner'] is not None:
                    return False

        self.graph.nodes[node_id].update({
            'owner': player_id,
            'building': BuildingType.SETTLEMENT
        })
        self.players[player_id]['victory_points'] += 1

        # W fazie początkowej dostaje się zasoby tam gdzie postawisz osadę
        if initial_placement:
            for hex_data in self.hexes:
                if node_id in hex_data['vertices'] and hex_data['resource'] != 'pustynia':
                    resource = hex_data['resource']
                    if resource != 'pustynia':  # Double-check to exclude desert
                        self.players[player_id]['resources'][resource] += 1

        if not initial_placement:
            self.players[player_id]['resources']['drewno'] -= 1
            self.players[player_id]['resources']['glina'] -= 1
            self.players[player_id]['resources']['owca'] -= 1
            self.players[player_id]['resources']['zboze'] -= 1
            # Wywala się puste zasoby
            for res in ['drewno', 'glina', 'owca', 'zboze']:
                if self.players[player_id]['resources'].get(res, 0) == 0:
                    del self.players[player_id]['resources'][res]

        return True

    def build_road(self, u, v, player_id):
        if not self.graph.has_edge(u, v):
            return False

        # Check if player can afford the road first (unless in initial placement)
        if not self.initial_placement_phase and not self.can_afford_road(player_id):
            print("Nie stać cię na drogę biedaku")
            return False

        # Sprawdzenie, czy droga należy do kogoś
        if self.graph.edges[u, v]['owner'] is not None:
            return False

        # Sprawdzenie, czy jest wioska/miasto przynależne, bo wtedy możemy budować
        if self.graph.nodes[u]['owner'] == player_id or self.graph.nodes[v]['owner'] == player_id:
            # Deduct resources first (unless in initial placement)
            if not self.initial_placement_phase:
                self.players[player_id]['resources']['drewno'] -= 1
                self.players[player_id]['resources']['glina'] -= 1
                # Remove resource keys if count reaches 0
                if self.players[player_id]['resources']['drewno'] == 0:
                    del self.players[player_id]['resources']['drewno']
                if self.players[player_id]['resources']['glina'] == 0:
                    del self.players[player_id]['resources']['glina']

            self.graph.edges[u, v]['owner'] = player_id
            self.update_longest_road_card()
            return True

        # Sprawdzenie czy jest połączenie drogowe, nie wiem zrobił to, jakimś DFS
        # We need to find if there's a path from this edge to any of player's roads
        # through other player's roads
        temp_graph = self.graph.copy()

        # Temporarily add this road to check connectivity
        temp_graph.edges[u, v]['owner'] = player_id

        # Get all player's roads
        player_roads = [(x, y) for x, y, data in temp_graph.edges(data=True)
                        if data['owner'] == player_id]

        # Check if this new road connects to any existing road
        for road in player_roads:
            if road == (u, v):  # Skip the current road we're adding
                continue

            # Check if connected through roads (BFS)
            visited = set()
            queue = []
            start_node = u if u in road else (v if v in road else None)

            if start_node is not None:
                queue.append(start_node)
                visited.add(start_node)

                while queue:
                    current = queue.pop(0)

                    for neighbor in temp_graph.neighbors(current):
                        if neighbor not in visited:
                            edge_data = temp_graph.edges[current, neighbor]
                            # Only traverse through player's roads
                            if edge_data['owner'] == player_id:
                                if neighbor in road:
                                    # Deduct resources first (unless in initial placement)
                                    if not self.initial_placement_phase:
                                        self.players[player_id]['resources']['drewno'] -= 1
                                        self.players[player_id]['resources']['glina'] -= 1
                                        # Remove resource keys if count reaches 0
                                        if self.players[player_id]['resources']['drewno'] == 0:
                                            del self.players[player_id]['resources']['drewno']
                                        if self.players[player_id]['resources']['glina'] == 0:
                                            del self.players[player_id]['resources']['glina']

                                    self.graph.edges[u, v]['owner'] = player_id
                                    self.update_longest_road_card()
                                    return True
                                visited.add(neighbor)
                                queue.append(neighbor)
        return False

    def upgrade_to_city(self, node_id, player_id):
        if (node_id not in self.graph.nodes or
                self.graph.nodes[node_id]['owner'] != player_id or
                self.graph.nodes[node_id]['building'] != BuildingType.SETTLEMENT):
            return False

        if not self.can_afford_city(player_id):
            print("Nie stać cię na miasto biedaku!")
            return False

        self.graph.nodes[node_id]['building'] = BuildingType.CITY
        self.players[player_id]['victory_points'] += 1  # Dodajemy jeden punkt za ulepsczenie wioska -> miasto

        # Deduct resources
        self.players[player_id]['resources']['zboze'] -= 2
        self.players[player_id]['resources']['kamień'] -= 3
        # Clean up empty resources
        for res in ['zboze', 'kamień']:
            if self.players[player_id]['resources'].get(res, 0) == 0:
                del self.players[player_id]['resources'][res]
        return True

    def roll_dice(self):
        dice_1 = random.randint(1, 6)
        dice_2 = random.randint(1, 6)

        self.diceroll = dice_1 + dice_2
        return self.diceroll

    def distribute_resources(self, dice_roll):
        if dice_roll == 7:
            self.handle_robber()
            return

        for hex_data in self.hexes:
            if hex_data['resource'] == 'pustynia' or hex_data['token'] is None:
                continue

            # Sprawdzenie numerków pól, czy są takie same jak na kości
            if hex_data['token'] == dice_roll:

                # Blokujemy hexa złodziejem
                if self.robber_hex and self.robber_hex['position'] == hex_data['position']:
                    continue

                # Sprawdzenie wszystkich miast należacych to tego jebanego plastra miodu
                for vertex in hex_data['vertices']:
                    if vertex in self.graph.nodes:
                        node_data = self.graph.nodes[vertex]
                        if node_data['owner'] is not None:
                            player_id = node_data['owner']
                            # Dodajemy zasoby, miasto daje +2 a wioska +1
                            if node_data['building'] == BuildingType.SETTLEMENT:
                                self.players[player_id]['resources'][hex_data['resource']] += 1
                            elif node_data['building'] == BuildingType.CITY:
                                self.players[player_id]['resources'][hex_data['resource']] += 2

    def handle_robber(self):
        """Kieddy jest wyrzucone 7 to jak się ma więcej niż 7 zasobów to traci się mniejszą połowę, na razie losowo"""
        print("Wyrzucił się złodziej, trzeba to zrobić")
        for player in self.players:
            total_resources = sum(player['resources'].values())
            if total_resources > 7:
                discard_count = total_resources // 2
                print(f"Player {player['id'] + 1} must discard {discard_count} resources")

                resources = []
                for resource, count in player['resources'].items():
                    resources.extend([resource] * count)

                random.shuffle(resources)
                for resource in resources[:discard_count]:
                    player['resources'][resource] -= 1
                    if player['resources'][resource] == 0:
                        del player['resources'][resource]
        # Tutaj wchodzimy do fazy gdzie stawiamy złodzieja
        self.robber_phase = True
        print("Wybierz pole gdzie chcesz postawić złodzieja")

    def place_robber(self, hex_pos):
        """ Tam gdzie stawiamy złodzieja to wybieramy losowy surowiec od losowego gracza"""
        if not self.robber_phase:
            return False

        # Znajdz pozycje tego hexa
        target_hex = None
        for hex_data in self.hexes:
            if hex_data['position'] == hex_pos:
                target_hex = hex_data
                break

        if not target_hex or target_hex == self.robber_hex:
            return False

        # Zmieniamy pozycję starego złodzieja
        self.robber_hex = target_hex
        self.robber_phase = False

        # Szukamy graczy którzy mają wioskę/miasto przy tym polu
        adjacent_players = set()
        for vertex in target_hex['vertices']:
            if vertex in self.graph.nodes:
                node_data = self.graph.nodes[vertex]
                if (node_data['owner'] is not None and
                        node_data['owner'] != self.current_player_idx and
                        node_data['building'] != BuildingType.NONE):
                    adjacent_players.add(node_data['owner'])

        # Tutaj kradniemy zasoby
        if adjacent_players:
            victim_id = random.choice(list(adjacent_players))
            self.steal_resource(victim_id)

        # Dopiero po postawieniu i ukradnięciu idziemy do następnego gracza
        self.robber_phase = False
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return True

    def steal_resource(self, victim_id):
        """Tutaj jest ta kradzież tych surowców"""
        victim = self.players[victim_id]
        thief = self.players[self.current_player_idx]

        resources = []
        for resource, count in victim['resources'].items():
            resources.extend([resource] * count)

        if resources:
            stolen_resource = random.choice(resources)
            victim['resources'][stolen_resource] -= 1
            thief['resources'][stolen_resource] += 1

            if victim['resources'][stolen_resource] == 0:
                del victim['resources'][stolen_resource]

            print(f"Gracz {thief['id'] + 1} ukradł 1 {stolen_resource} od Gracza {victim['id'] + 1}")

    def can_afford_road(self, player_id):
        """Sprawdzamy, czy stać na drogę, u mnie jedno drewno i jedna glina """
        player = self.players[player_id]
        return (player['resources'].get('drewno', 0) >= 1 and
                player['resources'].get('glina', 0) >= 1)

    def can_afford_settlement(self, player_id):
        """Sprawdzamy, czy stać na wioskę, u mnie po jednym ze wszystkiego oprócz kamienia"""
        player = self.players[player_id]
        return (player['resources'].get('drewno', 0) >= 1 and
                player['resources'].get('glina', 0) >= 1 and
                player['resources'].get('owca', 0) >= 1 and
                player['resources'].get('zboze', 0) >= 1)

    def can_afford_city(self, player_id):
        """Sprawdzamy, czy stać na ulepszenie wioski na miasto"""
        player = self.players[player_id]
        return (player['resources'].get('zboze', 0) >= 2 and
                player['resources'].get('kamień', 0) >= 3)

    def calculate_longest_roads(self):
        """Liczenie najdłuższej drogi dla każdego gracza"""
        player_longest_roads = defaultdict(int)

        for player_id in range(len(self.players)):
            # Wszystkie drogi należące do tego gracza
            player_roads = [(u, v) for u, v, data in self.graph.edges(data=True)
                            if data['owner'] == player_id]

            if not player_roads:
                continue

            # Tworzenie supgrafu dla tylko tego gracza
            road_graph = nx.Graph()
            road_graph.add_edges_from(player_roads)

            # Znalezienie najdłuższej drogi w tym supgrafie
            longest = 0
            # Trzeba sprawdzić każdy punkt początkowy
            for component in nx.connected_components(road_graph):
                subgraph = road_graph.subgraph(component)
                # Dla każdego połączonej drogi sprawdź
                for node in subgraph.nodes():
                    path_length = self._longest_path_from_node(subgraph, node)
                    if path_length > longest:
                        longest = path_length

            player_longest_roads[player_id] = longest

        return player_longest_roads

    def _longest_path_from_node(self, graph, start_node, visited=None):
        """Funkcja pomocnicza, która szuka najdłuższej drogi za pomocą DFS"""
        if visited is None:
            visited = set()

        max_length = 0
        visited.add(start_node)

        for neighbor in graph.neighbors(start_node):
            if neighbor not in visited:
                length = 1 + self._longest_path_from_node(graph, neighbor, visited.copy())
                if length > max_length:
                    max_length = length

        return max_length

    def update_longest_road_card(self):
        longest_roads = self.calculate_longest_roads()
        current_max = 0
        current_holder = None

        # Szukaj gracza, który ma najdłuższą drogę (ma być minimum 5 połączonych dróg)
        for player_id, length in longest_roads.items():
            if length >= 5 and length > current_max:
                current_max = length
                current_holder = player_id
            elif length == current_max and current_holder is not None:
                # Jak jest remis to zostaje ten wcześniejszy, trzeba przebić
                pass

        # Update tego gracza
        for player in self.players:
            if 'longest_road' in player and player['longest_road']:
                player['longest_road'] = False
                player['victory_points'] -= 2  # Trzeba zabrać te punkty, jak się straciło

        if current_holder is not None:
            self.players[current_holder]['longest_road'] = True
            self.players[current_holder]['victory_points'] += 2  # Dodaj nowe punkty
            print(f'Gracz {current_holder + 1}: ma najdłuższą drogę : {current_max}')

    def trade_with_bank(self, player_id, give_resource, take_resource):
        """Wymieniamy 4 czegoś na 1 czegoś"""
        player = self.players[player_id]

        # Trzeba sprawdzić czy gracz ma co najmniej 4 zasoby
        if player['resources'].get(give_resource, 0) < 4:
            print(f"Nie masz wystarczająco {give_resource} (potrzeba 4)")
            return False

        # Robimy ten trade
        player['resources'][give_resource] -= 4
        if player['resources'][give_resource] == 0:
            del player['resources'][give_resource]

        player['resources'][take_resource] = player['resources'].get(take_resource, 0) + 1

        print(f"Gracz {player_id + 1} wymienił 4 {give_resource} na 1 {take_resource}")
        return True


    def to_qubo_input(self):
        """Na razie takie coś, zobaczymy czy się nada, ale raczej do zmiany"""
        return {
            'graph': nx.node_link_data(self.graph),
            'players': self.players,
            'current_player': self.current_player_idx,
            'hexes': self.hexes
        }
