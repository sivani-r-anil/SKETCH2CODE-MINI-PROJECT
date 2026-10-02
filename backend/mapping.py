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
        navigation_runs = [o for o in runs if not any(
            child['class'] not in TEXT_CLASSES
            and intersection(o, child)/max(1, area(o)) > .6 for _, child in children)]
        navigation_height = median([o['y2']-o['y1'] for o in navigation_runs]) if navigation_runs else 1
        page_top = min((o['y1'] for o in text_items), default=c['y1'])
        text_brand_navigation = (
            c['class'] == 'Button' and c.get('outline') and not c.get('filled')
            and len(navigation_runs) >= 4
            and c['y1'] <= page_top+navigation_height
            and c['x2']-c['x1'] > 8*max(1, c['y2']-c['y1'])
            and max((o['y1']+o['y2'])/2 for o in navigation_runs)
                - min((o['y1']+o['y2'])/2 for o in navigation_runs) < navigation_height*.8
            and all(b['x1']-a['x2'] > navigation_height*.6
                    for a, b in zip(navigation_runs, navigation_runs[1:])))
        if text_brand_navigation:
            removed.add(i)
            # A larger first run is branding, not an inferred navigation link.
            brand = navigation_runs[0]['y2']-navigation_runs[0]['y1'] > navigation_height*1.3
            links = navigation_runs[int(brand):]
            # A trailing action can share the header baseline without being
            # another navigation link. Require a distinct gap after several
            # supported links; preserve explicit underline/link evidence.
            def supported_link(o):
                return (o.get('underlined') or o.get('link_hint') or any(
                    d['class'] == 'Link' and (d.get('confidence') or 0) >= .4
                    and intersection(d, o)/max(1, area(o)) >= .6
                    for d in detections))
            if len(links) >= 4:
                trailing = links[-1]
                normal_gaps = [b['x1']-a['x2'] for a, b in zip(links[:-2], links[1:-1])]
                action_gap = trailing['x1']-links[-2]['x2']
                if (not supported_link(trailing)
                        and sum(bool(supported_link(o)) for o in links[:-1]) >= 3
                        and action_gap > max(navigation_height*2, median(normal_gaps)*3)
                        and trailing['x2']-trailing['x1'] <= navigation_height*6):
                    regions.append({**text_box(trailing), 'class': 'Button',
                                    'source': 'header-action-geometry',
                                    'confidence': trailing.get('confidence', 0),
                                    'corrections': ['Separated trailing header action after supported navigation links.']})
                    links = links[:-1]
            nav_text_ids.update(o['ocr_id'] for o in links)
            continue
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
    # A pencil-shaded action is not saturated, so `filled` can be false.
    # Recover only an unclaimed, darker rectangle aligned with at least two
    # detected form controls. Compare local fills, not an absolute paper colour.
    def brightness(r):
        value = r.get('fill_color', '')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            return None
        return sum(int(value[i:i+2], 16) for i in (1, 3, 5))/3
    for r in rectangles or []:
        shade = brightness(r)
        if shade is None:
            continue
        peers = [p for p in rectangles or [] if p is not r
                 and brightness(p) is not None
                 and abs(p['x1']-r['x1']) < (r['x2']-r['x1'])*.1
                 and .8 < (p['x2']-p['x1'])/max(1, r['x2']-r['x1']) < 1.25
                 and any(c['class'] in INPUTS | {'Button'}
                         and intersection(p, c)/max(1, area(p)) > .9 for c in regions)]
        runs = [o for o in text_items if intersection(r, o)/max(1, area(o)) > .9]
        if (len(peers) >= 2 and 1 <= len(runs) <= 4
                and shade+25 < median(brightness(p) for p in peers)
                and max(o['y1'] for o in runs) < min(o['y2'] for o in runs)
                and not any(c['class'] not in TEXT_CLASSES | CONTAINERS
                            and intersection(r, c)/max(1, area(r)) > .5 for c in regions)):
            regions.append({**r, 'class': 'Button', 'confidence': None,
                            'outline': True, 'source': 'opencv+ocr+geometry',
                            'corrections': ['Darker captioned rectangle aligned with detected form controls.']})
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



def consolidate_repeated_cards(detections, text_items, containers):
    """Resolve repeated card outlines before controls can claim their OCR.

    Require three similarly sized, aligned outlines and distinct text levels.
    This deliberately leaves isolated controls and ordinary button rows alone.
    """
    regions = deepcopy(detections)
    candidates = []
    for r in containers or []:
        w, h = r['x2']-r['x1'], r['y2']-r['y1']
        matches = [c for c in regions if c['class'] == 'Button'
                   and c.get('outline') and not c.get('filled')
                   and intersection(r, c)/max(1, area(r)+area(c)-intersection(r, c)) > .85]
        runs = [o for o in text_items if intersection(r, o)/max(1, area(o)) > .95]
        if len(runs) < 2 or not .8 < w/max(1, h) < 4:
            continue
        ordered_runs = sorted(runs, key=lambda o: o['y1'])
        statistic = (len(ordered_runs) == 2
                     and re.fullmatch(r'[0-9]+(?:[.,][0-9]+)*%?', ordered_runs[0]['text'].strip())
                     and any(ch.isalpha() for ch in ordered_runs[1]['text'])
                     and ordered_runs[1]['y1'] > ordered_runs[0]['y2']
                     and abs(ordered_runs[0]['x1']-ordered_runs[1]['x1']) < h*.15)
        if not matches and not statistic and (len(runs) < 3 or any(
                c['class'] in INPUTS | {'Image', 'Check Box', 'Radio Button'}
                and intersection(r, c)/max(1, area(c)) > .85 for c in regions)):
            continue
        # Wrapped button captions have similar typography; statistic/content
        # cards have separate levels with a visibly larger upper text line.
        ordered = sorted(runs, key=lambda o: o['y1'])
        upper, lower = ordered[0], ordered[-1]
        if (lower['y1'] < upper['y2']
                or (matches and upper['y2']-upper['y1'] < 1.15*(lower['y2']-lower['y1'])
                    and upper['x2']-upper['x1'] >= .6*(lower['x2']-lower['x1']))):
            continue
        candidates.append((r, matches))
    accepted = []
    for r, matches in candidates:
        w, h = r['x2']-r['x1'], r['y2']-r['y1']
        peers = [(q, controls) for q, controls in candidates
                 if .8*w <= q['x2']-q['x1'] <= 1.25*w
                 and .8*h <= q['y2']-q['y1'] <= 1.25*h
                 and abs((q['y1']+q['y2']-r['y1']-r['y2'])/2) < .2*h]
        peers.sort(key=lambda pair: pair[0]['x1'])
        if len(peers) >= 3 and all(
                0 <= b['x1']-a['x2'] <= .6*w
                for (a, _), (b, _) in zip(peers, peers[1:])):
            accepted.append((r, matches))
    for r, matches in accepted:
        primary = matches[0] if matches else {**r, 'class': 'Card',
                   'confidence': None, 'source': 'opencv+ocr+geometry'}
        if not matches:
            regions.append(primary)
        change_class(primary, 'Card', 'Repeated aligned outline with separate text hierarchy.')
        primary.update({k: r[k] for k in ('x1', 'y1', 'x2', 'y2')})
        # Retain genuine child controls. Remove only duplicate outlines and
        # table-class fragments inside this independently supported card.
        regions = [c for c in regions if c is primary or not (
            any(c is duplicate for duplicate in matches[1:]) or
            (c['class'] in {'Table', 'Table head', 'Table data', 'Table row', 'Carousel'}
             and area(c) <= area(r)*1.2
             and intersection(r, c)/max(1, area(c)) >= .85))]
        # A compact, text-free box beside the two statistic text levels is
        # retained as raster artwork rather than an empty input or button.
        runs = sorted([o for o in text_items
                       if intersection(r, o)/max(1, area(o)) > .95], key=lambda o: o['y1'])
        if (len(runs) == 2 and re.fullmatch(r'[0-9]+(?:[.,][0-9]+)*%?', runs[0]['text'].strip())
                and any(ch.isalpha() for ch in runs[1]['text'])):
            icons = [c for c in regions if c is not primary
                     and c['class'] in {'Button', 'Textbox', 'Image'}
                     and intersection(r, c)/max(1, area(c)) > .95
                     and .65 < (c['x2']-c['x1'])/max(1, c['y2']-c['y1']) < 1.5
                     and .3 < (c['y2']-c['y1'])/(r['y2']-r['y1']) < .9
                     and c['x2'] < min(o['x1'] for o in runs)
                     and not any(intersection(c, o) > 0 for o in text_items)]
            kept = []
            for icon in sorted(icons, key=lambda c: c.get('confidence') or 0, reverse=True):
                if any(intersection(icon, other)/max(1, min(area(icon), area(other))) > .8
                       for other in kept):
                    regions = [c for c in regions if c is not icon]
                    continue
                change_class(icon, 'Image', 'Text-free compact artwork beside statistic text in repeated cards.')
                kept.append(icon)
    return regions


def recover_text_panels(detections, text_items, containers):
    """Use repeated text rows and closed panel evidence to resolve false images."""
    regions = deepcopy(detections)
    if not containers or not text_items:
        return regions
    page = max(containers, key=area)
    page_width, page_height = page['x2']-page['x1'], page['y2']-page['y1']
    for panel in sorted(containers, key=area):
        if not (.65*page_width < panel['x2']-panel['x1']
                and .12*page_height < panel['y2']-panel['y1'] < .4*page_height):
            continue
        images = [c for c in regions if c['class'] in {'Image', 'Carousel'}
                  and not c.get('outline')
                  and intersection(panel, c)/max(1, area(c)) >= .9]
        if len(images) < 2 or not any(
                intersection(a, b)/max(1, min(area(a), area(b))) > .5
                for i, a in enumerate(images) for b in images[i+1:]):
            continue
        runs = [o for o in text_items if intersection(panel, o)/max(1, area(o)) >= .95]
        rows = []
        for o in sorted(runs, key=lambda o: (o['y1']+o['y2'])/2):
            cy = (o['y1']+o['y2'])/2
            row = next((r for r in rows if abs(cy-median(
                (p['y1']+p['y2'])/2 for p in r)) < .6*(o['y2']-o['y1'])), None)
            if row is None:
                rows.append([o])
            else:
                row.append(o)
        aligned = []
        for row in rows:
            row.sort(key=lambda o: o['x1'])
            if len(row) >= 2 and any(b['x1']-a['x2'] > .3*page_width
                                     for a, b in zip(row, row[1:])):
                aligned.append(row)
        if len(aligned) < 3:
            continue
        text_height = median(o['y2']-o['y1'] for row in aligned for o in row)
        if (max(row[0]['x1'] for row in aligned)-min(row[0]['x1'] for row in aligned) > text_height
                or max(row[-1]['x2'] for row in aligned)-min(row[-1]['x2'] for row in aligned) > text_height):
            continue
        # Preserve OCR separately: these are repeated text rows, not a crop.
        removed = [c for c in regions if c['class'] in {'Image', 'Carousel'}
                   and not c.get('outline')
                   and intersection(panel, c)/max(1, area(c)) > .6
                   and any(intersection(c, image)/max(1, min(area(c), area(image))) > .5
                           for image in images)]
        regions = [c for c in regions if c not in removed]
        regions.append({**panel, 'class': 'Panel', 'confidence': None,
                        'source': 'opencv+ocr+yolo-geometry',
                        'evidence': deepcopy(removed),
                        'corrections': ['Overlapping image predictions contradicted by repeated aligned text rows in a closed panel.']})
    # A page-wide border can attract a button prediction from footer text.
    # Require a bottom band, multiword text, and raw predictions much narrower
    # than the snapped outline. A normal full-width action is left unchanged.
    for c in regions:
        if c['class'] != 'Button' or not c.get('outline') or c.get('filled'):
            continue
        w, h = c['x2']-c['x1'], c['y2']-c['y1']
        runs = [o for o in text_items if intersection(c, o)/max(1, area(o)) >= .9]
        evidence = c.get('evidence', [])
        if (w > .9*page_width and w > 10*max(1, h)
                and c['y1'] > page['y1']+.85*page_height
                and len(runs) >= 2 and len(' '.join(o['text'] for o in runs).split()) >= 5
                and max(o['x2'] for o in runs)-min(o['x1'] for o in runs) < w*.65
                and evidence and all(e['x2']-e['x1'] < w*.65 for e in evidence)):
            change_class(c, 'Paragraph', 'Bottom text band snapped to a page-wide outline; raw predictions cover only text.')
    return regions


def clean_region_evidence(detections, text_items, rectangles, containers):
    """Discard unsupported table regions and duplicate input-edge predictions."""
    regions = deepcopy(detections)
    table_cells = [c for c in regions if c['class'] == 'Table head']
    if not table_cells:
        # Keep tables when several independent table predictions agree. A lone
        # oversized Table data box on a form is not enough table evidence.
        table_boxes = [c for c in regions if c['class'] == 'Table']
        if len(table_boxes) < 3:
            regions = [c for c in regions if c['class'] not in {'Table', 'Table data', 'Table row'}]
    supported_inputs = [c for c in regions if c['class'] in INPUTS | {'Button'} and c.get('outline')]
    kept = []
    for c in regions:
        if c['class'] in INPUTS and not c.get('outline'):
            runs = [o for o in text_items if intersection(c, o)/max(1, area(o)) >= .6]
            aligned = [p for p in supported_inputs if abs(p['x1']-c['x1']) < (p['x2']-p['x1'])*.35
                       and .6 < (c['x2']-c['x1'])/max(1, p['x2']-p['x1']) < 1.4]
            crossing = any(0 < intersection(c, p) < area(c)*.8 for p in aligned)
            boundary = any(r['x1'] <= (c['x1']+c['x2'])/2 <= r['x2']
                           and (c['y1'] < r['y1'] < c['y2'] or c['y1'] < r['y2'] < c['y2'])
                           for r in containers or [])
            if not runs and len(aligned) >= 2 and (crossing or boundary):
                continue
        kept.append(c)
    return kept


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
    detections = consolidate_repeated_cards(detections, text_items, containers)
    detections = recover_text_panels(detections, text_items, containers)
    detections = clean_region_evidence(detections, text_items, rectangles, containers)
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
        if c.get('outline') and c['class'] in INPUTS | {'Button'}:
            field_caption = re.fullmatch(
                r'(?:confirm |re[- ]?enter )?password|(?:full |first |last |user ?)?name|'
                r'e[- ]?mail(?: address)?|(?:user ?name|email)(?: or (?:user ?name|email))|'
                r'phone(?: number)?|address|city|postal code|zip code', text)
            siblings = [p for p in output if p is not c and p.get('outline')
                        and p['class'] in INPUTS
                        and abs(p['x1']-c['x1']) < (c['x2']-c['x1'])*.1
                        and .8 < (p['x2']-p['x1'])/max(1, c['x2']-c['x1']) < 1.25]
            if field_caption and (c['class'] in INPUTS or siblings):
                change_class(c, 'Password box' if 'password' in text else 'Textbox',
                             'Field caption in an outlined control aligned with input fields.')
        if c['class'] == 'Textbox' and 'email' in text:
            c['input_type'] = 'email'

    # Recover every unmatched OCR run, using typography, nearby fields and underlines.
    heights = [o['y2']-o['y1'] for o in text_items]
    typical_height = median(heights) if heights else 1
    fields = [c for c in output if c['class'] in INPUTS]
    top = min((o['y1'] for o in text_items), default=0)
    # Interpret short standalone account actions only below detected form
    # fields and outside controls. This is semantic mapping, not page selection.
    ordered_unmatched = reading_order(unmatched)
    action_pattern = re.compile(r'(?:log ?in|sign ?in|sign ?up|register|'
                                r'(?:forgot|reset|recover|change) (?:your )?password|'
                                r'create (?:an? )?account)[?!.]?$', re.I)
    for i in range(len(ordered_unmatched)):
        for count in range(1, 4):
            group = ordered_unmatched[i:i+count]
            if len(group) != count:
                continue
            h = min(p['y2']-p['y1'] for p in group)
            if any(abs(a['y1']+a['y2']-b['y1']-b['y2'])/2 > h*.5
                   or not -h*.15 <= b['x1']-a['x2'] <= h*.7
                   for a, b in zip(group, group[1:])):
                continue
            caption = re.sub(r'\s+', ' ', ' '.join(p['text'].replace('_', ' ') for p in group))
            near_form = any(group[0]['y1'] >= f['y2']
                            and group[0]['y1']-f['y2'] < 4*(f['y2']-f['y1'])
                            and f['x1'] <= group[0]['x1'] <= f['x2'] for f in fields)
            if near_form and action_pattern.fullmatch(caption):
                for p in group:
                    if p.get('underlined') or p.get('link_hint') or any(
                            d['class'] == 'Link' and (d.get('confidence') or 0) >= .4
                            and intersection(d, p)/max(1, area(p)) >= .6 for d in detections):
                        continue
                    p['link_hint'] = True
                    # Keep raw OCR in `ocr`; only display text is normalized.
                    p['display_text'] = re.sub(r'\s+', ' ', p['text'].replace('_', ' '))
    for o in unmatched:
        kind = 'Paragraph'
        # A tilted OCR box can be taller than its neighbours on the same line.
        # Use nearby typography to avoid promoting half a sentence to a heading.
        peers = [p for p in text_items if p['ocr_id'] != o['ocr_id']
                 and abs((p['y1']+p['y2']-o['y1']-o['y2'])/2) < typical_height*.5
                 and -.15*typical_height <= max(p['x1'],o['x1'])-min(p['x2'],o['x2']) < typical_height*1.5]
        text_height = min([o['y2']-o['y1']] + [p['y2']-p['y1'] for p in peers])
        nearby = [c for c in fields if 0 <= c['y1']-o['y2'] <= typical_height*1.5
                  and abs(c['x1']-o['x1']) <= typical_height*1.2]
        line_left = min([o['x1']] + [p['x1'] for p in peers])
        line_right = max([o['x2']] + [p['x2'] for p in peers])
        supporting_text = any(
            p['ocr_id'] != o['ocr_id'] and p['y1'] < o['y1']
            and p['y2']-p['y1'] >= text_height*1.6
            and -.3*text_height <= o['y1']-p['y2'] <= text_height
            and abs((p['x1']+p['x2']-line_left-line_right)/2)
                < .3*max(p['x2']-p['x1'], line_right-line_left)
            for p in text_items)
        if nearby and not (o.get('underlined') or o.get('link_hint')):
            kind = 'Label'
        elif o.get('underlined') or o.get('link_hint') or o['ocr_id'] in nav_text_ids or any(d['class'] == 'Link' and (d.get('confidence') or 0) >= .4
                                          and intersection(d, o)/max(1, area(o)) >= .6
                                          for d in detections):
            kind = 'Link'
        elif supporting_text:
            kind = 'Paragraph'
        elif text_height >= typical_height*1.5:
            kind = 'Heading'
        elif o['y1']-top < typical_height*3:
            kind = 'Subheading'
        c = {**text_box(o), 'id': f'ocr-{o["ocr_id"]}', 'class': kind,
             'texts': [o.get('display_text', o['text'])], 'ocr': [o], 'confidence': o['confidence'],
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
                and -typical_height*.15 <= c['x1']-prev['x2'] <= typical_height*(.45 if c['class'] == 'Link' else 1.2)):
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
