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


def _adjacent_panels(nodes):
    """Tolerate slight outline overlap between independent sibling panels."""
    if len(nodes) < 2 or not all(n['kind'] == 'container' for n in nodes):
        return []
    ordered = sorted(nodes, key=lambda n: n['x1'])
    for a, b in zip(ordered, ordered[1:]):
        width = min(a['x2']-a['x1'], b['x2']-b['x1'])
        height = min(a['y2']-a['y1'], b['y2']-b['y1'])
        overlap = min(a['y2'], b['y2'])-max(a['y1'], b['y1'])
        if (width <= 0 or height <= 0 or overlap < .7*height
                or not -.06*width <= b['x1']-a['x2'] <= .04*width):
            return []
    return [[n] for n in ordered]


def _horizontal_fields(nodes):
    """Keep repeated left-caption/control pairs atomic before column cuts."""
    pairs = []
    used = set()
    for control in nodes:
        c = control.get('component', {})
        if control['kind'] != 'component' or c.get('class') not in CONTROL_CLASSES:
            continue
        height = max(1, control['y2']-control['y1'])
        labels = [n for n in nodes if n['kind'] == 'component'
                  and n.get('component', {}).get('class') in {'Label', 'Paragraph'}
                  and n.get('component', {}).get('texts')
                  and 0 <= control['x1']-n['x2'] <= 3*height
                  and n['x2']-n['x1'] <= .6*(control['x2']-control['x1'])
                  and min(n['y2'], control['y2'])-max(n['y1'], control['y1'])
                      >= .7*(n['y2']-n['y1'])]
        if len(labels) == 1:
            pairs.append((labels[0], control))
    accepted = []
    for label, control in pairs:
        h = max(1, control['y2']-control['y1'])
        peers = [(a, b) for a, b in pairs if b is not control
                 and abs(b['x1']-control['x1']) <= .3*h
                 and abs(a['x1']-label['x1']) <= .3*h
                 and abs(b['y1']-control['y1']) >= h]
        if peers and id(label) not in used and id(control) not in used:
            accepted.append(_group('row', [label, control], role='form-row'))
            used.update((id(label), id(control)))
    return [n for n in nodes if id(n) not in used]+accepted


def _column_groups(nodes):
    if len(nodes) < 2:
        return []
    bounds = _bounds(nodes)
    width = max(1, bounds['x2']-bounds['x1'])
    height = max(1, bounds['y2']-bounds['y1'])
    panels = _adjacent_panels(nodes)
    if panels:
        return panels
    groups = _axis_groups(nodes, 'x')
    # A persistent narrow gutter can separate dense panels. Require both
    # sides to span most of the region, with several items and substantial width.
    if len(groups) == 2 and all(
            len(g) >= 3 and _bounds(g)['y2']-_bounds(g)['y1'] >= height*.75
            and _bounds(g)['x2']-_bounds(g)['x1'] >= width*.25 for g in groups):
        return groups
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


def _join_text_runs(nodes):
    """Join adjacent OCR fragments on one baseline, tolerating tilted boxes.

    Keep links, labels and controls separate. No text is inferred or rewritten.
    This runs after parent assignment, so it cannot merge across containers.
    """
    groups = []
    for node in sorted(nodes, key=lambda n: (n['y1'], n['x1'])):
        c = node.get('component', {})
        if node['kind'] != 'component' or c.get('class') not in {'Paragraph', 'Heading', 'Subheading'}:
            groups.append([node])
            continue
        target = None
        for group in groups:
            if any(p['kind'] != 'component' or
                   p.get('component', {}).get('class') != c['class'] for p in group):
                continue
            def same_line(p):
                h = min(node['y2']-node['y1'], p['y2']-p['y1'])
                overlap = min(node['y2'], p['y2'])-max(node['y1'], p['y1'])
                gap = max(node['x1'], p['x1'])-min(node['x2'], p['x2'])
                return (h > 0 and overlap >= h*.5 and gap >= -h*.15
                        and abs(node['y1']+node['y2']-p['y1']-p['y2'])/2 < h*.6)
            if all(same_line(p) for p in group) and any(
                    max(node['x1'], p['x1'])-min(node['x2'], p['x2'])
                    <= 1.5*min(node['y2']-node['y1'], p['y2']-p['y1']) for p in group):
                target = group
                break
        if target is None:
            groups.append([node])
        else:
            target.append(node)
    result = []
    for group in groups:
        if len(group) == 1:
            result.append(group[0])
            continue
        group.sort(key=lambda n: n['x1'])
        bounds = _bounds(group)
        component = {**group[0]['component'], **bounds,
                     'texts': [t for n in group for t in n['component'].get('texts', [])],
                     'ocr': [o for n in group for o in n['component'].get('ocr', [])]}
        result.append({**group[0], **bounds, 'component': component})
    return result


def _panel_list_rows(nodes):
    """Prefer paired rows in a text panel when repeated baselines support them.

    This is scoped to explicit panels, not general two-column page sections.
    A single leading caption may sit above the list.
    """
    if len(nodes) < 6 or any(n['kind'] != 'component' or
            n.get('component', {}).get('class') not in
            {'Paragraph', 'Subheading', 'Heading', 'Link'} for n in nodes):
        return None
    rows = []
    for node in sorted(nodes, key=lambda n: (n['y1']+n['y2'])/2):
        cy = (node['y1']+node['y2'])/2
        target = next((row for row in rows if all(
            abs(cy-(p['y1']+p['y2'])/2) < .6*min(node['y2']-node['y1'], p['y2']-p['y1'])
            and (node['x1'] >= p['x2'] or p['x1'] >= node['x2']) for p in row)), None)
        if target is None:
            rows.append([node])
        else:
            target.append(node)
    caption = rows[:1] if len(rows[0]) == 1 else []
    pairs = rows[len(caption):]
    if len(pairs) < 3 or any(len(row) != 2 for row in pairs):
        return None
    for row in pairs:
        row.sort(key=lambda n: n['x1'])
    height = median(n['y2']-n['y1'] for row in pairs for n in row)
    if (max(row[0]['x1'] for row in pairs)-min(row[0]['x1'] for row in pairs) > height
            or max(row[1]['x2'] for row in pairs)-min(row[1]['x2'] for row in pairs) > height):
        return None
    left = _bounds([row[0] for row in pairs])
    right = _bounds([row[1] for row in pairs])
    if right['x1']-left['x2'] < height*2:
        return None
    children = list(caption[0]) if caption else []
    if children:
        title = children[0]
        component = title['component']
        # A separate leading caption above repeated rows is a section title.
        # Links and existing heading levels keep their original semantics.
        if (component['class'] == 'Paragraph'
                and title['y2'] <= min(n['y1'] for n in pairs[0])
                and title['y2']-title['y1'] >= height
                and len(' '.join(component.get('texts', [])).split()) <= 8):
            children[0] = {**title, 'component': {
                **component, 'class': 'Subheading',
                'corrections': component.get('corrections', []) +
                    ['Separate leading caption above aligned panel rows.']}}
    for row in pairs:
        # Shared track widths keep all descriptions and trailing values aligned.
        # Only layout boxes change; component/OCR evidence remains untouched.
        aligned = [{**n, 'x1': bounds['x1'], 'x2': bounds['x2']}
                   for n, bounds in zip(row, (left, right))]
        children.append(_group('row', aligned, role='list-row'))
    return _group('stack', children, role='list')


def _content_titles(nodes, card=False):
    """Recover local text hierarchy after OCR fragments have been joined.

    Restrict this to caption/description cards (optionally with artwork above
    the caption), or a caption immediately above a repeated card row.
    """
    lines = _join_text_runs(nodes)
    text = [n for n in lines if n.get('kind') == 'component'
            and n.get('component', {}).get('class') in
                {'Paragraph', 'Heading', 'Subheading'}]
    artwork = [n for n in lines if n.get('kind') == 'component'
               and n.get('component', {}).get('class') == 'Image']
    if card and len(text)+len(artwork) == len(lines) and len(text) >= 3:
        captions = [n for n in text if any(ch.isalpha() for ch in
                    ' '.join(n['component'].get('texts', [])))]
        captions.sort(key=lambda n: n['y1'])
        if len(captions) >= 3:
            title, body = captions[0], captions[1:]
            h = title['y2']-title['y1']
            body_height = median(n['y2']-n['y1'] for n in body)
            if (all(n['y2'] <= title['y1'] for n in artwork)
                    and title['component']['class'] == 'Paragraph'
                    and h >= body_height*1.12
                    and len(' '.join(title['component'].get('texts', [])).split()) <= 8
                    and all(n['y1'] >= title['y1']+h*.6 for n in body)):
                title['component'] = {**title['component'], 'class': 'Subheading',
                    'corrections': title['component'].get('corrections', []) +
                        ['Larger leading caption above card description lines.']}
    cards = [n for n in lines if n.get('kind') == 'container'
             and n.get('container_class') == 'Card']
    if len(cards) >= 3:
        h = median(n['y2']-n['y1'] for n in cards)
        top = min(n['y1'] for n in cards)
        if max(n['y1'] for n in cards)-top <= h*.15:
            left, right = min(n['x1'] for n in cards), max(n['x2'] for n in cards)
            above = [n for n in text if n['y2'] <= top and top-n['y2'] < h*.7
                     and abs((n['x1']+n['x2']-left-right)/2) < (right-left)*.12]
            above.sort(key=lambda n: n['y1'])
            if len(above) == 2:
                title, subtitle = above
                if (title['component']['class'] == 'Paragraph'
                        and title['y2']-title['y1'] >=
                            (subtitle['y2']-subtitle['y1'])*1.35):
                    title['component'] = {**title['component'], 'class': 'Subheading',
                        'corrections': title['component'].get('corrections', []) +
                            ['Larger centered caption above repeated cards.']}
    return lines


def _container_rows(nodes):
    """Keep aligned sibling cards atomic before searching for page-wide cuts.

    Small handwriting overlaps above a card row must not cause each card to
    fall into the ambiguous vertical-stack fallback. Geometry and explicit
    card containers are the evidence; no text or fixed column count is used.
    """
    cards = sorted([n for n in nodes if n.get('kind') == 'container'
                    and n.get('container_class') == 'Card'], key=lambda n: (n['y1'], n['x1']))
    used = set()
    rows = []
    for card in cards:
        if id(card) in used:
            continue
        height = max(1, card['y2']-card['y1'])
        peers = [n for n in cards if id(n) not in used
                 and .75*height <= n['y2']-n['y1'] <= 1.33*height
                 and min(n['y2'], card['y2'])-max(n['y1'], card['y1']) >= .75*height]
        peers.sort(key=lambda n: n['x1'])
        if len(peers) < 2 or any(a['x2'] > b['x1'] for a, b in zip(peers, peers[1:])):
            continue
        bounds = _bounds(peers)
        # Do not enclose unrelated text/controls occupying the spaces between
        # these cards. Slight boundary noise from a nearby heading is allowed.
        peer_ids = {id(n) for n in peers}
        obstructed = False
        for n in nodes:
            if id(n) in peer_ids:
                continue
            overlap = max(0, min(n['x2'], bounds['x2'])-max(n['x1'], bounds['x1']))
            overlap *= max(0, min(n['y2'], bounds['y2'])-max(n['y1'], bounds['y1']))
            if overlap/max(1, _area(n)) > .2:
                obstructed = True
                break
        if not obstructed:
            rows.append(_group('row', peers, role='card-row'))
            used.update(peer_ids)
    return [n for n in nodes if id(n) not in used]+rows if rows else nodes


def _spatial_tree(nodes, depth=0, prefer_rows=False):
    nodes = sorted(_horizontal_fields(_content_titles(nodes)),
                   key=lambda n: (n['y1'], n['x1']))
    if not nodes:
        return _group('stack', [])
    if len(nodes) == 1:
        return nodes[0]
    if prefer_rows:
        paired = _panel_list_rows(nodes)
        if paired is not None:
            return paired
    if depth >= 12:
        return _group('stack', nodes, reason='Recursion limit; geometry retained.')

    # A common horizontal band is a row, even when it contains three buttons.
    common = min(n['y2'] for n in nodes)-max(n['y1'] for n in nodes)
    disjoint = len(_axis_groups(nodes, 'x')) == len(nodes)
    # OCR prose and its inline link may touch or overlap by a few pixels.
    # Allow only small boundary noise between text leaves on a shared baseline;
    # keep controls, containers and genuinely overlapping regions unchanged.
    text_nodes = sorted(nodes, key=lambda n: n['x1'])
    if (not disjoint and all(n.get('kind') == 'component'
            and n.get('component', {}).get('class') in
                {'Paragraph', 'Label', 'Link', 'Heading', 'Subheading'} for n in text_nodes)):
        disjoint = all(b['x1']-a['x2'] >= -.15*min(a['y2']-a['y1'], b['y2']-b['y1'])
                       for a, b in zip(text_nodes, text_nodes[1:]))
    if disjoint and common >= .35*min(n['y2']-n['y1'] for n in nodes):
        children = sorted(nodes, key=lambda n: n['x1'])
        classes = [n.get('component', {}).get('class') for n in children]
        role = 'button-group' if all(c == 'Button' for c in classes) else 'row'
        return _group('row', children, role=role)

    # A shallow, spanning first row is independent of columns underneath.
    # Detect it before a full-height gutter can split navigation into the body.
    bands = _axis_groups(nodes, 'y')
    if len(bands) > 1 and len(bands[0]) >= 3:
        header = bands[0]
        head_bounds, bounds = _bounds(header), _bounds(nodes)
        head_overlap = min(n['y2'] for n in header)-max(n['y1'] for n in header)
        if (len(_axis_groups(header, 'x')) == len(header)
                and head_overlap >= .35*min(n['y2']-n['y1'] for n in header)
                and head_bounds['x2']-head_bounds['x1'] >= .75*(bounds['x2']-bounds['x1'])
                and head_bounds['y2']-head_bounds['y1'] <= .2*(bounds['y2']-bounds['y1'])):
            body = [n for band in bands[1:] for n in band]
            return _group('stack', [_spatial_tree(header, depth+1),
                                    _spatial_tree(body, depth+1)])

    columns = _column_groups(nodes)
    if columns:
        children = [_spatial_tree(group, depth+1) for group in columns]
        return _group('columns', children,
                      widths=[c['x2']-c['x1'] for c in children],
                      gaps=[max(0, b['x1']-a['x2']) for a, b in zip(children, children[1:])])

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

    # Preserve established card rows when slight border/text overlap prevents
    # a clean page-wide cut. Leave already successful partitions unchanged.
    grouped = _container_rows(nodes)
    if len(grouped) < len(nodes):
        return _spatial_tree(grouped, depth+1, prefer_rows)

    # Ambiguous overlapping boxes are retained, not silently discarded.
    return _group('stack', nodes, reason='No unambiguous whitespace cut.')


def _cell_column_slots(evidence, rows, anchors, bounds, height):
    """Use repeated compact cell boxes when OCR fragments over-split columns."""
    groups = []
    for cell in sorted(evidence, key=lambda n: (n['x1']+n['x2'])/2):
        center = (cell['x1']+cell['x2'])/2
        match = next((g for g in groups if abs(center-median(
            (p['x1']+p['x2'])/2 for p in g)) < height), None)
        if match is None:
            groups.append([cell])
        else:
            match.append(cell)
    slots = []
    for group in groups:
        row_ids = {min(range(len(rows)), key=lambda i: abs(
            (n['y1']+n['y2'])/2-median((o['y1']+o['y2'])/2 for o in rows[i])))
            for n in group}
        if len(row_ids) >= 3:
            slots.append({'x1': median(n['x1'] for n in group),
                          'x2': median(n['x2'] for n in group)})
    if len(slots) < 3:
        return None
    # Keep sparse outer columns, such as row identifiers or an action heading.
    for anchor in anchors:
        left = min(o['x1'] for _, o in anchor)
        right = max(o['x2'] for _, o in anchor)
        if right < slots[0]['x1']-height*.4 or left > slots[-1]['x2']+height*.4:
            slots.append({'x1': left, 'x2': right})
            slots.sort(key=lambda n: n['x1'])
    if len(slots) >= len(anchors) or any(
            b['x1'] <= a['x2'] for a, b in zip(slots, slots[1:])):
        return None
    edges = [bounds['x1']] + [(a['x2']+b['x1'])/2
             for a, b in zip(slots, slots[1:])] + [bounds['x2']]
    proposed = [[] for _ in slots]
    for row_index, row in enumerate(rows):
        for word in row:
            center = (word['x1']+word['x2'])/2
            col = next((i for i in range(len(slots))
                        if edges[i] <= center <= edges[i+1]), None)
            if col is None:
                return None
            # A phrase crossing a proposed divider is evidence against it.
            overlap = min(word['x2'], edges[col+1])-max(word['x1'], edges[col])
            if overlap < .8*max(1, word['x2']-word['x1']):
                return None
            proposed[col].append((row_index, word))
    if any(not col for col in proposed):
        return None
    return proposed, edges


def _table_groups(leaves):
    """Use table predictions plus repeated OCR alignment, not table vocabulary."""
    candidates = [n for n in leaves if n['component']['class'] in {'Table', 'Table data'}]
    clusters = []
    for node in candidates:
        touching = []
        for group in clusters:
            if any(min(node['y2'], p['y2']) >= max(node['y1'], p['y1'])
                   and min(node['x2'], p['x2'])-max(node['x1'], p['x1'])
                   > .7*min(node['x2']-node['x1'], p['x2']-p['x1']) for p in group):
                touching.append(group)
        joined = [node]
        for group in touching:
            joined.extend(group)
            clusters.remove(group)
        clusters.append(joined)
    tables, consumed = [], set()
    for group in clusters:
        bounds = _bounds(group)
        members = [n for n in leaves if n['index'] not in consumed
                   and (_inside(n, bounds) or n in group)]
        words = {}
        for n in members:
            for o in n['component'].get('ocr', []):
                words[o['ocr_id']] = o
        if len(words) < 6:
            continue
        height = median(max(1, o['y2']-o['y1']) for o in words.values())
        # Large erroneous table boxes can cover the toolbar. Tight cell-sized
        # detections provide a stronger vertical boundary than their union.
        cell_evidence = [n for n in members
                         if n['component']['class'] in {'Table head', 'Table data'}
                         and n['y2']-n['y1'] <= height*2.5
                         and n['x2']-n['x1'] <= (bounds['x2']-bounds['x1'])*.45]
        # Separate distant compact-cell bands before trusting the union of
        # broad table predictions. A false box may bridge unrelated sections.
        evidence_bands = []
        for n in sorted(cell_evidence, key=lambda n: n['y1']):
            if not evidence_bands or n['y1'] > max(
                    p['y2'] for p in evidence_bands[-1])+height*3:
                evidence_bands.append([n])
            else:
                evidence_bands[-1].append(n)
        supported = [band for band in evidence_bands if len(band) >= 6
                     and max(n['y2'] for n in band)-min(n['y1'] for n in band) > height*3]
        # Multiple plausible tables in one cluster need separate evidence;
        # do not silently choose one and consume the others.
        if len(supported) > 1:
            continue
        evidence = supported[0] if supported else cell_evidence
        outside_words = []
        recovered_boundary = False
        if len(evidence) >= 6:
            top = min(n['y1'] for n in evidence)-height*.25
            bottom = max(n['y2'] for n in evidence)+height*.25
            recovered_boundary = any(not top <= (o['y1']+o['y2'])/2 <= bottom
                                     for n in group for o in n['component'].get('ocr', []))
            bounds = {**bounds, 'y1': max(bounds['y1'], top),
                      'y2': min(bounds['y2'], bottom)}
            members = [n for n in members if n in group or
                       (n['y1'] >= bounds['y1']-height*.25
                        and n['y2'] <= bounds['y2']+height*.25)]
            # Split OCR ownership at the boundary instead of either swallowing
            # outside text or abandoning table reconstruction entirely.
            all_words = {o['ocr_id']: o for n in members
                         for o in n['component'].get('ocr', [])}
            words = {i: o for i, o in all_words.items()
                     if bounds['y1'] <= (o['y1']+o['y2'])/2 <= bounds['y2']}
            outside_words = [o for i, o in all_words.items() if i not in words]
        rows = []
        for o in sorted(words.values(), key=lambda o: ((o['y1']+o['y2'])/2, o['x1'])):
            cy = (o['y1']+o['y2'])/2
            row = next((r for r in rows if abs(cy-median(
                (p['y1']+p['y2'])/2 for p in r)) < height*.65), None)
            if row is None:
                rows.append([o])
            else:
                row.append(o)
        # Require several multi-cell rows; one title bar is not a table.
        multi_rows = [r for r in rows if len(r) >= 2]
        if len(multi_rows) < 3:
            continue
        anchors = []
        for row_index, row in enumerate(rows):
            for o in sorted(row, key=lambda o: o['x1']):
                match = next((a for a in anchors if abs(
                    o['x1']-median(p['x1'] for _, p in a)) < height*1.2), None)
                if match is None:
                    anchors.append([(row_index, o)])
                else:
                    match.append((row_index, o))
        anchors.sort(key=lambda a: median(p['x1'] for _, p in a))
        # Split OCR phrases must not create extra columns inside an
        # established column's text extent (for example a split personal name).
        consolidated = []
        for anchor in anchors:
            if (consolidated and 0 not in {i for i, _ in anchor}
                    and {i for i, _ in anchor}.issubset(
                        {i for i, _ in consolidated[-1]})
                    and len({i for i, _ in consolidated[-1]}) >= 3
                    and min(p['x1'] for _, p in anchor)
                        <= max(p['x2'] for _, p in consolidated[-1])+height*.3):
                consolidated[-1].extend(anchor)
            else:
                consolidated.append(anchor)
        anchors = consolidated
        repeated = [a for a in anchors if len({i for i, _ in a}) >= 3]
        if len(repeated) < 2:
            continue
        # When recovering a contaminated region, a separated first row can
        # define column slots even when headings are centred and body text is
        # left-aligned. Require repeated body support; never inspect wording.
        if recovered_boundary:
            first = sorted(rows[0], key=lambda o: o['x1'])
            if len(first) >= 3 and all(b['x1']-a['x2'] > height*.6
                                      for a, b in zip(first, first[1:])):
                centers = [(o['x1']+o['x2'])/2 for o in first]
                slots = [bounds['x1']] + [(a+b)/2 for a, b in zip(centers, centers[1:])] + [bounds['x2']]
                proposed = [[] for _ in first]
                for row_index, row in enumerate(rows):
                    for o in row:
                        cx = (o['x1']+o['x2'])/2
                        col = next((i for i in range(len(first))
                                    if slots[i] <= cx <= slots[i+1]), None)
                        if col is not None:
                            proposed[col].append((row_index, o))
                supported_cols = sum(len({i for i, _ in col if i > 0}) >= 2
                                     for col in proposed)
                if (supported_cols >= max(2, len(first)//2)
                        and sum(map(len, proposed)) == len(words)):
                    anchors = proposed
        # Keep sparse edge columns (for example a header whose row IDs OCR missed).
        starts = [median(p['x1'] for _, p in a) for a in anchors]
        edges = [bounds['x1']] + [
            (max(p['x2'] for _, p in left)+min(p['x1'] for _, p in right))/2
            for left, right in zip(anchors, anchors[1:])] + [bounds['x2']]
        cell_slots = _cell_column_slots(evidence, rows, anchors, bounds, height)
        if cell_slots is not None:
            anchors, edges = cell_slots
            starts = [median(p['x1'] for _, p in a) for a in anchors]
        if any(b <= a for a, b in zip(edges, edges[1:])):
            continue  # Ambiguous overlapping columns: retain original evidence.
        row_nodes = []
        for row_index, row in enumerate(rows):
            cells = []
            for col in range(len(anchors)):
                cell_words = [p for i, p in anchors[col] if i == row_index]
                cell_words.sort(key=lambda p: p['x1'])
                y1, y2 = min(p['y1'] for p in row), max(p['y2'] for p in row)
                c = dict(x1=edges[col], x2=edges[col+1], y1=y1, y2=y2,
                         id=f"table-{group[0]['index']}-{row_index}-{col}",
                         **{'class': 'Paragraph'}, texts=[p['text'] for p in cell_words],
                         ocr=cell_words, source='table-geometry')
                cells.append(dict(kind='component', component=c,
                                  **{k: c[k] for k in ('x1', 'x2', 'y1', 'y2')}))
            row_nodes.append(_group('row', cells, role='table-row'))
        # Unknown controls/icons remain available to the renderer as evidence;
        # do not invent edit/delete actions from their position or OCR wording.
        controls = [n for n in members if n['component']['class'] in
                    {'Button', 'Check Box', 'Radio Button', 'Textbox', 'Select', 'Image'}]
        for n in controls:
            cy = (n['y1']+n['y2'])/2
            row = min(row_nodes, key=lambda r: abs(cy-(r['y1']+r['y2'])/2))
            col = min(range(len(starts)), key=lambda i: abs(n['x1']-starts[i]))
            cell = row['children'][col]
            # Text already appears in cells, so remove it from copied controls.
            c = {**n['component'], 'texts': [], 'ocr': []}
            child = {**n, 'component': c}
            row['children'][col] = {**cell, 'kind': 'stack', 'children': [cell, child]}
        node = _group('container', row_nodes, container_class='Section',
                      role='table', column_edges=edges, index=group[0]['index'],
                      source_indices=[n['index'] for n in members])
        node.update(bounds)
        # OCR from an oversized consumed prediction still belongs to the
        # page. Rebuild those runs at their own boxes, outside the table.
        for o in outside_words:
            c = {**{k: o[k] for k in ('x1', 'y1', 'x2', 'y2')},
                 'id': f"table-outside-{o['ocr_id']}", 'class': 'Paragraph',
                 'texts': [o['text']], 'ocr': [o], 'source': 'table-boundary-recovery'}
            # A short, prominent caption to the left of a toolbar belongs
            # to the following table section, not to its first data row.
            # Require both an input and a button on its baseline; this avoids
            # promoting ordinary prose or individual table cells.
            h = max(1, o['y2']-o['y1'])
            toolbar = [n for n in leaves
                       if n['component']['class'] in CONTROL_CLASSES | {'Button'}
                       and n['x1'] > o['x2']
                       and abs((n['y1']+n['y2']-o['y1']-o['y2'])/2)
                           <= .6*max(h, n['y2']-n['y1'])
                       and n['y2'] <= bounds['y1'] + height*.25]
            classes = {n['component']['class'] for n in toolbar}
            if (o['y2'] <= bounds['y1'] and bounds['y1']-o['y2'] <= height*3
                    and h >= height*1.2 and len(o['text'].split()) <= 8
                    and 'Button' in classes and 'Textbox' in classes):
                c['class'] = 'Subheading'
                c['corrections'] = ['Prominent caption beside table toolbar controls.']
            tables.append(dict(kind='component', component=c,
                               **{k: c[k] for k in ('x1', 'y1', 'x2', 'y2')}))
        tables.append(node)
        consumed.update(n['index'] for n in members)
    return tables, consumed


def _hierarchy(components):
    leaves = []
    for index, component in enumerate(components):
        c = dict(component)
        leaves.append({'kind': 'component', 'component': c, 'index': index,
                       **{key: c[key] for key in ('x1', 'y1', 'x2', 'y2')}})

    tables, table_members = _table_groups(leaves)
    leaves = [n for n in leaves if n['index'] not in table_members]

    # Only explicit, mapped label associations form atomic fields.
    # Missing IDs must never make unrelated labels and controls match.
    used = set()
    grouped = list(tables)
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
        if node['component']['class'] == 'Card':
            children = _content_titles(children, card=True)
        return {**node, 'kind': 'container',
                'children': [_spatial_tree(children, prefer_rows=node['component']['class'] == 'Panel')],
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
