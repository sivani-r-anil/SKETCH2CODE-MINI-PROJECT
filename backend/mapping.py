"""Spatial association first; conservative, explainable semantic corrections second."""
from statistics import median
from copy import deepcopy
import re
from detection import area, intersection

TEXT_CLASSES = {'Heading', 'Subheading', 'Label', 'Paragraph', 'Link'}
CONTAINERS = {'Form', 'Card', 'Container', 'Panel', 'Section', 'Table', 'Table row'}
INPUTS = {'Textbox', 'Password box', 'Textarea', 'Select'}


def text_box(ocr):
    return dict(x1=min(p[0] for p in ocr['box']), y1=min(p[1] for p in ocr['box']),
                x2=max(p[0] for p in ocr['box']), y2=max(p[1] for p in ocr['box']))


def reading_order(items):
    rows = []
    for item in sorted(items, key=lambda c: (c['y1'], c['x1'])):
        cy = (item['y1'] + item['y2']) / 2
        row = next((r for r in rows if abs(cy-r['cy']) < .5 * min(
            item['y2']-item['y1'], r['height'])), None)
        if row is None:
            rows.append({'cy': cy, 'height': item['y2']-item['y1'], 'items': [item]})
        else:
            row['items'].append(item)
    return [c for r in rows for c in sorted(r['items'], key=lambda c: c['x1'])]


def change_class(c, new_class, reason):
    if c['class'] != new_class:
        c.setdefault('original_class', c['class'])
        c['class'] = new_class
        c.setdefault('corrections', []).append(reason)


def prepare_regions(detections, text_items, rectangles, markers):
    """Recover only geometry-supported regions; keep inference provenance explicit."""
    regions = deepcopy(detections)
    nav_text_ids = set()
    removed = set()
    for i, c in enumerate(regions):
        if i in removed or c['class'] not in INPUTS | {'Button', 'Image'}:
            continue
        children = [(j, d) for j, d in enumerate(regions) if j != i
                    and area(d) < area(c)*.65
                    and intersection(c, d)/max(1, area(d)) > .9]
        runs = reading_order([o for o in text_items if intersection(c, o)/max(1, area(o)) > .6])
        # A header border is also a rectangle. It is not evidence that a whole
        # navigation bar is a button. Require an enclosed image/logo region and
        # several independent captions on one baseline before overriding it.
        free_runs = [o for o in runs if not any(
            intersection(o, child)/max(1, area(o)) > .6 for _, child in children)]
        nav_height = median([o['y2']-o['y1'] for o in free_runs]) if free_runs else 1
        outlined_navigation = (
            c['class'] == 'Button' and c.get('outline') and not c.get('filled')
            and len(free_runs) >= 3
            and (c['x2']-c['x1']) > 6*max(1, c['y2']-c['y1'])
            and any(child['class'] == 'Image' and child['x2'] < free_runs[0]['x1']
                    for _, child in children)
            and max((o['y1']+o['y2'])/2 for o in free_runs)
                - min((o['y1']+o['y2'])/2 for o in free_runs) < nav_height*.6
            and all(b['x1']-a['x2'] > nav_height*.6
                    for a, b in zip(free_runs, free_runs[1:])))
        if outlined_navigation:
            removed.add(i)
            nav_text_ids.update(o['ocr_id'] for o in free_runs)
            continue
        # A wide enclosing detection with several separated captions is a group,
        # not one enormous button. Child controls retain ownership of their text.
        if children and len(runs) >= 3 and not c.get('outline'):
            separated = any(b['x1']-a['x2'] > 1.2*(a['y2']-a['y1'])
                            for a, b in zip(runs, runs[1:]))
            if separated and (c['x2']-c['x1']) > 3*(c['y2']-c['y1']):
                removed.add(i)
                nav_text_ids.update(o['ocr_id'] for o in runs)
        # Nested, textless shapes in a compact region are ambiguous artwork.
        # Represent one image placeholder instead of inventing empty controls.
        elif children and not runs and (c['x2']-c['x1']) < 2.5*(c['y2']-c['y1']):
            change_class(c, 'Image', 'Nested textless shapes consolidated as an artwork region.')
            c['source'] = 'geometry+yolo'
            removed.update(j for j, _ in children)
    regions = [c for i, c in enumerate(regions) if i not in removed]
    for r in rectangles or []:
        runs = [o for o in text_items if intersection(r, o)/max(1, area(o)) > .85]
        if (r.get('filled') and runs and not any(intersection(r, c)/max(1, min(area(r), area(c))) > .5
                                                for c in regions if c['class'] not in TEXT_CLASSES | CONTAINERS)):
            regions.append({**r, 'class': 'Button', 'confidence': None, 'source': 'opencv+ocr',
                            'outline': True, 'corrections': ['Filled closed rectangle with an OCR caption; missed by YOLO.']})
    for m in markers or []:
        if not m.get('square') or any(intersection(m, o)/max(1, area(m)) > .2 for o in text_items):
            continue
        h = m['y2']-m['y1']
        adjacent = [o for o in text_items if 0 <= o['x1']-m['x2'] < 2*h
                    and abs((o['y1']+o['y2']-m['y1']-m['y2'])/2) < .6*h]
        if adjacent and not any(intersection(c, m)/max(1, area(m)) > .5 for c in regions
                                if c['class'] not in TEXT_CLASSES | CONTAINERS):
            regions.append({**m, 'class': 'Check Box', 'confidence': None, 'source': 'opencv+ocr',
                            'corrections': ['Square outline beside OCR text; missed by YOLO.']})
    return regions, nav_text_ids


def map_text_to_components(detections, ocr_texts, markers=None, rectangles=None, containers=None):
    text_items = [{**o, **text_box(o), 'ocr_id': i} for i, o in enumerate(ocr_texts)]
    # A coloured fragment needs inline context; colour alone is not a link.
    # Propagate that evidence across neighbouring fragments of the same run.
    pending = [o for o in text_items if o.get('coloured_text')]
    def adjacent(a, b):
        h = min(a['y2']-a['y1'], b['y2']-b['y1'])
        return (abs((a['y1']+a['y2']-b['y1']-b['y2'])/2) < h*.6
                and -h*.2 <= max(a['x1'],b['x1'])-min(a['x2'],b['x2']) < h*1.2)
    while pending:
        group = [pending.pop(0)]
        changed = True
        while changed:
            changed = False
            for item in list(pending):
                if any(adjacent(item, member) for member in group):
                    group.append(item)
                    pending.remove(item)
                    changed = True
        anchored = any(o.get('underlined') or o.get('link_hint') for o in group) or any(
            not p.get('coloured_text') and any(adjacent(p, o) for o in group) for p in text_items)
        if anchored:
            for item in group:
                item['link_hint'] = True
    detections, nav_text_ids = prepare_regions(detections, text_items, rectangles, markers)
    mapped = [{**d, 'id': f'component-{i}', 'source': d.get('source', 'yolo'), 'texts': [], 'ocr': []}
              for i, d in enumerate(detections)]
    unmatched = []
    for o in reading_order(text_items):
        # Containers and text detections must not swallow whole lines or child text.
        choices = []
        for c in mapped:
            coverage = intersection(c, o) / max(1, area(o))
            if c['class'] in CONTAINERS:
                continue
            if c['class'] in TEXT_CLASSES:
                continue  # Rebuild text runs from OCR geometry below.
            if coverage >= .60:
                choices.append(c)
        if choices:
            best = min(choices, key=lambda c: area(c))
            best['ocr'].append(o)
        else:
            unmatched.append(o)

    if markers is not None:
        # Closed letters (O, D, etc.) inside OCR text are not toggle outlines.
        markers = [m for m in markers if not any(intersection(m, o)/max(1, area(m)) > .2
                                                for o in text_items)]
        for c in mapped:
            if c['class'] not in {'Check Box', 'Radio Button'}:
                continue
            runs = c['ocr']
            left = min((o['x1'] for o in runs), default=c['x2'])
            valid = any(intersection(c, m)/max(1, area(m)) > .5
                        and m['x2'] <= left+2 for m in markers)
            if not valid:
                unmatched.extend(runs)
                c['ocr'] = []
                c['class'] = 'Paragraph'  # Rebuilt from OCR below, not a fake toggle.

    # Text-only detections with OCR are reconstructed below, without empty headings.
    output = [c for c in mapped if c['class'] not in TEXT_CLASSES]
    for c in output:
        c['ocr'] = reading_order(c['ocr'])
        c['texts'] = [o['text'] for o in c['ocr']]
        text = ' '.join(c['texts']).strip().lower()
        # A word such as "password" in a LINK is never an input rule.
        if c.get('outline') and c['class'] in INPUTS | {'Button', 'Image'}:
            if re.match(r'^(enter|type|input|search)\s+\S', text):
                kind = 'Password box' if 'password' in text else 'Textbox'
                change_class(c, kind, 'Placeholder instruction inside a rectangular control.')
            elif c['class'] in {'Textbox', 'Password box', 'Image'} and text in {
                'login', 'log in', 'sign in', 'sign up', 'submit', 'register',
                'save', 'cancel', 'continue', 'next', 'send', 'search', 'create account'
            }:
                change_class(c, 'Button', 'Short action caption inside a rectangular control.')
        if c['class'] == 'Textbox' and 'email' in text:
            c['input_type'] = 'email'

    # Recover every unmatched OCR run, using typography, nearby fields and underlines.
    heights = [o['y2']-o['y1'] for o in text_items]
    typical_height = median(heights) if heights else 1
    fields = [c for c in output if c['class'] in INPUTS]
    top = min((o['y1'] for o in text_items), default=0)
    for o in unmatched:
        kind = 'Paragraph'
        # A tilted OCR box can be taller than its neighbours on the same line.
        # Use nearby typography to avoid promoting half a sentence to a heading.
        peers = [p for p in text_items if p['ocr_id'] != o['ocr_id']
                 and abs((p['y1']+p['y2']-o['y1']-o['y2'])/2) < typical_height*.5
                 and -.15*typical_height <= max(p['x1'],o['x1'])-min(p['x2'],o['x2']) < typical_height*1.5]
        text_height = min([o['y2']-o['y1']] + [p['y2']-p['y1'] for p in peers])
        nearby = [c for c in fields if 0 <= c['y1']-o['y2'] <= typical_height*1.5
                  and c['x1']-typical_height <= o['x1'] < c['x2']]
        if nearby and not (o.get('underlined') or o.get('link_hint')):
            kind = 'Label'
        elif o.get('underlined') or o.get('link_hint') or o['ocr_id'] in nav_text_ids or any(d['class'] == 'Link' and (d.get('confidence') or 0) >= .4
                                          and intersection(d, o)/max(1, area(o)) >= .6
                                          for d in detections):
            kind = 'Link'
        elif text_height >= typical_height*1.5:
            kind = 'Heading'
        elif o['y1']-top < typical_height*3:
            kind = 'Subheading'
        c = {**text_box(o), 'id': f'ocr-{o["ocr_id"]}', 'class': kind,
             'texts': [o['text']], 'ocr': [o], 'confidence': o['confidence'],
             'source': 'ocr', 'corrections': ['Text retained using OCR geometry.']}
        if nearby and kind == 'Label':
            field = min(nearby, key=lambda f: (f['y1']-o['y2'], abs(f['x1']-o['x1'])))
            c['for_id'] = field['id']
            field['label'] = o['text']
            if 'password' in o['text'].lower() and field['class'] in {'Textbox', 'Select'}:
                change_class(field, 'Password box', 'Password label immediately above this field.')
        output.append(c)

    # Join neighbouring text fragments only within a line, retaining links separately.
    ordered = reading_order(output)
    merged = []
    for c in ordered:
        prev = merged[-1] if merged else None
        h = c['y2']-c['y1']
        if (prev and c['source'] == prev.get('source') == 'ocr'
                and not any(o['ocr_id'] in nav_text_ids or (o.get('separate_run') and not o.get('coloured_text'))
                            for o in c['ocr']+prev['ocr'])
                and c['class'] == prev['class'] and c.get('for_id') == prev.get('for_id')
                and abs((c['y1']+c['y2']-prev['y1']-prev['y2'])/2) < .5*min(h, prev['y2']-prev['y1'])
                and -typical_height*.15 <= c['x1']-prev['x2'] <= typical_height*1.2):
            prev['x2'] = c['x2']; prev['y1'] = min(prev['y1'], c['y1']); prev['y2'] = max(prev['y2'], c['y2'])
            prev['texts'].extend(c['texts']); prev['ocr'].extend(c['ocr'])
        else:
            merged.append(c)
    for c in merged:
        c['texts'] = [re.sub(r"([A-Za-z])(['’])\s+([A-Za-z])", r'\1\2\3', t) for t in c['texts']]
    for c in merged:
        if c['class'] == 'Check Box' and not c['texts']:
            h = c['y2']-c['y1']
            captions = [p for p in merged if p['class'] in {'Paragraph', 'Subheading'}
                        and 0 <= p['x1']-c['x2'] < 2*h
                        and abs((p['y1']+p['y2']-c['y1']-c['y2'])/2) < .6*h]
            if captions:
                p = min(captions, key=lambda p: p['x1'])
                c['texts'], c['ocr'] = p['texts'], p['ocr']
                c['x2'] = p['x2']
                merged.remove(p)
    # Optional closed outlines need supporting content before becoming cards.
    # Reject the outer page frame, artwork and boxes cutting through siblings.
    content = [c for c in merged if c['class'] not in CONTAINERS]
    for r in containers or []:
        inside = [c for c in content if intersection(r, c)/max(1, area(c)) >= .95]
        if len(inside) < 2 or len(inside) >= len(content)*.9:
            continue
        if not any(c['class'] in INPUTS | {'Button', 'Check Box', 'Radio Button'} for c in inside):
            continue
        if any(.05 < intersection(r, c)/max(1, area(c)) < .95 for c in content):
            continue
        if any(intersection(r, c)/max(1, min(area(r), area(c))) > .85
               for c in merged if c['class'] in CONTAINERS | {'Image'}):
            continue
        merged.append({**r, 'class': 'Card', 'id': f'container-{len(merged)}',
                       'texts': [], 'ocr': [], 'confidence': None, 'source': 'opencv+geometry',
                       'corrections': ['Closed outline enclosing multiple mapped components.']})
    return merged
