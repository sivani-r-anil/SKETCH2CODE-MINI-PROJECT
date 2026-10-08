"""Run from backend: python -m unittest discover -s tests -p test_svg_icons.py -v"""
import copy
import unittest
import code_generator as g

CROP = 'data:image/png;base64,iVBORw0KGgo='


def caption(text):
    return {'class': 'Paragraph', 'texts': [text], 'ocr': [
        {'text': text, 'confidence': .95, 'box': [[40, 0], [140, 0], [140, 24], [40, 24]]}]}


def inline(text):
    return {**caption(text), 'icon_image_src': CROP,
            'icon_box': {'x1': 0, 'y1': 0, 'x2': 24, 'y2': 24}}


class SvgIconTests(unittest.TestCase):
    def test_semantic_variations(self):
        for text, icon in [('All members', 'Users'), ('Recent documents', 'FileText'),
                           ('Completed tasks', 'CircleCheck'), ('Upcoming appointments', 'CalendarDays'),
                           ('My preferences', 'Settings'), ('Notifications', 'Bell'),
                           ('Security', 'LockKeyhole'), ('Profile', 'UserRound'),
                           ('Search', 'Search'), ('Email', 'Mail'), ('Password', 'Lock'),
                           ('Edit', 'Pencil'), ('Delete', 'Trash2')]:
            with self.subTest(text=text):
                self.assertEqual(g.semantic_icon(caption(text)), icon)

    def test_unknown_ambiguous_and_brand_fallback(self):
        for text in ('Custom workspace', 'Google', 'GitHub', 'Email notifications',
                     'Security reports', 'Profile photo', 'Do not delete', 'Searchlight'):
            with self.subTest(text=text):
                output = g.inline_artwork(inline(text))
                self.assertIn('<img ', output)
                self.assertNotIn('data-lucide', output)
                self.assertIn(CROP, output)

    def test_geometry_and_confidence_required(self):
        for change in ('large', 'far', 'low', 'no_box', 'no_crop', 'existing_icon'):
            c = inline('Profile')
            if change == 'large': c['icon_box']['y2'] = 150
            elif change == 'far': c['icon_box']['x1'], c['icon_box']['x2'] = -150, -126
            elif change == 'low': c['ocr'][0]['confidence'] = .2
            elif change == 'no_box': c.pop('icon_box')
            elif change == 'no_crop': c.pop('icon_image_src')
            else: c['icon'] = 'custom'
            with self.subTest(change=change):
                self.assertNotIn('data-lucide', g.inline_artwork(c))

    def test_inline_svg_is_self_contained_and_keeps_input(self):
        c = inline('Notifications'); original = copy.deepcopy(c)
        jsx = g.generate_component(c)
        self.assertEqual(c, original)
        self.assertIn('data-lucide={"Bell"}', jsx)
        self.assertIn('stroke="currentColor"', jsx)
        self.assertIn('aria-hidden="true"', jsx)
        self.assertIn('h-8 w-8', jsx)
        self.assertNotIn('import ', jsx)
        self.assertIn('Lucide', jsx)

    def test_large_images_and_placeholders_unchanged(self):
        c = {**caption('Profile'), 'class': 'Image', 'image_src': CROP}
        self.assertIn('<img ', g.generate_component(c))
        c.pop('image_src')
        self.assertIn('role="img"', g.generate_component(c))
        self.assertNotIn('data-lucide', g.generate_component(c))

    def test_known_action_icons_preserved(self):
        for name in ('edit', 'delete'):
            jsx = g.generate_component({'class': 'Button', 'icon': name, 'texts': []})
            self.assertIn(g.action_icon(name), jsx)
            self.assertNotIn('data-lucide', jsx)

    def test_stat_icon_requires_compact_crop_inside_parent(self):
        picture = {'x1': 10, 'y1': 20, 'x2': 70, 'y2': 80,
                   'component': {'class': 'Image', 'image_src': CROP, 'asset_source': 'wireframe-crop'}}
        label = {'component': caption('All members')}
        parent = {'x1': 0, 'y1': 0, 'x2': 300, 'y2': 120}
        self.assertEqual(g.stat_icon_match(picture, label, parent), 'Users')
        picture['x2'] = 260
        self.assertIsNone(g.stat_icon_match(picture, label, parent))
        picture['x2'] = 70
        picture['component']['alt'] = 'Company logo'
        self.assertIsNone(g.stat_icon_match(picture, label, parent))


if __name__ == '__main__':
    unittest.main()
