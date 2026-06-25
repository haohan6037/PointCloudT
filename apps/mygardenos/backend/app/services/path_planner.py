import math


def rotate_point(point: dict, angle_degrees: float) -> dict:
    angle = math.radians(angle_degrees)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    x = float(point["x"])
    y = float(point["y"])
    return {"x": (x * cos_a) - (y * sin_a), "y": (x * sin_a) + (y * cos_a)}


def line_polygon_intervals(polygon: list[dict], y: float) -> list[tuple[float, float]]:
    intersections = []
    for index, point in enumerate(polygon):
        next_point = polygon[(index + 1) % len(polygon)]
        y1 = float(point["y"])
        y2 = float(next_point["y"])
        if y1 == y2:
            continue
        if y >= min(y1, y2) and y < max(y1, y2):
            x1 = float(point["x"])
            x2 = float(next_point["x"])
            ratio = (y - y1) / (y2 - y1)
            intersections.append(x1 + (ratio * (x2 - x1)))
    intersections.sort()
    intervals = []
    for index in range(0, len(intersections) - 1, 2):
        start = intersections[index]
        end = intersections[index + 1]
        if end - start > 0.001:
            intervals.append((start, end))
    return intervals


def subtract_intervals(intervals: list[tuple[float, float]], blockers: list[tuple[float, float]]) -> list[tuple[float, float]]:
    remaining = intervals
    for block_start, block_end in blockers:
        next_remaining = []
        for start, end in remaining:
            if block_end <= start or block_start >= end:
                next_remaining.append((start, end))
                continue
            if block_start > start:
                next_remaining.append((start, block_start))
            if block_end < end:
                next_remaining.append((block_end, end))
        remaining = next_remaining
    return [(start, end) for start, end in remaining if end - start > 0.001]


def estimate_path_distance(points: list[dict]) -> float:
    distance = 0.0
    for index in range(1, len(points)):
        previous = points[index - 1]
        current = points[index]
        distance += math.dist((float(previous["x"]), float(previous["y"])), (float(current["x"]), float(current["y"])))
    return round(distance, 3)


def generate_parallel_path_points(
    work_polygon: list[dict],
    no_go_polygons: list[list[dict]],
    blade_width: float,
    overlap_ratio: float,
    path_angle: float,
) -> list[dict]:
    spacing = blade_width * (1 - overlap_ratio)
    if spacing <= 0:
        raise ValueError("blade_width and overlap_ratio produce invalid path spacing")

    rotated_work = [rotate_point(point, -path_angle) for point in work_polygon]
    rotated_no_go = [[rotate_point(point, -path_angle) for point in polygon] for polygon in no_go_polygons]
    min_y = min(point["y"] for point in rotated_work)
    max_y = max(point["y"] for point in rotated_work)
    if max_y - min_y <= 0:
        raise ValueError("Work zone polygon has no usable height")

    y_values = []
    y = min_y + (spacing / 2)
    while y < max_y:
        y_values.append(y)
        y += spacing
    if not y_values:
        y_values = [(min_y + max_y) / 2]

    path_points = []
    reverse_segment = False
    for y_value in y_values:
        intervals = line_polygon_intervals(rotated_work, y_value)
        blockers = []
        for polygon in rotated_no_go:
            blockers.extend(line_polygon_intervals(polygon, y_value))
        clear_intervals = subtract_intervals(intervals, blockers)
        for start_x, end_x in clear_intervals:
            segment = [{"x": start_x, "y": y_value}, {"x": end_x, "y": y_value}]
            if reverse_segment:
                segment.reverse()
            path_points.extend(rotate_point(point, path_angle) for point in segment)
            reverse_segment = not reverse_segment

    return [{"x": round(point["x"], 3), "y": round(point["y"], 3)} for point in path_points]
