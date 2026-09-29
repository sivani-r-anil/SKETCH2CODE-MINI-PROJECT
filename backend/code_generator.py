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
        'page': '#eff6ff', 'surface': '#ffffff', 'text': '#172554',
        'muted': '#1e40af', 'border': '#3b82f6', 'soft': '#dbeafe',
        'soft-hover': '#bfdbfe', 'accent': '#1d4ed8',
        'accent-hover': '#1e40af', 'on-accent': '#ffffff',
    },
}

FOCUS = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--s2c-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--s2c-surface)]'


def theme_css():
    rules = []
    for name, tokens in THEMES.items():
        declarations = ';'.join(f'--s2c-{key}:{value}' for key, value in tokens.items())
        scheme = 'dark' if name == 'dark' else 'light'
        rules.append(f'.sketch-page[data-sketch-theme="{name}"]{{{declarations};color-scheme:{scheme}}}')
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
        return f'<h2 className="text-lg text-[var(--s2c-muted)]" style={{{{textAlign: {js(align)}}}}}>{value}</h2>'
    if kind == 'Paragraph':
        return f'<p className="text-sm text-[var(--s2c-muted)]" style={{{{textAlign: {js(align)}}}}}>{value}</p>'
    if kind == 'Label':
        return f'<label htmlFor={{{js(c.get("for_id", ""))}}} className="block text-sm font-medium text-[var(--s2c-text)]">{value}</label>'
    if kind in {'Textbox', 'Password box'}:
        input_type = 'password' if kind == 'Password box' else c.get('input_type', 'text')
        return f'<input id={ident} type="{input_type}" placeholder={value} aria-label={{{js(c.get("label") or text or "Text input")}}} className="w-full min-w-0 border border-[var(--s2c-border)] rounded-lg px-4 py-3 bg-[var(--s2c-surface)] placeholder:text-[var(--s2c-muted)] {focus}" />'
    if kind == 'Button' and c.get('filled'):
        return f'<button type="button" className="w-full rounded-lg bg-[var(--s2c-accent)] text-[var(--s2c-on-accent)] px-4 py-3 font-medium hover:bg-[var(--s2c-accent-hover)] transition-colors {focus}">{value}</button>'
    if kind == 'Button':
        return f'<button type="button" className="w-full border border-[var(--s2c-border)] bg-[var(--s2c-soft)] hover:bg-[var(--s2c-soft-hover)] rounded-lg px-4 py-3 font-medium transition-colors {focus}">{value if text else "Button"}</button>'
    if kind in {'Check Box', 'Radio Button'}:
        input_type = 'checkbox' if kind == 'Check Box' else 'radio'
        return f'<label className="inline-flex items-center gap-2 text-sm cursor-pointer"><input type="{input_type}" name={{{js(c.get("group", "choice"))}}} className="w-4 h-4 shrink-0 accent-[var(--s2c-accent)] {focus}" /><span>{value}</span></label>'
    if kind == 'Link':
        return f'<a href="#" className="text-sm text-[var(--s2c-accent)] underline underline-offset-4 rounded-sm {focus}">{value}</a>'
    if kind == 'Textarea':
        return f'<textarea id={ident} aria-label={{{js(c.get("label") or text or "Text area")}}} placeholder={value} rows={{4}} className="w-full border border-[var(--s2c-border)] rounded-lg p-3 bg-[var(--s2c-surface)] text-[var(--s2c-text)] placeholder:text-[var(--s2c-muted)] {focus}" />'
    if kind == 'Select':
        return f'<select id={ident} aria-label={{{js(c.get("label") or text or "Select option")}}} className="w-full border border-[var(--s2c-border)] rounded-lg p-3 bg-[var(--s2c-surface)] text-[var(--s2c-text)] {focus}"><option>{value if text else "Select"}</option></select>'
    if kind in {'Image', 'Carousel'}:
        src = image_source(c)
        if src:
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

    def cell_content(cell):
        if cell.get('kind') == 'component':
            return generate_component(cell['component'])
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


def render_layout_tree(node, scale):
    """Render geometric groups in normal flow; never position controls absolutely."""
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
        links = ''.join('<div className="shrink-0">' + render_layout_tree(c, scale) + '</div>'
                        for c in children[1:])
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
            classes += 's2c-card-row grid-cols-1 sm:grid-cols-2 lg:grid-cols-[var(--s2c-tracks)] items-stretch'
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
    for child in children:
        gap = round(min(64, max(0, child['y1']-bottom)*scale))
        bottom = max(bottom, child['y2'])
        left = max(0, (child['x1']-node['x1'])/width*100)
        child_width = min(100-left, max(1, (child['x2']-child['x1'])/width*100))
        # OCR heading widths describe ink, not a restrictive text container.
        text_kind = child.get('component', {}).get('class')
        if text_kind in {'Heading', 'Subheading'}:
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
        for row in region.get('rows', []):
            gap = round(min(64, row.get('gap_before', 16)*scale))
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
