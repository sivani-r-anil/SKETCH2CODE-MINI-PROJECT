"""Render mapped semantics; classification belongs in mapping.py, never here."""
import json
import re


# All generated-page colours live here. Tailwind classes refer to these tokens.
THEMES = {
    'light': {
        'page': '#f8fafc', 'surface': '#ffffff', 'text': '#0f172a',
        'muted': '#475569', 'border': '#64748b', 'soft': '#f1f5f9',
        'soft-hover': '#e2e8f0', 'accent': '#1d4ed8',
        'accent-hover': '#1e40af', 'on-accent': '#ffffff',
    },
    'dark': {
        'page': '#020617', 'surface': '#0f172a', 'text': '#f8fafc',
        'muted': '#cbd5e1', 'border': '#94a3b8', 'soft': '#1e293b',
        'soft-hover': '#334155', 'accent': '#93c5fd',
        'accent-hover': '#bfdbfe', 'on-accent': '#0f172a',
    },
    'blue': {
        'page': '#152d60', 'surface': '#1c396e', 'text': '#f7f9fc',
        'muted': '#c8d5e8', 'border': '#7890b4', 'soft': '#25467b',
        'soft-hover': '#30558a', 'accent': '#b8cbe5',
        'accent-hover': '#d0dded', 'on-accent': '#152d60',
        'wireframe-surface': '#193465',
    },
    'purple-gradient': {
        'page': '#c4b5fd', 'surface': '#faf5ff', 'text': '#2e1065',
        'muted': '#5b467a', 'border': '#8060a8', 'soft': '#ede9fe',
        'soft-hover': '#ddd6fe', 'accent': '#6d28d9',
        'accent-hover': '#5b21b6', 'on-accent': '#ffffff',
        'wireframe-surface': 'rgba(250,245,255,.64)',
        'page-image': 'linear-gradient(125deg,#ddd6fe 0%,#a78bfa 52%,#f0abfc 100%)',
        'accent-image': 'linear-gradient(110deg,#7e22ce,#6d28d9,#4338ca)',
        'accent-hover-image': 'linear-gradient(110deg,#6b21a8,#5b21b6,#3730a3)',
    },
    'ocean-gradient': {
        'page': '#102d60', 'surface': '#f4fafb', 'text': '#12344b',
        'muted': '#3d606e', 'border': '#658995', 'soft': '#e2f0f2',
        'soft-hover': '#cde5e9', 'accent': '#17677a',
        'accent-hover': '#125368', 'on-accent': '#ffffff',
        'wireframe-surface': 'rgba(244,250,251,.96)',
        'page-image': 'linear-gradient(180deg,#65d0ce 0%,#299ead 35%,#135178 68%,#102d60 100%)',
    },
    'sunset-gradient': {
        'page': '#fed7aa', 'surface': '#fff7ed', 'text': '#431407',
        'muted': '#79433f', 'border': '#a45e62', 'soft': '#ffe4e6',
        'soft-hover': '#fed7aa', 'accent': '#b01655',
        'accent-hover': '#9d174d', 'on-accent': '#ffffff',
        'wireframe-surface': 'rgba(255,247,237,.64)',
        'page-image': 'linear-gradient(125deg,#fdba74 0%,#fecaca 38%,#f9a8d4 76%,#ddd6fe 100%)',
        'accent-image': 'linear-gradient(110deg,#c2410c,#be185d)',
        'accent-hover-image': 'linear-gradient(110deg,#9a3412,#9d174d)',
    },
}

FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--s2c-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--s2c-surface)]'


def theme_css():
    rules = []
    for name, tokens in THEMES.items():
        # Image tokens are separate from colours: background-color, text,
        # borders and form controls must never receive a CSS gradient value.
        values = {'page-image': 'none', 'accent-image': 'none',
                  'accent-hover-image': 'none',
                  'wireframe-surface': tokens['surface'], **tokens}
        declarations = ';'.join(f'--s2c-{key}:{value}' for key, value in values.items())
        scheme = 'dark' if name in {'dark', 'blue'} else 'light'
        rules.append(f'.sketch-page[data-sketch-theme="{name}"]{{{declarations};color-scheme:{scheme}}}')
    rules.extend([
        '.sketch-page{background-image:var(--s2c-page-image,none)}',
        # Only the outer canvas is translucent. Nested cards, inputs and table
        # rows continue to use solid surface/soft tokens for readable content.
        '.sketch-page>.wireframe{background-color:var(--s2c-wireframe-surface,var(--s2c-surface))}',
        '.sketch-page .s2c-primary{background-image:var(--s2c-accent-image,none)}',
        '.sketch-page .s2c-primary:hover{background-image:var(--s2c-accent-hover-image,none)}',
    ])
    return '\n'.join(rules)


def image_source(c):
    # Embedded PNG/JPEG/WebP crops work in srcDoc and downloaded JSX without
    # requiring the backend URL. Reject script URLs and untrusted SVG data.
    value = c.get('image_src')
    if not isinstance(value, str):
        return None
    if re.fullmatch(r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}', value):
        return value
    return None


def js(value):
    # JSON expressions preserve braces, quotes and OCR text safely in JSX.
    return json.dumps(value, ensure_ascii=True)


def profile_icon():
    """Decorative account symbol; uses currentColor in every page theme."""
    return ('<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" strokeWidth={1.8} '
            'strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 shrink-0">'
            '<circle cx={12} cy={8} r={3} />'
            '<path d="M5 21v-2a7 7 0 0 1 14 0v2" /></svg>')


def action_icon(name):
    """Render only an action already identified upstream; never infer from text."""
    paths = {
        'edit': '<path d="m16 3 5 5-12 12-6 1 1-6Z" /><path d="m14 5 5 5M4 15l5 5" />',
        'delete': '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7" />',
    }
    if name not in paths:
        return ''
    return ('<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" strokeWidth={1.8} '
            'strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 shrink-0">'
            + paths[name] + '</svg>')


# Pinned Lucide 0.468.0 SVG paths, shared by its React icon package.
# https://github.com/lucide-icons/lucide/tree/0.468.0/icons
LUCIDE_LICENSE = 'ISC License\n\nCopyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other copyright (c) for Lucide are held by Lucide Contributors 2022.\n\nPermission to use, copy, modify, and/or distribute this software for any\npurpose with or without fee is hereby granted, provided that the above\ncopyright notice and this permission notice appear in all copies.\n\nTHE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES\nWITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF\nMERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR\nANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES\nWHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN\nACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF\nOR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.\n'
LUCIDE_PATHS = {'Users': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />', 'Folder': '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />', 'FileText': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" /><path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M10 9H8" /><path d="M16 13H8" /><path d="M16 17H8" />', 'CircleCheck': '<circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" />', 'ChartColumnIncreasing': '<path d="M13 17V9" /><path d="M18 17V5" /><path d="M3 3v16a2 2 0 0 0 2 2h16" /><path d="M8 17v-3" />', 'CalendarDays': '<path d="M8 2v4" /><path d="M16 2v4" /><rect width="18" height="18" x="3" y="4" rx="2" /><path d="M3 10h18" /><path d="M8 14h.01" /><path d="M12 14h.01" /><path d="M16 14h.01" /><path d="M8 18h.01" /><path d="M12 18h.01" /><path d="M16 18h.01" />', 'UserRound': '<circle cx="12" cy="8" r="5" /><path d="M20 21a8 8 0 0 0-16 0" />', 'Settings': '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" />', 'Bell': '<path d="M10.268 21a2 2 0 0 0 3.464 0" /><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326" />', 'LockKeyhole': '<circle cx="12" cy="16" r="1" /><rect x="3" y="10" width="18" height="12" rx="2" /><path d="M7 10V7a5 5 0 0 1 10 0v3" />', 'Search': '<circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />', 'Mail': '<rect width="20" height="16" x="2" y="4" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />', 'Lock': '<rect width="18" height="11" x="3" y="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />', 'Pencil': '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" /><path d="m15 5 4 4" />', 'Trash2': '<path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /><line x1="10" x2="10" y1="11" y2="17" /><line x1="14" x2="14" y1="11" y2="17" />'}


def lucide_svg(name, classes):
    """Self-contained React SVG: no runtime package/import in preview or export."""
    if name not in LUCIDE_PATHS:
        return ''
    return ('<svg data-lucide={' + js(name) + '} aria-hidden="true" focusable="false" '
            'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" strokeWidth={2} strokeLinecap="round" '
            'strokeLinejoin="round" className="' + classes + '">'
            '<metadata>{' + js(LUCIDE_LICENSE) + '}</metadata>' + LUCIDE_PATHS[name] + '</svg>')


def semantic_icon(component):
    """Closed vocabulary for short UI labels; unknown/ambiguous phrases abstain.

    This is label-based semantic matching, not visual icon recognition. Callers
    must independently establish a compact crop and its geometric association.
    """
    text = ' '.join(component.get('texts', [])).strip().casefold()
    if not text or re.search(r'[^a-z\s-]', text):
        return None
    words = set(text.replace('-', ' ').split())
    if len(text.split()) > 5:
        return None
    runs = component.get('ocr', [])
    if not runs or any(float(r.get('confidence', 0)) < .6 for r in runs):
        return None
    groups = {
        'Users': {'student', 'students', 'user', 'users', 'member', 'members', 'staff', 'people'},
        'Folder': {'department', 'departments', 'folder', 'folders', 'directory', 'directories'},
        'FileText': {'project', 'projects', 'document', 'documents', 'file', 'files', 'task', 'tasks'},
        'ChartColumnIncreasing': {'report', 'reports', 'analytics', 'statistics'},
        'CalendarDays': {'calendar', 'calendars', 'deadline', 'deadlines', 'appointment', 'appointments', 'event', 'events'},
        'UserRound': {'profile'}, 'Settings': {'settings', 'preferences'},
        'Bell': {'notification', 'notifications', 'alerts'},
        'LockKeyhole': {'security'}, 'Search': {'search'}, 'Mail': {'email', 'mail'},
        'Lock': {'password'}, 'Pencil': {'edit', 'rename'}, 'Trash2': {'delete', 'remove'},
    }
    modifiers = {'total', 'all', 'my', 'your', 'our', 'new', 'active', 'ongoing',
                 'pending', 'completed', 'complete', 'upcoming', 'generated', 'recent', 'account'}
    matches = [(name, terms) for name, terms in groups.items() if words & terms]
    if len(matches) != 1:
        return None
    name, terms = matches[0]
    if words - terms - modifiers:
        return None
    if name == 'FileText' and words & {'completed', 'complete'}:
        return 'CircleCheck'
    return name


def inline_icon_match(c):
    """Require an existing compact crop immediately left of its OCR label."""
    if c.get('icon') or c.get('class') not in {'Paragraph', 'Button', 'Link', 'Textbox', 'Password box'}:
        return None
    box, runs = c.get('icon_box'), c.get('ocr', [])
    if not isinstance(box, dict) or not runs:
        return None
    try:
        x, y, r, b = (float(box[k]) for k in ('x1', 'y1', 'x2', 'y2'))
        points = [p for run in runs for p in run['box']]
        tx, ty = min(p[0] for p in points), min(p[1] for p in points)
        tr, tb = max(p[0] for p in points), max(p[1] for p in points)
        w, h, th = r-x, b-y, tb-ty
        if (min(w,h,th) <= 0 or not .5 <= w/h <= 1.8
                or h > 2*th or not -.15*th <= tx-r <= 2*th
                or abs((y+b-ty-tb)/2) > .6*max(h,th)):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return semantic_icon(c)


def stat_icon_match(picture, caption, parent):
    """A small square-ish picture inside an already reconstructed number card."""
    c = picture['component']
    if (not image_source(c) or c.get('icon') or c.get('asset_source') != 'wireframe-crop'
            or c.get('alt') not in {None, '', 'Cropped illustration from the uploaded wireframe'}):
        return None
    w, h = picture['x2']-picture['x1'], picture['y2']-picture['y1']
    pw, ph = parent['x2']-parent['x1'], parent['y2']-parent['y1']
    if (min(w,h,pw,ph) <= 0 or not .5 <= w/h <= 1.8
            or w > .38*pw or h > .8*ph
            or picture['x1'] < parent['x1'] or picture['y1'] < parent['y1']
            or picture['x2'] > parent['x2'] or picture['y2'] > parent['y2']):
        return None
    return semantic_icon(caption['component'])

def inline_artwork(c):
    """Replace only confidently associated UI icons; preserve every other crop."""
    src = image_source({'image_src': c.get('icon_image_src')})
    if not src:
        return ''
    size = 'h-6 w-6' if c.get('class') == 'Button' else 'h-8 w-8'
    matched = inline_icon_match(c)
    if matched:
        return lucide_svg(matched, size + ' shrink-0')
    return ('<img src={' + js(src) + '} alt="" aria-hidden="true" '
            'className="' + size + ' shrink-0 object-contain" />')


def generate_component(c):
    kind = c.get('class', '')
    text = ' '.join(c.get('texts', [])).strip()
    value = '{' + js(text) + '}'
    ident = '{' + js(c.get('id', 'field')) + '}'
    focus = FOCUS
    align = c.get('align', 'left')
    if kind == 'Field':
        return '<div className="space-y-2">'+''.join(generate_component(child) for child in c['children'])+'</div>'
    if kind == 'Heading':
        return f'<h1 className="text-3xl sm:text-4xl font-bold text-[var(--s2c-text)]" style={{{{textAlign: {js(align)}}}}}>{value}</h1>'
    if kind == 'Subheading':
        return f'<h2 className="text-lg font-semibold text-[var(--s2c-text)]" style={{{{textAlign: {js(align)}}}}}>{value}</h2>'
    if kind == 'Paragraph':
        artwork = inline_artwork(c)
        if artwork:
            return ('<p className="flex min-w-0 items-center gap-3 text-sm text-[var(--s2c-muted)]">'
                    + artwork + '<span className="min-w-0">' + value + '</span></p>')
        return f'<p className="text-sm text-[var(--s2c-muted)]" style={{{{textAlign: {js(align)}}}}}>{value}</p>'
    if kind == 'Label':
        return f'<label htmlFor={{{js(c.get("for_id", ""))}}} className="block text-sm font-medium text-[var(--s2c-text)]">{value}</label>'
    if kind in {'Textbox', 'Password box'}:
        input_type = 'password' if kind == 'Password box' else c.get('input_type', 'text')
        is_search = kind == 'Textbox' and (input_type == 'search' or (
            input_type == 'text' and re.match(r'^search\b', text, re.IGNORECASE)))
        if is_search:
            return ('<div className="relative w-full min-w-0">'
                    '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" '
                    'fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" '
                    'className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--s2c-muted)]">'
                    '<circle cx={10.5} cy={10.5} r={6.5} /><path d="m16 16 4 4" /></svg>'
                    f'<input id={ident} type="search" placeholder={value} '
                    f'aria-label={{{js(c.get("label") or text or "Search")}}} '
                    'className="w-full min-w-0 rounded-lg border border-[var(--s2c-border)] '
                    'bg-[var(--s2c-surface)] py-3 pl-10 pr-4 text-[var(--s2c-text)] '
                    f'placeholder:text-[var(--s2c-muted)] {focus}" /></div>')
        return f'<input id={ident} type="{input_type}" placeholder={value} aria-label={{{js(c.get("label") or text or "Text input")}}} className="w-full min-w-0 border border-[var(--s2c-border)] rounded-lg px-4 py-3 bg-[var(--s2c-surface)] placeholder:text-[var(--s2c-muted)] {focus}" />'
    if kind == 'Button' and c.get('icon') in {'edit', 'delete'}:
        label = c.get('label') or text or c['icon'].title()
        return ('<button type="button" aria-label={' + js(label) + '} title={' + js(label) + '} '
                'className="inline-flex h-9 w-9 shrink-0 items-center justify-center '
                'rounded-md border border-[var(--s2c-border)] bg-[var(--s2c-surface)] '
                'text-[var(--s2c-text)] hover:bg-[var(--s2c-soft-hover)] transition-colors '
                + focus + '">' + action_icon(c['icon']) + '</button>')
    if kind == 'Button' and c.get('filled'):
        artwork = profile_icon() if c.get('icon') == 'profile' else inline_artwork(c)
        content = artwork + '<span className="min-w-0">' + value + '</span>' if artwork else value
        icon_classes = 'inline-flex items-center justify-center gap-2 ' if artwork else ''
        return f'<button type="button" className="s2c-primary {icon_classes}w-full rounded-lg bg-[var(--s2c-accent)] text-[var(--s2c-on-accent)] px-4 py-3 font-medium hover:bg-[var(--s2c-accent-hover)] transition-colors {focus}">{content}</button>'
    if kind == 'Button':
        content = value if text else 'Button'
        icon_classes = ''
        artwork = profile_icon() if c.get('icon') == 'profile' else inline_artwork(c)
        if artwork:
            content = artwork + '<span className="min-w-0">' + content + '</span>'
            icon_classes = 'inline-flex items-center justify-center gap-2 '
        return f'<button type="button" className="{icon_classes}w-full border border-[var(--s2c-border)] bg-[var(--s2c-soft)] hover:bg-[var(--s2c-soft-hover)] rounded-lg px-4 py-3 font-medium transition-colors {focus}">{content}</button>'
    if kind in {'Check Box', 'Radio Button'}:
        input_type = 'checkbox' if kind == 'Check Box' else 'radio'
        # Use an initial state, not a controlled `checked` prop: the generated
        # control must remain editable without requiring a React state handler.
        # Missing or ambiguous evidence preserves the previous unchecked output.
        initial_state = ' defaultChecked={true}' if c.get('checked') is True else ''
        return f'<label className="inline-flex items-center gap-2 text-sm cursor-pointer"><input type="{input_type}" name={{{js(c.get("group", "choice"))}}}{initial_state} className="w-4 h-4 shrink-0 accent-[var(--s2c-accent)] {focus}" /><span>{value}</span></label>'
    if kind == 'Link':
        return f'<a href="#" className="text-sm text-[var(--s2c-accent)] underline underline-offset-4 rounded-sm {focus}">{value}</a>'
    if kind == 'Textarea':
        return f'<textarea id={ident} aria-label={{{js(c.get("label") or text or "Text area")}}} placeholder={value} rows={{4}} className="w-full border border-[var(--s2c-border)] rounded-lg p-3 bg-[var(--s2c-surface)] text-[var(--s2c-text)] placeholder:text-[var(--s2c-muted)] {focus}" />'
    if kind == 'Select':
        return f'<select id={ident} aria-label={{{js(c.get("label") or text or "Select option")}}} className="w-full border border-[var(--s2c-border)] rounded-lg p-3 bg-[var(--s2c-surface)] text-[var(--s2c-text)] {focus}"><option>{value if text else "Select"}</option></select>'
    if kind == 'Pagination':
        # Pagination is already a detected semantic component. Render standard
        # directional controls and only page labels actually supplied by OCR.
        # Never infer a missing numeric sequence or pretend additional data exists.
        labels = []
        for fragment in c.get('texts', []):
            labels.extend(re.findall(r'\d+|\.{3}|…', fragment))
        classes = ('inline-flex h-9 min-w-9 shrink-0 items-center justify-center '
                   'rounded-md border border-[var(--s2c-border)] px-2 '
                   'bg-[var(--s2c-surface)] text-sm text-[var(--s2c-text)] '
                   'hover:bg-[var(--s2c-soft-hover)] ' + focus)
        def direction(label, path):
            return ('<button type="button" aria-label={' + js(label) + '} className="'
                    + classes + '"><svg aria-hidden="true" focusable="false" '
                    'viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} '
                    'strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">'
                    '<path d={' + js(path) + '} /></svg></button>')
        parts = [direction('Previous page', 'm14 6-6 6 6 6')]
        for label in labels:
            if label in {'...', '…'}:
                parts.append('<span className="px-1 text-[var(--s2c-muted)]">{' + js(label) + '}</span>')
            else:
                parts.append('<button type="button" aria-label={' + js('Page '+label)
                             + '} className="' + classes + '">{' + js(label) + '}</button>')
        parts.append(direction('Next page', 'm10 6 6 6-6 6'))
        return ('<nav aria-label="Pagination" className="flex min-w-0 flex-wrap '
                'items-center justify-end gap-2">' + ''.join(parts) + '</nav>')
    if kind in {'Image', 'Carousel'}:
        src = image_source(c)
        if src:
            display_width = c.get('display_width')
            if isinstance(display_width, (int, float)) and 0 < display_width <= 1200:
                return (f'<img src={{{js(src)}}} alt={{{js(c.get("alt") or text or "Wireframe image region")}}} '
                        'className="block h-auto max-w-full object-contain" '
                        'style={' + js({'width': round(display_width)}) + '} loading="lazy" />')
            return f'<img src={{{js(src)}}} alt={{{js(c.get("alt") or text or "Wireframe image region")}}} className="block w-full h-auto object-contain rounded-lg" loading="lazy" />'
        return f'<div role="img" aria-label={{{js(text or kind)}}} className="min-h-24 border border-dashed border-[var(--s2c-border)] rounded-lg flex items-center justify-center text-[var(--s2c-muted)]">{value if text else kind}</div>'
    return f'<div className="border border-dashed border-[var(--s2c-border)] p-2 text-sm text-[var(--s2c-muted)]">{value if text else "{"+js(kind)+"}"}</div>'



def _uses_hierarchy(node):
    """Keep the established single-card renderer unless structural groups exist."""
    if not node:
        return False
    if node.get('kind') == 'columns':
        return True
    if node.get('kind') == 'container' and node.get('container_class') in {'Card', 'Panel', 'Section'}:
        return True
    return any(_uses_hierarchy(child) for child in node.get('children', []))


def _is_inline_text_row(children):
    """Only nearby prose/link fragments share a line; independent items keep tracks."""
    if len(children) < 2 or any(c.get('kind') != 'component' for c in children):
        return False
    kinds = [c['component'].get('class') for c in children]
    allowed = {'Paragraph', 'Label', 'Link', 'Check Box', 'Radio Button'}
    if not all(k in allowed for k in kinds):
        return False
    # A navigation row of links or a row of independent choices is not prose.
    if 'Link' not in kinds or not any(k in {'Paragraph', 'Label', 'Check Box', 'Radio Button'} for k in kinds):
        return False
    if sum(k in {'Check Box', 'Radio Button'} for k in kinds) > 1:
        return False
    for left, right in zip(children, children[1:]):
        height = max(1, min(left['y2']-left['y1'], right['y2']-right['y1']))
        gap = right['x1']-left['x2']
        overlap = min(left['y2'], right['y2'])-max(left['y1'], right['y1'])
        if gap < -height*.25 or gap > height*.9 or overlap < height*.5:
            return False
    return True


def render_table(node):
    """Render the layout's cells; never invent missing values or action labels."""
    rows = node.get('children', [])
    edges = node.get('column_edges', [])
    if not rows or len(edges) < 2:
        return '<div />'
    count = len(edges)-1
    width = max(1, edges[-1]-edges[0])
    min_width = max(320, count*112)
    # Keep compact action groups inside their inferred column on narrow screens;
    # the existing table wrapper supplies horizontal scrolling when necessary.
    for row in rows:
        for col, cell in enumerate(row.get('children', [])[:count]):
            controls = cell.get('children', [])
            if (cell.get('kind') == 'row' and controls and all(
                    c.get('component', {}).get('class') == 'Button'
                    and c['component'].get('icon') in {'edit', 'delete'} for c in controls)):
                proportion = max(1, edges[col+1]-edges[col])/width
                needed = 36*len(controls) + 8*(len(controls)-1) + 26
                min_width = max(min_width, int(needed/proportion)+1)

    def cell_content(cell):
        if cell.get('kind') == 'component':
            return generate_component(cell['component'])
        children = cell.get('children', [])
        if cell.get('kind') == 'row' and children and all(
                child.get('kind') == 'component'
                and child.get('component', {}).get('class') == 'Button'
                and child['component'].get('icon') in {'edit', 'delete'}
                for child in children):
            return '<div className="flex flex-nowrap items-center gap-2">' + ''.join(
                cell_content(child) for child in children) + '</div>'
        # Cell children share normal flow; page-coordinate margins do not belong
        # inside a table cell. Keep any mapped controls and images interactive.
        return '<div className="flex flex-col gap-2">' + ''.join(
            cell_content(child) for child in cell.get('children', [])) + '</div>'

    parts = [
        '<div data-layout-kind="table" role="region" aria-label="Reconstructed table" '
        'tabIndex={0} className="w-full min-w-0 max-w-full overflow-x-auto rounded-lg '
        'border border-[var(--s2c-border)] ' + FOCUS + '">',
        '<table className="w-full table-fixed border-collapse text-left text-sm '
        'text-[var(--s2c-text)]" style={{minWidth: ' + str(min_width) + '}}>',
        '<colgroup>',
    ]
    for left, right in zip(edges, edges[1:]):
        proportion = max(0, right-left)/width*100
        parts.append('<col style={{width: ' + js(f'{proportion:.3f}%') + '}} />')
    parts.append('</colgroup><tbody>')
    for row_index, row in enumerate(rows):
        background = 'bg-[var(--s2c-surface)]' if row_index % 2 == 0 else 'bg-[var(--s2c-soft)]'
        parts.append('<tr className="' + background + '">')
        for cell in row.get('children', []):
            parts.append('<td className="border border-[var(--s2c-border)] px-3 py-3 '
                         'align-top whitespace-normal [overflow-wrap:anywhere]">')
            parts.append(cell_content(cell))
            parts.append('</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div>')
    return '\n'.join(parts)


def _render_icon_sidebar(node, scale):
    """Center contents of a narrow sidebar containing repeated icon rows."""
    if node['y2']-node['y1'] <= 1.3*max(1,node['x2']-node['x1']):
        return None
    def flatten(part):
        if part.get('kind') == 'component':
            return [part]
        if part.get('kind') != 'stack':
            return None
        items=[]
        for child in part.get('children', []):
            group=flatten(child)
            if group is None:
                return None
            items.extend(group)
        return items
    items=[]
    for child in node.get('children', []):
        group=flatten(child)
        if group is None:
            return None
        items.extend(group)
    if (sum(bool(p['component'].get('icon_image_src')) for p in items)<3
            or any(p['component'].get('class') not in
                   {'Paragraph','Heading','Subheading','Link','Image'} for p in items)):
        return None
    items.sort(key=lambda p:(p['y1'],p['x1']))
    parts=['<aside data-layout-kind="icon-sidebar" className="min-w-0 rounded-xl border '
           'border-[var(--s2c-border)] bg-[var(--s2c-surface)] p-4 sm:p-6 shadow-sm text-center">']
    bottom=items[0]['y1']
    for i,part in enumerate(items):
        icon_row = bool(part['component'].get('icon_image_src'))
        previous_icon = i > 0 and bool(items[i-1]['component'].get('icon_image_src'))
        if icon_row and not previous_icon:
            parts.append('<div className="mx-auto w-max max-w-full text-left">')
        c={**part['component'],'align':'left' if icon_row else 'center'}
        gap=min(40,max(0,round((part['y1']-bottom)*scale)))
        if i:
            gap=max(8,gap)
        bottom=max(bottom,part['y2'])
        style={'marginTop':gap}
        if c['class']=='Image':
            style['width']=max(48,min(112,round((part['x2']-part['x1'])*scale)))
            classes='mx-auto max-w-full'
        elif icon_row:
            classes='w-full min-w-0 text-left'
        else:
            classes='flex w-full min-w-0 justify-center text-center'
        parts.append('<div className="'+classes+'" style={'+js(style)+'}>'
                     +generate_component(c)+'</div>')
        next_icon = i+1 < len(items) and bool(items[i+1]['component'].get('icon_image_src'))
        if icon_row and not next_icon:
            parts.append('</div>')
    return ''.join(parts)+'</aside>'


def _render_text_card(node, scale):
    """Render a simple caption/description card without OCR ink-width columns.

    One image above the caption can share this flow. Mixed controls, nested
    containers and multi-column cards keep the normal hierarchy renderer.
    """
    def flatten(part):
        if part.get('kind') == 'component':
            return [part]
        if part.get('kind') != 'stack':
            return None
        result = []
        for child in part.get('children', []):
            items = flatten(child)
            if items is None:
                return None
            result.extend(items)
        return result
    items = []
    for child in node.get('children', []):
        group = flatten(child)
        if group is None:
            return None
        items.extend(group)
    if not items or any(p['component'].get('class') not in
                        {'Paragraph', 'Heading', 'Subheading', 'Image'} for p in items):
        return None
    # Inline artwork belongs to its own row, not a flattened description.
    # Keep the spatial renderer for icon lists even when a title is present.
    if any(p['component'].get('icon_image_src') or p['component'].get('icon')
           for p in items):
        return None
    items.sort(key=lambda p: (p['y1'], p['x1']))
    headings = [i for i, p in enumerate(items)
                if p['component']['class'] in {'Heading', 'Subheading'}]
    if len(headings) != 1:
        return None
    index = headings[0]
    title, before, after = items[index], items[:index], items[index+1:]
    pictures = [p for p in items if p['component']['class'] == 'Image']
    if (len(pictures) > 1 or any(p not in before or p['y2'] > title['y1']
                                or not image_source(p['component']) for p in pictures)):
        return None
    if len(after) < 2 or any(p['y1'] < title['y1'] for p in after):
        return None
    width = max(1, node['x2']-node['x1'])
    centered = all(abs((p['x1']+p['x2']-node['x1']-node['x2'])/2)
                   <= width*.15 for p in items)
    align = 'center' if centered else 'left'
    # Retain the sketch's space above the caption, even when an icon was
    # missed. Any existing OCR in that region remains visible for inspection.
    leading = max(0, min(96, round((title['y1']-node['y1'])*scale)-24))
    prefix = ''.join(generate_component({**p['component'], 'align': align}) for p in before)
    heading = generate_component({**title['component'], 'align': align})
    if pictures:
        prefix_parts = []
        for part in before:
            if part['component']['class'] == 'Image':
                # The original crop is embedded in JSX, so preview and export
                # use the same asset. Bound its display size, not its pixels.
                size = max(48, min(96, round((part['x2']-part['x1'])*scale)))
                margin = 'mx-auto ' if centered else ''
                prefix_parts.append('<div className="' + margin
                                    + 'mb-4 max-w-full" style={' + js({'width': size}) + '}>'
                                    + generate_component(part['component']) + '</div>')
            else:
                prefix_parts.append(generate_component({**part['component'], 'align': align}))
        prefix = ''.join(prefix_parts)
        # Reserve two caption lines so descriptions in neighbouring cards do
        # not jump upward when one caption fits on a single line.
        heading = '<div className="min-h-14">' + heading + '</div>'
    description = ' '.join(t for p in after for t in p['component'].get('texts', []))
    return ('<section data-layout-kind="text-card" className="min-w-0 rounded-xl border '
            'border-[var(--s2c-border)] bg-[var(--s2c-surface)] p-6 shadow-sm" '
            'style={' + js({'textAlign': align}) + '}>'
            '<div className="flex flex-col justify-start" style={' +
            js({'minHeight': leading}) + '}>' + prefix + '</div>'
            + heading
            + '<p className="mt-2 text-sm leading-6 text-[var(--s2c-muted)]">{'
            + js(description) + '}</p></section>')


def _render_stat_card(node, scale):
    """Keep a numeric value and its caption together beside an optional image."""
    def leaves(part):
        if part.get('kind') == 'component':
            return [part]
        if part.get('kind') not in {'stack', 'row', 'columns'}:
            return None
        result = []
        for child in part.get('children', []):
            group = leaves(child)
            if group is None:
                return None
            result.extend(group)
        return result
    items = []
    for child in node.get('children', []):
        group = leaves(child)
        if group is None:
            return None
        items.extend(group)
    images = [p for p in items if p['component'].get('class') == 'Image']
    text = sorted([p for p in items if p['component'].get('class') in
                   {'Heading', 'Subheading', 'Paragraph'}], key=lambda p: p['y1'])
    if len(text) != 2 or len(images) > 1 or len(items) != len(text)+len(images):
        return None
    number, caption = text
    value = ' '.join(number['component'].get('texts', [])).strip()
    label = ' '.join(caption['component'].get('texts', [])).strip()
    width = max(1, node['x2']-node['x1'])
    if (not re.fullmatch(r'[0-9]+(?:[.,][0-9]+)*%?', value)
            or not any(ch.isalpha() for ch in label)
            or caption['y1'] <= number['y1']
            or abs(number['x1']-caption['x1']) > width*.2):
        return None
    artwork = ''
    if images:
        picture = images[0]
        if picture['x2'] > min(number['x1'], caption['x1'])+width*.08:
            return None
        size = max(48, min(96, round((picture['x2']-picture['x1'])*scale)))
        matched = stat_icon_match(picture, caption, node)
        rendered = (lucide_svg(matched, 'block w-full h-auto text-[var(--s2c-muted)]')
                    if matched else generate_component(picture['component']))
        artwork = ('<div className="shrink-0" style={' + js({'width': size}) + '}>'
                   + rendered + '</div>')
    return ('<section data-layout-kind="stat-card" className="flex min-w-0 min-h-36 '
            'items-center gap-4 rounded-xl border border-[var(--s2c-border)] '
            'bg-[var(--s2c-surface)] p-6 shadow-sm">' + artwork
            + '<div className="min-w-0"><p className="text-4xl sm:text-5xl font-medium '
            'leading-tight tabular-nums text-[var(--s2c-text)]">{' + js(value) + '}</p>'
            '<p className="mt-2 text-sm leading-6 text-[var(--s2c-muted)]">{'
            + js(label) + '}</p></div></section>')


def _centered_title_group(child, parent):
    """Identify an already-grouped title/subtitle centred over a wider section."""
    parts = child.get('children', [])
    if (child.get('kind') != 'stack' or len(parts) != 2
            or any(p.get('kind') != 'component' for p in parts)
            or parts[0]['component'].get('class') not in {'Heading', 'Subheading'}
            or parts[1]['component'].get('class') != 'Paragraph'):
        return False
    width = max(1, parent['x2']-parent['x1'])
    centre = (parent['x1']+parent['x2'])/2
    return (child['x2']-child['x1'] < width*.7
            and all(abs((p['x1']+p['x2'])/2-centre) < width*.08 for p in parts)
            and parts[1]['y1'] >= parts[0]['y1'])


def _align_form_stack(node):
    """Regularize small sketch offsets within an established horizontal form.

    Work on a rendering copy: detections and the reconstructed tree stay intact.
    Repeated label/control pairs provide the shared columns, never OCR words.
    """
    from copy import deepcopy
    from statistics import median
    if node.get('kind') != 'stack':
        return node
    rows = [c for c in node.get('children', [])
            if c.get('kind') == 'row' and c.get('role') == 'form-row'
            and len(c.get('children', [])) == 2]
    if len(rows) < 2:
        return node
    controls = [r['children'][1] for r in rows]
    unit = median(max(1, c['y2']-c['y1']) for c in controls)
    tolerance = .6*unit
    left = node['x1']
    label_right = median(r['children'][0]['x2'] for r in rows)
    control_left = median(c['x1'] for c in controls)
    right = median(c['x2'] for c in controls)
    if (not left < label_right < control_left < right
            or any(abs(r['x1']-left) > tolerance for r in rows)
            or any(abs(c['x1']-control_left) > tolerance
                   or abs(c['x2']-right) > tolerance for c in controls)):
        return node
    aligned = deepcopy(node)
    def align_intro(part):
        children = part.get('children', [])
        if (part.get('kind') == 'stack' and children
                and all(c.get('kind') == 'component'
                        and c.get('component', {}).get('class') in {'Heading', 'Subheading', 'Paragraph'}
                        and abs(c['x1']-left) <= tolerance for c in children)):
            part['x1'] = left
            for c in children:
                c['x1'] = left
    for child in aligned.get('children', []):
        if child.get('kind') == 'row' and child.get('role') == 'form-row':
            child['x1'], child['x2'] = left, right
            label, control = child['children']
            label['x1'], label['x2'] = left, label_right
            control['x1'], control['x2'] = control_left, right
        elif abs(child['x1']-left) <= tolerance:
            align_intro(child)
            if child.get('kind') == 'component':
                child['x1'] = left
    return aligned


def render_layout_tree(node, scale):
    """Render geometric groups in normal flow; never position controls absolutely."""
    node = _align_form_stack(node)
    kind = node.get('kind', 'stack')
    children = node.get('children', [])
    if kind == 'component':
        return generate_component(node['component'])
    if kind == 'field':
        return '<div className="flex min-w-0 flex-col gap-2">' + ''.join(
            render_layout_tree(child, scale) for child in children) + '</div>'
    if node.get('role') == 'table':
        return render_table(node)
    if kind == 'container':
        sidebar = _render_icon_sidebar(node, scale)
        if sidebar is not None:
            return sidebar
        if node.get('container_class') == 'Card':
            card = _render_stat_card(node, scale)
            if card is not None:
                return card
            card = _render_text_card(node, scale)
            if card is not None:
                return card
        # A container is represented once, with its actual descendants inside.
        caption = ' '.join(node.get('component', {}).get('texts', [])).strip()
        heading = ('<p className="mb-3 font-semibold">{' + js(caption) + '}</p>') if caption else ''
        return '<section className="min-w-0 rounded-xl border border-[var(--s2c-border)] bg-[var(--s2c-surface)] p-4 sm:p-6 shadow-sm">' + heading + ''.join(
            render_layout_tree(child, scale) for child in children) + '</section>'
    if not children:
        return '<div />'

    # A branding element followed by multiple links is a navigation group.
    # Link count alone is insufficient: inline policy/account links stay prose.
    navigation = (kind == 'row' and len(children) >= 3
                  and all(c.get('kind') == 'component' for c in children)
                  and children[0]['component'].get('class') in {'Heading', 'Subheading'}
                  and sum(c['component'].get('class') == 'Link' for c in children[1:]) >= 2
                  and all(c['component'].get('class') in {'Link', 'Button'} for c in children[1:]))
    if navigation:
        brand = render_layout_tree(children[0], scale)
        items = []
        for child in children[1:]:
            component = child['component']
            label = ' '.join(component.get('texts', [])).strip().casefold()
            # A requested visual enhancement for existing account buttons only.
            # Do not reclassify links, add controls, or alter the input layout.
            if (component.get('class') == 'Button' and not component.get('icon')
                    and label in {'admin', 'administrator', 'profile', 'account', 'my account'}):
                rendered = generate_component({**component, 'icon': 'profile'})
            else:
                rendered = render_layout_tree(child, scale)
            items.append('<div className="shrink-0">' + rendered + '</div>')
        links = ''.join(items)
        return ('<header data-layout-kind="navigation" className="flex flex-wrap items-center '
                'justify-between gap-x-8 gap-y-4 border-b border-[var(--s2c-border)] pb-4 mb-4">'
                '<div className="shrink-0 max-w-full break-normal [&>h1]:text-2xl '
                '[&>h2]:text-2xl [&>h1]:font-bold [&>h2]:font-bold">' + brand + '</div>'
                '<nav aria-label="Main navigation" className="flex flex-wrap items-center '
                'justify-end gap-x-6 gap-y-3">' + links + '</nav></header>')

    if kind == 'row' and _is_inline_text_row(children):
        # Ink widths are not text container widths. Inline flow lets sentences
        # wrap naturally while keeping each link and choice interactive.
        fragments = [render_layout_tree(child, scale) for child in children]
        return ('<div data-layout-kind="inline" className="min-w-0 text-sm leading-6 '
                '[&>p]:inline [&>label]:inline [&>label>input]:mr-2">'
                + '{" "}'.join(fragments) + '</div>')

    if kind in {'row', 'columns'}:
        widths = [max(1, child['x2']-child['x1']) for child in children]
        tracks = ' '.join(f'minmax(0,{round(width, 3)}fr)' for width in widths)
        gaps = [max(0, b['x1']-a['x2']) for a, b in zip(children, children[1:])]
        gap = min(64, max(8, round(sum(gaps)/max(1, len(gaps))*scale)))
        classes = 'grid min-w-0 items-start gap-3 '
        card_row = kind == 'row' and len(children) >= 2 and all(
            child.get('kind') == 'container' and child.get('role') != 'table'
            and child.get('container_class') in {'Card', 'Panel', 'Section'}
            for child in children)
        if card_row:
            # Preserve inferred proportions on desktop; use readable card widths
            # on smaller viewports. The card count comes from the layout tree.
            classes += 's2c-card-row pb-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-[var(--s2c-tracks)] items-stretch'
        elif kind == 'columns':
            classes += 'grid-cols-1 md:grid-cols-[var(--s2c-tracks)]'
        else:
            classes += 's2c-tree-row grid-cols-[var(--s2c-tracks)] items-center'
        style = js({'--s2c-tracks': tracks, 'columnGap': gap})
        parts = [f'<div data-layout-kind="{kind}" className="{classes}" style={{{style}}}>']
        for child in children:
            # Preserve vertical offsets on desktop; remove them when columns stack.
            offset = round(max(0, child['y1']-node['y1'])*scale) if kind == 'columns' else 0
            child_style = js({'--s2c-offset': f'{offset}px'})
            wrapper = 'min-w-0 md:pt-[var(--s2c-offset)]'
            if card_row:
                wrapper += ' flex flex-col [&>section]:h-full'
            parts.append(f'<div className="{wrapper}" style={{{child_style}}}>')
            parts.append(render_layout_tree(child, scale))
            parts.append('</div>')
        parts.append('</div>')
        return '\n'.join(parts)

    # Vertical sections retain their gaps and relative horizontal alignment.
    width = max(1, node['x2']-node['x1'])
    bottom = node['y1']
    parts = ['<div data-layout-kind="stack" className="flex min-w-0 flex-col">']
    for index, child in enumerate(children):
        gap = round(min(64, max(0, child['y1']-bottom)*scale))
        # OCR boxes may touch even when a title and its supporting sentence
        # should breathe. Apply a small semantic minimum without moving groups.
        previous = children[index-1] if index else {}
        if (previous.get('component', {}).get('class') in {'Heading', 'Subheading'}
                and child.get('component', {}).get('class') == 'Paragraph'):
            gap = max(8, gap)
        bottom = max(bottom, child['y2'])
        if _centered_title_group(child, node):
            title, subtitle = child['children']
            parts.append('<div data-layout-kind="section-intro" className="w-full '
                         'space-y-2 pb-4 text-center" style={' + js({'marginTop': gap}) + '}>'
                         + generate_component({**title['component'], 'align': 'center'})
                         + generate_component({**subtitle['component'], 'align': 'center'})
                         + '</div>')
            continue
        left = max(0, (child['x1']-node['x1'])/width*100)
        child_width = min(100-left, max(1, (child['x2']-child['x1'])/width*100))
        # OCR heading widths describe ink, not a restrictive text container.
        text_kind = child.get('component', {}).get('class')
        if text_kind in {'Heading', 'Subheading'}:
            centered = (child.get('component', {}).get('align') == 'center'
                        and abs((child['x1']+child['x2']-node['x1']-node['x2'])/2)
                            <= width*.12)
            if centered:
                left = 0
            child_width = 100-left
        elif text_kind == 'Paragraph' and child_width >= 60:
            # Long prose uses the available width in its existing parent.
            # Narrow counters/captions and all controls retain their geometry.
            child_width = 100-left
        style = js({'marginTop': gap, '--s2c-left': f'{left:.3f}%',
                    '--s2c-width': f'{child_width:.3f}%'})
        parts.append(f'<div className="min-w-0 w-full md:ml-[var(--s2c-left)] md:w-[var(--s2c-width)]" style={{{style}}}>')
        parts.append(render_layout_tree(child, scale))
        parts.append('</div>')
    parts.append('</div>')
    return '\n'.join(parts)

def generate_react_code(layout, theme='light'):
    # The original one-argument API still works. The frontend will switch this
    # literal attribute in Monaco's current code, without rerunning inference.
    theme = theme if theme in THEMES else 'light'
    width = layout.get('page', {}).get('width', 800)
    max_width = max(400, min(1100, round(width*.70)+64))
    scale = min(.70, (max_width-64)/max(1, width))
    lines = ['function GeneratedPage() {', '  return (',
             f'    <main data-sketch-theme="{theme}" className="sketch-page min-h-screen bg-[var(--s2c-page)] px-4 py-8 text-[var(--s2c-text)]">',
             f'      <section className="wireframe mx-auto w-full bg-[var(--s2c-surface)] border border-[var(--s2c-border)] rounded-2xl p-6 sm:p-8" style={{{{maxWidth: {max_width}}}}}>',
             '        <style>{`',
             '          .wireframe .sketch-row { display:grid; grid-template-columns:repeat(24,minmax(0,1fr)); align-items:center; }',
             '          .wireframe .sketch-cell { min-width:0; overflow-wrap:anywhere; grid-column:var(--start) / span var(--span); }',
             '          @media(max-width:700px) { .wireframe .sketch-row { display:flex; flex-wrap:wrap; gap:12px; } .wireframe .sketch-cell { flex:1 1 max(120px,var(--mobile-width)); } }',
             '        `}</style>']
    lines.insert(4, '      <style>{' + js(theme_css()) + '}</style>')

    def render_rows(region):
        nonlocal lines
        region_items = [c for r in region.get('rows', []) for c in r['components']]
        region_left = min((c['x1'] for c in region_items), default=0)
        region_right = max((c['x2'] for c in region_items), default=1)
        previous = []
        for row in region.get('rows', []):
            gap = round(min(64, row.get('gap_before', 16)*scale))
            # OCR ink boxes can touch or overlap although a heading and its
            # supporting line still need a small readable gap in normal flow.
            if (len(previous) == 1 and previous[0].get('class') == 'Heading'
                    and len(row['components']) == 1
                    and row['components'][0].get('class') == 'Paragraph'):
                gap = max(8, gap)
            previous = row['components']
            children = [dict(kind='component', component=c,
                             **{k: c[k] for k in ('x1', 'y1', 'x2', 'y2')})
                        for c in row['components']]
            if _is_inline_text_row(children):
                # Nearby prose and its link are one sentence, including in the
                # established single-column renderer used by simple forms.
                left = min(c['x1'] for c in children)
                right = max(c['x2'] for c in children)
                centered = abs((left+right-region_left-region_right)/2) < .07*max(1, region_right-region_left)
                align = 'center' if centered else 'left'
                node = dict(kind='row', children=children)
                lines.append('<div style={' + js({'marginTop': gap, 'textAlign': align}) + '}>'
                             + render_layout_tree(node, scale) + '</div>')
                continue
            lines.append(f'        <div className="sketch-row" style={{{{marginTop: {gap}}}}}>')
            for c in row['components']:
                start, span = c.get('grid_start', 1), c.get('grid_span', 24)
                mobile_width = '100%' if span >= 14 else f'{round(span/24*100)}%'
                style = js({'--start': start, '--span': span, '--mobile-width': mobile_width})
                lines += [f'          <div className="sketch-cell" style={{{style}}}>',
                          '            '+generate_component(c), '          </div>']
            lines.append('        </div>')
    if _uses_hierarchy(layout.get('tree')):
        lines.append('<style>{` .s2c-hierarchy h1 {font-size:28px;line-height:1.2} .s2c-hierarchy {overflow-wrap:anywhere} @media(max-width:639px){.s2c-hierarchy .s2c-tree-row:has(h1){display:flex;flex-wrap:wrap;gap:12px}.s2c-hierarchy .s2c-tree-row:has(h1)>div{flex:1 1 auto}.s2c-hierarchy .s2c-tree-row:has(h1)>div:has(h1){flex-basis:100%}} `}</style>')
        lines.append('<div className="s2c-hierarchy">')
        lines.append(render_layout_tree(layout['tree'], scale))
        lines.append('</div>')
    elif layout.get('mode') == 'columns':
        lines.append('<style>{` .wireframe:has(.sketch-columns) h1 {font-size:28px;line-height:1.2} .wireframe:has(.sketch-columns) .sketch-row {column-gap:4px} .wireframe:has(.sketch-columns) a {white-space:nowrap} .sketch-columns {display:grid;grid-template-columns:var(--columns);align-items:start;} @media(max-width:760px){.wireframe:has(.sketch-columns) .sketch-cell:has(>h1){flex-basis:100%}.sketch-columns{grid-template-columns:1fr!important}.sketch-column{padding-top:0!important}} `}</style>')
        render_rows(layout['header'])
        widths = [c['page']['width'] for c in layout['columns']]
        style = js({'--columns': ' '.join(f'minmax(0,{w}fr)' for w in widths),
                    'gap': min(80, round(layout['column_gap']*scale)),
                    'marginTop': round(layout['body_gap']*scale)})
        lines.append(f'<div className="sketch-columns" style={{{style}}}>')
        for column in layout['columns']:
            offset = round(column['offset_top']*scale)
            lines.append(f'<div className="sketch-column" style={{{{paddingTop:{offset}}}}}>')
            render_rows(column)
            lines.append('</div>')
        lines.append('</div>')
    else:
        render_rows(layout)
    lines += ['      </section>', '    </main>', '  );', '}', '', 'export default GeneratedPage;']
    return '\n'.join(lines)
