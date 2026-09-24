"""Responsive row layout in a shared 24-column grid, using image coordinates."""
from statistics import median


def reconstruct_rows(components):
    # Form outlines are containers, not visible text widgets.
    containers = [dict(c) for c in components if c['class'] == 'Form']
    items = [dict(c) for c in components if c['class'] != 'Form']
    if not items:
        return {'mode': 'single', 'page': {'width': 0, 'height': 0},
                'rows': [], 'left': [], 'right': [], 'containers': containers}
    min_x = min(c['x1'] for c in items)
    max_x = max(c['x2'] for c in items)
    min_y = min(c['y1'] for c in items)
    max_y = max(c['y2'] for c in items)
    width = max(1, max_x-min_x)
    typical = median(c['y2']-c['y1'] for c in items)
    rows = []
    for c in sorted(items, key=lambda c: (c['y1'], c['x1'])):
        c['pixel_width'] = c['x2']-c['x1']
        c['pixel_height'] = c['y2']-c['y1']
        cy = (c['y1']+c['y2'])/2
        target = None
        for row in rows:
            # Normalised overlap replaces a fixed 24-pixel threshold.
            if all(min(c['y2'], p['y2'])-max(c['y1'], p['y1']) >
                   .35*min(c['pixel_height'], p['pixel_height'])
                   and abs(cy-(p['y1']+p['y2'])/2) < .6*max(c['pixel_height'], p['pixel_height'])
                   and (c['x1'] >= p['x2']-2 or p['x1'] >= c['x2']-2)
                   for p in row['components']):
                target = row
                break
        if target is None:
            rows.append({'components': [c], 'y1': c['y1'], 'y2': c['y2']})
        else:
            target['components'].append(c)
            target['y1'] = min(target['y1'], c['y1'])
            target['y2'] = max(target['y2'], c['y2'])
    rows.sort(key=lambda r: r['y1'])
    previous_bottom = min_y
    for i, row in enumerate(rows):
        row['row'] = i+1
        row['gap_before'] = round(max(0, row['y1']-previous_bottom), 1)
        previous_bottom = max(previous_bottom, row['y2'])
        row['components'].sort(key=lambda c: c['x1'])
        for c in row['components']:
            start = max(1, min(24, round((c['x1']-min_x)/width*24)+1))
            end = max(start+1, min(25, round((c['x2']-min_x)/width*24)+1))
            c['grid_start'], c['grid_span'] = start, end-start
            # A lone centred title/prose can use full width without text wrapping early.
            centered = abs((c['x1']+c['x2'])/2-(min_x+max_x)/2) < width*.07
            c['align'] = 'center' if centered and c['class'] in {'Heading', 'Subheading', 'Paragraph'} else 'left'
            if len(row['components']) == 1 and c['align'] == 'center':
                c['grid_start'], c['grid_span'] = 1, 24
        # Rounding must not introduce overlaps between adjacent grid cells.
        for left, right in zip(row['components'], row['components'][1:]):
            left['grid_span'] = max(1, min(left['grid_span'], right['grid_start']-left['grid_start']))
    return {'mode': 'spatial', 'page': {'width': round(width, 1), 'height': round(max_y-min_y, 1),
                                      'text_height': round(typical, 1)},
            'rows': rows, 'left': rows, 'right': [], 'containers': containers}


# Keep the established row algorithm as the leaf of a small spatial hierarchy.


def _compatible_layout(components):
    result = reconstruct_rows(components)
    items = [c for c in components if c['class'] != 'Form']
    if len(items) < 6:
        return result
    top, bottom = min(c['y1'] for c in items), max(c['y2'] for c in items)
    width = result['page']['width']
    candidates = []
    # Try a full-page gutter, then gutters below a shallow header/title band.
    cuts = [top] + sorted({c['y1'] for c in items if top < c['y1'] < top+(bottom-top)*.3})
    for cut in cuts:
        if any(c['y1'] < cut < c['y2'] for c in items):
            continue
        body = [c for c in items if c['y1'] >= cut]
        intervals = sorted((c['x1'], c['x2']) for c in body)
        occupied = []
        for a, b in intervals:
            if occupied and a <= occupied[-1][1]:
                occupied[-1][1] = max(b, occupied[-1][1])
            else:
                occupied.append([a, b])
        for a, b in zip(occupied, occupied[1:]):
            gap = b[0]-a[1]
            if gap < width*.06:
                continue
            left = [c for c in body if c['x2'] <= a[1]]
            right = [c for c in body if c['x1'] >= b[0]]
            if min(len(left), len(right)) < 3:
                continue
            # Two labels beside two inputs are rows, not enough evidence of columns.
            if any(max(c['y2'] for c in col)-min(c['y1'] for c in col) < (bottom-top)*.3
                   for col in (left, right)):
                continue
            candidates.append((gap, -cut, cut, left, right))
    if not candidates:
        return result
    widest = max(c[0] for c in candidates)
    gap, _, cut, left, right = min((c for c in candidates if c[0] >= widest*.9), key=lambda c: c[2])
    header = [c for c in items if c['y2'] <= cut and c not in left+right]
    columns = []
    body_top = min(c['y1'] for c in left+right)
    for column in (left, right):
        # Bind labels to their fields so responsive reflow cannot detach them.
        labels = {c['for_id']: c for c in column
                  if c['class'] == 'Label' and c.get('for_id')}
        grouped = []
        for c in column:
            if c['class'] == 'Label' and c.get('for_id') and any(
                    f.get('id') == c['for_id'] for f in column):
                continue
            label = labels.get(c.get('id'))
            if label:
                grouped.append({**c, 'class': 'Field', 'y1': label['y1'], 'children': [label, c]})
            else:
                grouped.append(c)
        leaf = reconstruct_rows(grouped)
        leaf['offset_top'] = min(c['y1'] for c in column)-body_top
        columns.append(leaf)
    result.update(mode='columns', columns=columns, column_gap=gap,
                  header=reconstruct_rows(header),
                  body_gap=max(0, body_top-max((c['y2'] for c in header), default=body_top)))
    return result


# The hierarchy is additive: legacy rows/columns remain available to the current
# generator. A later renderer can consume `tree` for nested sections and cards.
CONTAINER_CLASSES = {'Form', 'Card', 'Container', 'Panel', 'Section'}
CONTROL_CLASSES = {'Textbox', 'Password box', 'Textarea', 'Select'}


def _bounds(items):
    return {key: operation(item[key] for item in items)
            for key, operation in [('x1', min), ('y1', min), ('x2', max), ('y2', max)]}


def _area(item):
    return max(0, item['x2']-item['x1'])*max(0, item['y2']-item['y1'])


def _inside(child, parent):
    overlap = max(0, min(child['x2'], parent['x2'])-max(child['x1'], parent['x1']))
    overlap *= max(0, min(child['y2'], parent['y2'])-max(child['y1'], parent['y1']))
    return _area(parent) > _area(child)*1.05 and overlap/max(1, _area(child)) >= .95


def _group(kind, children, **extra):
    node = {'kind': kind, 'children': children, **extra}
    node.update(_bounds(children) if children else dict(x1=0, y1=0, x2=0, y2=0))
    return node


def _axis_groups(nodes, axis):
    """Connected intervals; unlike centre clustering, no box crosses a cut."""
    groups = []
    end = None
    for node in sorted(nodes, key=lambda n: (n[axis+'1'], n[axis+'2'])):
        if end is None or node[axis+'1'] > end:
            groups.append([node])
            end = node[axis+'2']
        else:
            groups[-1].append(node)
            end = max(end, node[axis+'2'])
    return groups


def _column_groups(nodes):
    if len(nodes) < 2:
        return []
    bounds = _bounds(nodes)
    width = max(1, bounds['x2']-bounds['x1'])
    height = max(1, bounds['y2']-bounds['y1'])
    groups = _axis_groups(nodes, 'x')
    # Small gaps inside a row are not evidence of independent columns.
    merged = []
    for group in groups:
        if merged and _bounds(group)['x1']-_bounds(merged[-1])['x2'] < width*.04:
            merged[-1].extend(group)
        else:
            merged.append(list(group))
    if len(merged) < 2:
        return []
    for group in merged:
        b = _bounds(group)
        substantial_single = len(group) == 1 and (
            group[0]['kind'] == 'container' or
            (group[0].get('component', {}).get('class') in {'Image', 'Carousel'}
             and b['y2']-b['y1'] >= height*.3))
        if len(group) < 2 and not substantial_single:
            return []
        if b['y2']-b['y1'] < height*.3 or b['x2']-b['x1'] < width*.08:
            return []
    return merged


def _spatial_tree(nodes, depth=0):
    nodes = sorted(nodes, key=lambda n: (n['y1'], n['x1']))
    if not nodes:
        return _group('stack', [])
    if len(nodes) == 1:
        return nodes[0]
    if depth >= 12:
        return _group('stack', nodes, reason='Recursion limit; geometry retained.')

    # A common horizontal band is a row, even when it contains three buttons.
    common = min(n['y2'] for n in nodes)-max(n['y1'] for n in nodes)
    disjoint = len(_axis_groups(nodes, 'x')) == len(nodes)
    if disjoint and common >= .35*min(n['y2']-n['y1'] for n in nodes):
        children = sorted(nodes, key=lambda n: n['x1'])
        classes = [n.get('component', {}).get('class') for n in children]
        role = 'button-group' if all(c == 'Button' for c in classes) else 'row'
        return _group('row', children, role=role)

    columns = _column_groups(nodes)
    if columns:
        children = [_spatial_tree(group, depth+1) for group in columns]
        return _group('columns', children,
                      widths=[c['x2']-c['x1'] for c in children],
                      gaps=[b['x1']-a['x2'] for a, b in zip(children, children[1:])])

    # A spanning header/footer blocks a vertical cut. Isolate horizontal bands
    # only where no component crosses the boundary, then examine each section.
    bands = _axis_groups(nodes, 'y')
    for index in range(1, len(bands)):
        before = [n for band in bands[:index] for n in band]
        after = [n for band in bands[index:] for n in band]
        if _column_groups(before) or _column_groups(after):
            return _group('stack', [_spatial_tree(before, depth+1),
                                    _spatial_tree(after, depth+1)])
    if len(bands) > 1:
        children = [_spatial_tree(band, depth+1) for band in bands]
        return _group('stack', children,
                      gaps=[b['y1']-a['y2'] for a, b in zip(children, children[1:])])

    # Ambiguous overlapping boxes are retained, not silently discarded.
    return _group('stack', nodes, reason='No unambiguous whitespace cut.')


def _hierarchy(components):
    leaves = []
    for index, component in enumerate(components):
        c = dict(component)
        leaves.append({'kind': 'component', 'component': c, 'index': index,
                       **{key: c[key] for key in ('x1', 'y1', 'x2', 'y2')}})

    # Only explicit, mapped label associations form atomic fields.
    # Missing IDs must never make unrelated labels and controls match.
    used = set()
    grouped = []
    for node in leaves:
        c = node['component']
        if c['class'] not in CONTROL_CLASSES or not c.get('id'):
            continue
        labels = [n for n in leaves if n['component']['class'] == 'Label'
                  and n['component'].get('for_id') == c['id']]
        if labels:
            children = sorted(labels, key=lambda n: (n['y1'], n['x1']))+[node]
            grouped.append(_group('field', children))
            used.update(n['index'] for n in children)
    grouped.extend(n for n in leaves if n['index'] not in used)

    # Assign each node to its smallest explicit enclosing container.
    containers = [n for n in grouped
                  if n.get('component', {}).get('class') in CONTAINER_CLASSES]
    parents = {}
    for index, node in enumerate(grouped):
        choices = [parent for parent in containers if _inside(node, parent)]
        if choices:
            parents[index] = min(choices, key=_area)['index']

    def expand(node, depth=0):
        if node not in containers or depth >= 12:
            return node
        children = [expand(child, depth+1) for i, child in enumerate(grouped)
                    if parents.get(i) == node['index']]
        return {**node, 'kind': 'container',
                'children': [_spatial_tree(children)],
                'container_class': node['component']['class']}

    roots = [expand(node) for index, node in enumerate(grouped) if index not in parents]
    return _spatial_tree(roots)


def reconstruct_layout(components):
    """Preserve the current rendering contract and expose a richer hierarchy.

    `tree` records nested containers, fields, rows, columns and vertical sections.
    Existing `mode`, `rows`, `header`, `columns`, `left` and `right` keep working.
    No OCR wording is used to choose a layout.
    """
    result = _compatible_layout(components)
    result['tree'] = _hierarchy(components)
    result['tree_version'] = 1
    return result
