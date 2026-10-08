from functools import lru_cache


@lru_cache(maxsize=1)
def get_reader():
    # Loaded once on first conversion; health routes can start without downloads.
    import easyocr
    return easyocr.Reader(['en'])


def extract_text(image_path):
    results = get_reader().readtext(str(image_path), paragraph=False)
    return [{'text': text, 'confidence': round(float(confidence), 3),
             'box': [[int(p[0]), int(p[1])] for p in box]}
            for box, text, confidence in results]


def extract_text_with_links(image_path):
    """Underline geometry can separate a link accidentally merged into prose.

    This does not guess words. Crops are sent back to the same EasyOCR reader.
    Raw OCR is returned separately for auditing.
    """
    import cv2
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("Could not read the OCR image.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    raw = extract_text(image_path)
    refined = []
    for o in raw:
        x, y = map(min, zip(*o['box']))
        x2, y2 = map(max, zip(*o['box']))
        x, y = max(0, x), max(0, y)
        x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
        h, w = y2-y, x2-x
        if h <= 0 or w <= 0:
            refined.append(o)
            continue
        # Real underlines are long, thin connected ink components. Letter
        # baselines and the border of the next field must not count as links.
        region = ink[y:y2, x:x2]
        _, _, stats, _ = cv2.connectedComponentsWithStats(region)
        spans = [tuple(map(int, r[:4])) for r in stats[1:]
                 if r[1] >= h*.60 and r[2] >= max(16, h*.4)
                 and r[3] <= max(4, h*.12) and r[2]/max(1, r[3]) > 6]
        if not spans:
            refined.extend(split_colour_run(image, o))
            continue
        lx = min(s[0] for s in spans)
        lw = max(s[0]+s[2] for s in spans)-lx
        split = None
        if lx > w*.35 and lw < w*.65:
            # Look for a word gap before the underline, excluding the underline itself.
            start = max(0, int(lx-h*1.5))
            band = ink[y:int(y+h*.62), x+start:x+lx]
            blank = (band > 0).sum(axis=0) == 0
            runs, begin = [], None
            for i, empty in enumerate(list(blank)+[False]):
                if empty and begin is None: begin = i
                if not empty and begin is not None:
                    runs.append((i-begin, start+(i+begin)//2)); begin = None
            if runs and max(runs)[0] > h*.12:
                split = x + max(runs)[1]
        if split:
            replacements = []
            for a, b, link in [(x, split, False), (split, x2, True)]:
                pad = 6
                left, top = max(0, a-pad), max(0, y-pad)
                region = image[top:min(image.shape[0], y2+pad), left:min(image.shape[1], b+pad)]
                for box, text, confidence in get_reader().readtext(region, paragraph=False):
                    replacements.append({'text': text.replace('_', ' ') if link else text,
                                         'confidence': round(float(confidence), 3),
                                         'box': [[int(p[0])+left, int(p[1])+top] for p in box],
                                         'underlined': link, 'source': 'ocr-underline-crop'})
            # Never discard an OCR result if either side cannot be reread.
            if (any(r['underlined'] for r in replacements)
                    and any(not r['underlined'] for r in replacements)
                    and same_text(o['text'], replacements)):
                refined.extend(replacements)
                continue
        # A failed partial split must not turn the entire sentence into a link.
        if lw >= w*.65:
            refined.append({**o, 'underlined': True, 'text': o['text'].replace('_', ' ')})
        else:
            refined.append(o)
    # Uniform colour alone does not establish a link. Expose it to mapping,
    # which requires a nearby contrasting inline run or an underline as well.
    refined = [dict(item) for item in refined]
    for item in refined:
        xs, ys = zip(*item['box'])
        crop = image[max(0,min(ys)):min(image.shape[0],max(ys)),
                     max(0,min(xs)):min(image.shape[1],max(xs))]
        if crop.size:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            visible = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) < 210
            saturated = (hsv[:,:,1] > 110) & (hsv[:,:,2] > 60)
            if visible.sum() > 0 and (saturated & visible).sum()/visible.sum() > .6 and saturated.mean() < .35:
                item['coloured_text'] = True
    refined.extend(recover_grid_numbers(image, refined))
    refined.extend(recover_aligned_numbers(image, refined))
    refined = retry_email_lines(image, refined)
    return raw, refined


def _recover_email_at(original, views):
    """Recover only @ when two crop readings agree on its location.

    Confidence belongs to the run containing @, not unrelated domain runs.
    All other original characters are retained; this is not address validation.
    """
    import re
    from difflib import SequenceMatcher
    compact = re.sub(r'\s+', '', original)
    if '@' in compact or len(views) != 2:
        return None
    evidence = []
    letters = lambda value: ''.join(c for c in value.casefold() if c.isalnum())
    for view in views:
        candidate = view['candidate']
        if candidate.count('@') != 1:
            return None
        prefix, suffix = candidate.split('@')
        at_runs = [run for run in view['runs'] if '@' in run['text']]
        if (len(at_runs) != 1 or not prefix or not suffix
                or float(at_runs[0]['confidence']) < .6
                or SequenceMatcher(None, letters(compact), letters(candidate)).ratio() < .85):
            return None
        evidence.append((prefix, suffix, float(at_runs[0]['confidence'])))
    first, second = evidence
    if (first[0].casefold() != second[0].casefold()
            or letters(first[1]) != letters(second[1])
            or max(first[2], second[2]) < .7):
        return None
    boundary = len(first[0])
    if compact[:boundary].casefold() != first[0].casefold():
        return None
    remainder = compact[boundary:]
    # A stray apostrophe at exactly the reread @ position may be replaced.
    # Do not remove punctuation elsewhere or infer a missing domain dot.
    if remainder.startswith(("'", "’")):
        remainder = remainder[1:]
    if not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', remainder):
        return None
    return compact[:boundary] + '@' + remainder


def retry_email_lines(image, existing):
    """Retry fragmented email-like lines without inventing a missing @ symbol.

    Two unconstrained OCR views must agree on a complete address, or support
    only the missing @ at the same position. Keep raw OCR and replaced runs.
    """
    import cv2
    import re
    from difflib import SequenceMatcher
    if image is None:
        return list(existing)
    email = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+")
    def bounds(item):
        xs,ys=zip(*item['box'])
        return min(xs),min(ys),max(xs),max(ys)
    groups=[]
    for index,item in sorted(enumerate(existing),key=lambda pair:(bounds(pair[1])[0],bounds(pair[1])[1])):
        x,y,r,b=bounds(item);h=max(1,b-y)
        target=None
        for group in groups:
            previous=existing[group[-1]];px,py,pr,pb=bounds(previous)
            unit=min(h,pb-py)
            if (unit>0 and -.4*unit <= x-pr <= 1.2*unit
                    and min(b,pb)-max(y,py)>=.5*unit
                    and abs(y+b-py-pb)/2<=.5*unit):
                target=group
                break
        if target is None:
            groups.append([index])
        else:
            target.append(index)
    replacements={};consumed=set();attempts=0
    for group in groups:
        items=[existing[i] for i in group]
        text=''.join(str(o['text']) for o in items)
        compact=re.sub(r'\s+','',text)
        if (email.fullmatch(compact) or not re.search(r'[A-Za-z0-9-]+\.[A-Za-z]{2,}',compact)
                or len(compact)>254 or any(o.get('separate_run') for o in items)):
            continue
        if attempts>=12:
            break
        attempts+=1
        boxes=[bounds(o) for o in items]
        x,y,r,b=min(q[0] for q in boxes),min(q[1] for q in boxes),max(q[2] for q in boxes),max(q[3] for q in boxes)
        pad=max(2,round((b-y)*.12))
        crop=image[max(0,y-pad):min(image.shape[0],b+pad),max(0,x-pad):min(image.shape[1],r+pad)]
        if not crop.size:
            continue
        gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        enhanced=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
        views=[cv2.resize(crop,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC),
               cv2.resize(enhanced,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)]
        candidates=[]
        diagnostic={'original_text':text, 'views':[], 'status':'rejected'}
        for view_name,view in zip(('colour_2x','contrast_3x'),views):
            results=get_reader().readtext(view,detail=1,paragraph=False)
            ordered=sorted(results,key=lambda v:min(p[0] for p in v[0]))
            candidate=re.sub(r'\s+','',''.join(v[1] for v in ordered))
            confidence=min((float(v[2]) for v in results),default=0.0)
            old_letters=re.sub(r'[^a-z0-9]','',compact.lower())
            new_letters=re.sub(r'[^a-z0-9]','',candidate.lower())
            similarity=SequenceMatcher(None,old_letters,new_letters).ratio()
            if not results:
                reason='no_text'
            elif confidence<.7:
                reason='low_confidence'
            elif not email.fullmatch(candidate):
                reason='not_complete_email'
            elif similarity<.85:
                reason='text_changed_too_much'
            else:
                reason='eligible'
                candidates.append((candidate,confidence))
            diagnostic['views'].append({
                'view':view_name, 'candidate':candidate,
                'confidence':round(confidence,4), 'similarity':round(similarity,4),
                'reason':reason,
                'runs':[{'text':str(v[1]),'confidence':round(float(v[2]),4)} for v in ordered]})
        if len(candidates)==2 and candidates[0][0]==candidates[1][0]:
            accepted_text=candidates[0][0]
            accepted_confidence=min(c[1] for c in candidates)
            diagnostic.update(status='accepted',reason='two_views_agree')
            source='ocr-email-line-retry'
        else:
            accepted_text=_recover_email_at(text,diagnostic['views'])
            if accepted_text is None:
                diagnostic['reason']='views_disagree' if len(candidates)==2 else 'ineligible_reading'
                replacements[group[0]]={**existing[group[0]],'email_retry':diagnostic}
                continue
            # Retain the original confidence: recovering punctuation does not
            # make the uncorrected letters more certain.
            accepted_confidence=min(float(o.get('confidence',0)) for o in items)
            diagnostic.update(status='partial',reason='two_views_agree_on_at',
                              recovered_text=accepted_text)
            source='ocr-email-at-retry'
        replacements[group[0]]={
            'text':accepted_text, 'confidence':round(accepted_confidence,3),
            'box':[[int(x),int(y)],[int(r),int(y)],[int(r),int(b)],[int(x),int(b)]],
            'source':source, 'original_runs':[dict(o) for o in items],
            'email_retry':diagnostic}
        for flag in ('underlined', 'link_hint', 'coloured_text'):
            if all(o.get(flag) for o in items):
                replacements[group[0]][flag] = True
        consumed.update(group[1:])
    return [replacements.get(i,o) for i,o in enumerate(existing) if i not in consumed]


def recover_grid_numbers(image, existing):
    """Retry missed numeric text in ruled tables, without inventing sequences.

    Long intersecting lines establish cells. At least two recognised numeric
    cells establish a numeric column. Only otherwise empty cells with compact
    ink are reread. The raw full-image OCR remains unchanged for auditing.
    """
    import cv2
    import numpy as np
    import re
    heights = [max(p[1] for p in o['box'])-min(p[1] for p in o['box'])
               for o in existing]
    heights = [h for h in heights if h > 0]
    if not heights:
        return []
    unit = float(np.median(heights))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    def grid_cells(line_ink):
        horizontal = cv2.morphologyEx(line_ink, cv2.MORPH_OPEN,
                                     np.ones((1, max(15, round(unit*4))), np.uint8))
        vertical = cv2.morphologyEx(line_ink, cv2.MORPH_OPEN,
                                   np.ones((max(15, round(unit*4)), 1), np.uint8))
        grid = cv2.bitwise_or(horizontal, vertical)
        gap = max(2, round(unit*.12))
        grid = cv2.morphologyEx(grid, cv2.MORPH_CLOSE, np.ones((gap, gap), np.uint8))
        contours, _ = cv2.findContours(grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cells = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if (1.2*unit <= w <= 18*unit and 1.2*unit <= h <= 5*unit
                    and cv2.contourArea(contour) >= w*h*.8):
                cells.append((x, y, w, h))
        # Several aligned closed cells are required, not isolated form controls.
        return [c for c in cells if sum(
            abs(d[1]-c[1]) < unit*.3 and abs(d[3]-c[3]) < unit*.3
            for d in cells) >= 3]

    cells = grid_cells(ink)
    if not cells:
        # Slightly slanted hand-drawn lines can disappear under a long, thin
        # opening kernel. Thicken only the grid-analysis copy as a fallback.
        # Glyph crops below still use the untouched original image and ink.
        thickness = max(3, min(9, round(unit*.14))) | 1
        cells = grid_cells(cv2.dilate(ink, np.ones((thickness, thickness), np.uint8)))
    columns = []
    for cell in sorted(cells):
        group = next((g for g in columns if abs(g[0][0]-cell[0]) < unit*.3
                      and abs(g[0][2]-cell[2]) < unit*.3), None)
        if group is None:
            columns.append([cell])
        else:
            group.append(cell)

    def content(cell):
        x, y, w, h = cell
        return [o for o in existing if x <= sum(p[0] for p in o['box'])/4 <= x+w
                and y <= sum(p[1] for p in o['box'])/4 <= y+h]

    additions, attempts = [], 0
    numeric = re.compile(r'[0-9]+(?:[.,][0-9]+)*')
    for column in columns:
        if len(column) < 3 or sum(len(content(c)) == 1 and bool(
                numeric.fullmatch(content(c)[0]['text'].strip())) for c in column) < 2:
            continue
        # Use observed cell contents to establish an integer column. Exclude
        # its top cell (the header); do not infer values from row positions.
        body_text = [o['text'].strip() for cell in sorted(column, key=lambda c: c[1])[1:]
                     for o in content(cell)]
        integer_column = len(body_text) >= 2 and all(
            re.fullmatch(r'[0-9]+', text) for text in body_text)
        for x, y, w, h in sorted(column, key=lambda c: c[1]):
            if content((x, y, w, h)) or attempts >= 24:
                continue
            pad = max(3, round(unit*.18))
            left, top = x+pad, y+pad
            region = ink[top:y+h-pad, left:x+w-pad]
            if not region.size:
                continue
            _, _, stats, _ = cv2.connectedComponentsWithStats(region)
            marks = [r for r in stats[1:] if r[4] >= max(3, unit*unit*.012)]
            if not marks or len(marks) > 8:
                continue
            a = min(r[0] for r in marks); b = min(r[1] for r in marks)
            c = max(r[0]+r[2] for r in marks); d = max(r[1]+r[3] for r in marks)
            # Reject border fragments, wide illustrations and tiny dust marks.
            if not (.35*unit <= d-b <= 1.8*unit and c-a <= 6*unit
                    and a > 0 and b > 0 and c < region.shape[1] and d < region.shape[0]):
                continue
            attempts += 1
            crop = image[top+b:top+d, left+a:left+c]
            readings = []
            unrestricted_text = []
            for factor in (3, 4):
                enlarged = cv2.resize(crop, None, fx=factor, fy=factor,
                                      interpolation=cv2.INTER_CUBIC)
                border = max(8, round(unit*.3*factor))
                enlarged = cv2.copyMakeBorder(enlarged, border, border, border, border,
                                             cv2.BORDER_CONSTANT, value=(255, 255, 255))
                # Use EasyOCR's recogniser on the bounded crop directly: its
                # full-page text detector is what can miss isolated small glyphs.
                result = get_reader().recognize(enlarged, detail=1, paragraph=False)
                if len(result) != 1:
                    break
                _, text, confidence = result[0]
                text = text.strip()
                unrestricted_text.append(text)
                if not numeric.fullmatch(text):
                    break
                readings.append((text, float(confidence)))
            source = 'ocr-grid-cell-retry'
            matching = len(readings) == 2 and readings[0][0] == readings[1][0]
            agreed = matching and min(r[1] for r in readings) >= .70
            # Resizing can reduce confidence without changing the recognised
            # digit. In this tightly bounded case retain a strong reading when
            # a second view independently returns the same digit moderately well.
            # Keep the minimum confidence in the trace, not the strongest score.
            narrow_integer = (integer_column and len(marks) == 1
                              and (c-a) <= .85*(d-b))
            if (not agreed and matching and narrow_integer
                    and re.fullmatch(r'[0-9]', readings[0][0])
                    and max(r[1] for r in readings) >= .95
                    and min(r[1] for r in readings) >= .60):
                agreed = True
                source = 'ocr-grid-consensus-retry'
            # A thin isolated digit is easily confused with I/l by unrestricted
            # OCR. Retry only a single compact glyph in an established integer
            # column, never an arbitrary icon, word, or multi-symbol cell.
            # Digit restriction changes the recogniser vocabulary, not the value:
            # two differently processed views must still agree at high confidence.
            if (not agreed and narrow_integer
                    and all(not t or re.fullmatch(r'[0-9Il|]', t)
                            for t in unrestricted_text)):
                readings = []
                gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                _, binary_crop = cv2.threshold(
                    gray_crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                for view, factor in ((gray_crop, 4), (binary_crop, 5)):
                    enlarged = cv2.resize(view, None, fx=factor, fy=factor,
                                          interpolation=cv2.INTER_CUBIC)
                    border = max(12, round((d-b)*factor*.5))
                    enlarged = cv2.copyMakeBorder(enlarged, border, border, border, border,
                                                 cv2.BORDER_CONSTANT, value=255)
                    result = get_reader().recognize(
                        enlarged, detail=1, paragraph=False, allowlist='0123456789')
                    if len(result) != 1:
                        break
                    _, text, confidence = result[0]
                    text = text.strip()
                    if not re.fullmatch(r'[0-9]', text) or float(confidence) < .90:
                        break
                    readings.append((text, float(confidence)))
                source = 'ocr-grid-numeric-retry'
                agreed = len(readings) == 2 and readings[0][0] == readings[1][0]
            if agreed:
                additions.append({'text': readings[0][0],
                                  'confidence': round(min(r[1] for r in readings), 3),
                                  'box': [[int(left+a), int(top+b)], [int(left+c), int(top+b)],
                                          [int(left+c), int(top+d)], [int(left+a), int(top+d)]],
                                  'source': source})
    return additions


def recover_aligned_numbers(image, existing):
    """Reread isolated ink above captions in an established row of counters.

    Geometry proposes a crop; two unrestricted EasyOCR readings must agree.
    No sequence, caption vocabulary or expected numeric value is assumed.
    """
    import cv2
    import re
    numeric = re.compile(r'[0-9]+(?:[.,][0-9]+)*%?')
    def bounds(o):
        return (min(p[0] for p in o['box']), min(p[1] for p in o['box']),
                max(p[0] for p in o['box']), max(p[1] for p in o['box']))
    numbers = [bounds(o) for o in existing if numeric.fullmatch(o['text'].strip())]
    if len(numbers) < 2:
        return []
    captions = [bounds(o) for o in existing if sum(c.isalpha() for c in o['text']) >= 4]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink)
    additions = []
    attempts = 0
    for x, y, w, h, pixels in stats[1:]:
        x, y, w, h = map(int, (x, y, w, h))
        if h < 8 or not .15 <= w/max(1, h) <= 1.3 or pixels < w*h*.08:
            continue
        # Already-read text, icons and controls must not be read a second time.
        if any(max(0, min(x+w, r)-max(x, l))*max(0, min(y+h, b)-max(y, t))
               > .1*w*h for l, t, r, b in map(bounds, existing)):
            continue
        peers = [(l, t, r, b) for l, t, r, b in numbers
                 if .65*h <= b-t <= 1.6*h
                 and abs((t+b)/2-(y+h/2)) < .35*h
                 and (r < x-2*h or l > x+w+2*h)]
        if len(peers) < 2:
            continue
        # The candidate lies within a supported number row and has its own
        # caption below it, aligned to the left like the neighbouring counters.
        if not min(l for l, _, _, _ in peers) < x < max(r for _, _, r, _ in peers):
            continue
        def has_caption(l, t, r, b):
            unit = b-t
            return any(abs(a-l) < .4*unit and 0 <= c-b <= 1.2*unit
                       and d-a > max(r-l, unit) for a, c, d, _ in captions)
        if not has_caption(x, y, x+w, y+h) or sum(has_caption(*p) for p in peers) < 2:
            continue
        attempts += 1
        pad = max(4, round(h*.25))
        crop = gray[y:y+h, x:x+w]
        readings = []
        for factor in (3, 4):
            enlarged = cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
            enlarged = cv2.copyMakeBorder(enlarged, pad*factor, pad*factor, pad*factor, pad*factor,
                                          cv2.BORDER_CONSTANT, value=255)
            found = get_reader().recognize(enlarged, detail=1, paragraph=False)
            if len(found) != 1:
                break
            _, text, confidence = found[0]
            text = text.strip()
            if not numeric.fullmatch(text) or float(confidence) < .8:
                break
            readings.append((text, float(confidence)))
        if len(readings) == 2 and readings[0][0] == readings[1][0]:
            additions.append({'text': readings[0][0],
                              'confidence': round(min(c for _, c in readings), 3),
                              'box': [[x, y], [x+w, y], [x+w, y+h], [x, y+h]],
                              'source': 'ocr-aligned-number-retry'})
        # Bound extra recognition work on dense sketches.
        if attempts >= 12:
            break
    return additions


def same_text(original, pieces):
    """Reject rereads that drop text; allow limited glyph substitutions."""
    import re
    normalize = lambda value: re.sub(r"[\W_]+", "", value.casefold())
    before = normalize(original)
    after = normalize(' '.join(p['text'] for p in pieces))
    # Allow a small number of glyph substitutions (e.g. l/u), but never drop
    # characters/words. Raw text is retained separately in the API trace.
    return len(before) == len(after) and sum(a != b for a,b in zip(before,after)) <= len(before)//12


def split_colour_run(image, item):
    """Separate contrasting inline text only when rereading preserves the text.

    Colour is a link hint, not proof. Mapping retains this provenance. Uniformly
    coloured headings/buttons are left intact. No particular hue or word is used.
    """
    import cv2
    import numpy as np
    xs, ys = zip(*item['box'])
    x, y = max(0, min(xs)), max(0, min(ys))
    x2, y2 = min(image.shape[1], max(xs)), min(image.shape[0], max(ys))
    crop = image[y:y2, x:x2]
    if not crop.size or x2-x < 3*(y2-y):
        return [item]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # Ignore lightly coloured backgrounds and require visible coloured ink.
    colour = (hsv[:, :, 1] > 110) & (hsv[:, :, 2] > 60)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    dark = gray < 180
    h, w = gray.shape
    if colour.mean() > .35 or not np.any(dark):
        return [item]
    columns = np.flatnonzero(colour.sum(axis=0) >= max(2, h*.08))
    if len(columns) < h*.3:
        return [item]
    groups = []
    for col in columns:
        if not groups or col-groups[-1][-1] > h*.65:
            groups.append([int(col)])
        else:
            groups[-1].append(int(col))
    spans = [(g[0], g[-1]+1) for g in groups if g[-1]-g[0] >= h*.6]
    if not spans or sum(b-a for a,b in spans) > w*.85:
        return [item]
    cuts = {0, w}
    blank = ~dark.any(axis=0) & ~colour.any(axis=0)
    for a,b in spans:
        for edge in (a,b):
            if edge < h*.3 or w-edge < h*.3:
                continue
            # A one-pixel inter-letter gap is not a boundary between words.
            # Require whitespace wide enough for a word gap before rereading.
            starts = np.flatnonzero(np.diff(np.r_[False, blank, False].astype(int)) == 1)
            ends = np.flatnonzero(np.diff(np.r_[False, blank, False].astype(int)) == -1)
            candidates = [int((a+b)//2) for a,b in zip(starts, ends)
                          if b-a >= max(3, h*.15)
                          and abs((a+b)/2-edge) <= h*.5]
            if not candidates:
                return [item]
            cuts.add(min(candidates, key=lambda v: abs(v-edge)))
    cuts = sorted(cuts)
    if len(cuts) < 3:
        return [item]
    pieces = []
    for a,b in zip(cuts,cuts[1:]):
        if b-a < 2:
            return [item]
        pad = 3
        left, top = max(0,x+a-pad), max(0,y-pad)
        region = image[top:min(image.shape[0],y2+pad), left:min(image.shape[1],x+b+pad)]
        results = get_reader().readtext(region, paragraph=False)
        if not results:
            return [item]
        hint = any(min(b,r)-max(a,l) > (b-a)*.5 for l,r in spans)
        for box,text,confidence in results:
            pieces.append({'text': text, 'confidence': round(float(confidence),3),
                           'box': [[int(pt[0]+left), int(pt[1]+top)] for pt in box],
                           'source': 'ocr-colour-crop', 'separate_run': True,
                           'link_hint': hint})
    return pieces if (same_text(item['text'], pieces)
                      and ''.join(ch.casefold() for ch in item['text'] if ch.isalnum())
                      == ''.join(ch.casefold() for p in pieces for ch in p['text'] if ch.isalnum())) else [item]
