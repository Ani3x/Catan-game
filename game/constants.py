
PLAYERS_NUMBERS = 2
WIDTH, HEIGHT = 1300, 800
HEX_SIZE = 60
FPS = 30
VERTEX_RADIUS = 7
ROAD_WIDTH = 5

PLAYER_COLORS = [
    (255, 0, 0),    # Czerwony
    (0, 0, 255),    # Niebieski
    (255, 255, 0),  # Żółty
    (0, 255, 0),    # Zielony
]

RESOURCE_COLORS = {
    'drewno': (34, 139, 34),
    'glina': (178, 34, 34),
    'zboze': (218, 165, 32),
    'owca': (144, 238, 144),
    'kamień': (105, 105, 105),
    'pustynia': (238, 232, 170)
}

RESOURCES = ['drewno'] * 4 + ['glina'] * 3 + ['zboze'] * 4 + ['owca'] * 4 + ['kamień'] * 3 + ['pustynia']
TOKENS = [2, 3, 3, 4, 4, 5, 5, 6, 6,
          8, 8, 9, 9, 10, 10, 11, 11, 12]