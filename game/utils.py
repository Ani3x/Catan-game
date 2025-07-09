import math


def get_hex_positions(center_x, center_y, size):
    rows = [3, 4, 5, 4, 3]
    positions = []
    dx = size * 3 ** 0.5
    dy = size * 1.5
    y = center_y - 2 * dy
    for i, count in enumerate(rows):
        x = center_x - dx * (count - 1) / 2
        for _ in range(count):
            positions.append((x, y))
            x += dx
        y += dy
    return positions


def rounded_pos(pos):
    return (round(pos[0]), round(pos[1]))


def find_closest_node(pos, nodes, threshold=20):
    mx, my = pos
    closest = None
    min_dist = float('inf')
    for node in nodes:
        nx, ny = node
        dist = math.hypot(mx - nx, my - ny)
        if dist < min_dist and dist < threshold:
            min_dist = dist
            closest = node
    return closest


def find_closest_hex(pos, hexes, threshold=50):
    mx, my = pos
    closest_hex = None
    min_dist = float('inf')
    for hex_data in hexes:
        hx, hy = hex_data['position']
        dist = math.hypot(mx - hx, my - hy)
        if dist < min_dist and dist < threshold:
            min_dist = dist
            closest_hex = hex_data
    return closest_hex


def find_closest_edge(pos, graph, threshold=15):
    mx, my = pos
    closest_edge = None
    min_dist = float('inf')
    for u, v in graph.edges():
        x1, y1 = u
        x2, y2 = v
        A = y2 - y1
        B = x1 - x2
        C = x2 * y1 - x1 * y2
        dist = abs(A * mx + B * my + C) / math.hypot(A, B)
        segment_length = math.hypot(x2 - x1, y2 - y1)
        dot_product = ((mx - x1) * (x2 - x1) + (my - y1) * (y2 - y1)) / (segment_length ** 2)
        if 0 <= dot_product <= 1 and dist < min_dist and dist < threshold:
            min_dist = dist
            closest_edge = (u, v)
    return closest_edge
