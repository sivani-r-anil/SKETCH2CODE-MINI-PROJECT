from functools import lru_cache
import easyocr


@lru_cache(maxsize=1)
def get_reader():
    # Loaded once on first conversion; health routes can start without downloads.
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
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    raw = extract_text(image_path)
    refined = []
    for o in raw:
        x, y = map(min, zip(*o['box']))
        x2, y2 = map(max, zip(*o['box']))
        h, w = y2-y, x2-x
        # Real underlines are long, thin connected ink components. Letter
        # baselines and the border of the next field must not count as links.
        region = ink[y:y2, x:x2]
        _, _, stats, _ = cv2.connectedComponentsWithStats(region)
        spans = [tuple(map(int, r[:4])) for r in stats[1:]
                 if r[1] >= h*.60 and r[2] >= max(16, h*.4)
                 and r[3] <= max(4, h*.12) and r[2]/max(1, r[3]) > 6]
        if not spans:
            refined.append(o)
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
            if any(r['underlined'] for r in replacements) and any(not r['underlined'] for r in replacements):
                refined.extend(replacements)
                continue
        refined.append({**o, 'underlined': True, 'text': o['text'].replace('_', ' ')})
    return raw, refined
