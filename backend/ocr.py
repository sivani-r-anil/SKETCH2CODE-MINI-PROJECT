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
    return raw, refined


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
            candidates = np.flatnonzero(blank[max(0,int(edge-h*.5)):min(w,int(edge+h*.5))])
            if not len(candidates):
                return [item]
            candidates += max(0,int(edge-h*.5))
            cuts.add(int(min(candidates, key=lambda v: abs(v-edge))))
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
                           'box': [[int(pt[0])+left,int(pt[1])+top] for pt in box],
                           'source': 'ocr-colour-crop', 'separate_run': True,
                           'link_hint': hint})
    return pieces if same_text(item['text'],pieces) else [item]
