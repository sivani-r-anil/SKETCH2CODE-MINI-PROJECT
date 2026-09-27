"""Synthetic regression tests; no model loading, downloads or browser required.

Run from backend: python -m unittest discover -s tests -p "test_pipeline.py" -v
Requires the existing OpenCV/numpy dependencies. These tests do not measure
YOLO/EasyOCR accuracy or replace visual checks with the real wireframe images.
"""
import sys
from copy import deepcopy
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from detection import reconcile_detections
from mapping import map_text_to_components
from layout import reconstruct_layout
from code_generator import generate_react_code, generate_component, render_layout_tree, THEMES
from ocr import same_text


def box(kind, x, y, w, h, **extra):
    return {'class': kind, 'x1': x, 'y1': y, 'x2': x+w, 'y2': y+h,
            'confidence': .8, 'source': 'yolo', **extra}


def text(value, x, y, w, h, **extra):
    return {'text': value, 'box': [[x,y],[x+w,y],[x+w,y+h],[x,y+h]],
            'confidence': .9, **extra}


class PipelineTests(unittest.TestCase):
    def test_unmatched_text_is_preserved(self):
        result = map_text_to_components([], [text('A new title', 20, 20, 100, 30)])
        self.assertEqual(result[0]['texts'], ['A new title'])
        self.assertEqual(result[0]['source'], 'ocr')

    def test_container_does_not_steal_child_text(self):
        result = map_text_to_components([box('Form',0,0,500,500), box('Textbox',20,100,200,40)],
                                        [text('Type your city',30,105,140,25)])
        self.assertFalse(result[0]['texts'])
        self.assertEqual(result[1]['texts'], ['Type your city'])

    def test_ordered_ocr_and_conservative_semantics(self):
        result = map_text_to_components([box('Button',0,50,300,60,outline=True)],
                                        [text('city',160,65,40,25),text('Enter your',15,65,130,25)])
        self.assertEqual(result[0]['texts'], ['Enter your','city'])
        self.assertEqual(result[0]['class'],'Textbox')

    def test_password_link_is_not_an_input(self):
        result = map_text_to_components([box('Link',20,20,200,30)],
                                        [text('Reset password',20,20,200,30,underlined=True)])
        self.assertEqual(result[0]['class'],'Link')

    def test_text_misclassified_as_checkbox_has_no_fake_toggle(self):
        result=map_text_to_components([box('Check Box',20,20,200,40)],
                                      [text('PROFILE',20,20,200,40)],markers=[])
        self.assertEqual(result[0]['texts'],['PROFILE'])
        self.assertNotEqual(result[0]['class'],'Check Box')

    def test_plain_detected_link_is_preserved(self):
        result=map_text_to_components([box('Link',20,20,200,30)],
                                      [text('View details',20,20,200,30)])
        self.assertEqual(result[0]['class'],'Link')

    def test_search_button_is_not_a_placeholder(self):
        result=map_text_to_components([box('Button',0,0,200,40,outline=True)],
                                      [text('Search',40,5,100,30)])
        self.assertEqual(result[0]['class'],'Button')

    def test_split_predictions_merge_on_one_rectangle(self):
        a=box('Textbox',0,0,170,50)
        b=box('Button',140,0,180,50)
        r={'x1':0,'y1':0,'x2':320,'y2':50}
        result=reconcile_detections([a],[b],[r])
        self.assertEqual(len(result),1)
        self.assertEqual(len(result[0]['evidence']),2)

    def test_adjacent_controls_stay_separate(self):
        a=box('Textbox',0,0,100,40);b=box('Textbox',120,0,100,40)
        self.assertEqual(len(reconcile_detections([a,b],[],[a,b])),2)

    def test_rows_preserve_both_columns_and_scale(self):
        items=[box('Label',0,0,80,20),box('Label',300,3,70,20),
               box('Textbox',0,40,200,40),box('Textbox',300,40,100,40)]
        layouts=[]
        for scale in [1,3]:
            scaled=[{k:v*scale if k in {'x1','x2','y1','y2'} else v for k,v in c.items()} for c in items]
            layouts.append(reconstruct_layout(scaled))
        for layout in layouts:
            self.assertEqual([len(r['components']) for r in layout['rows']], [2,2])
        self.assertEqual([[c['grid_start'] for c in r['components']] for r in layouts[0]['rows']],
                         [[c['grid_start'] for c in r['components']] for r in layouts[1]['rows']])

    def test_recovery_requires_filled_outline_and_caption(self):
        r=box('Button',0,100,300,50,filled=True)
        result=map_text_to_components([], [text('Publish draft',60,110,150,25)], rectangles=[r])
        self.assertEqual(result[0]['class'], 'Button')
        self.assertEqual(result[0]['source'], 'opencv+ocr')
        self.assertIsNone(result[0]['confidence'])
        r['filled']=False
        self.assertNotEqual(map_text_to_components([], [text('Publish draft',60,110,150,25)], rectangles=[r])[0]['class'], 'Button')

    def test_missing_square_toggle_recovered_but_letter_rejected(self):
        marker=box('unused',0,0,20,20,square=True)
        result=map_text_to_components([], [text('Keep changes',30,0,140,20)], markers=[marker])
        self.assertEqual(result[0]['class'], 'Check Box')
        self.assertEqual(result[0]['texts'], ['Keep changes'])
        result=map_text_to_components([], [text('Open',0,0,80,20)], markers=[marker])
        self.assertFalse(any(c['class']=='Check Box' for c in result))

    def test_nested_artwork_does_not_create_empty_controls(self):
        result=map_text_to_components([box('Button',0,0,240,180),box('Textbox',30,30,80,60)],[])
        self.assertEqual([c['class'] for c in result], ['Image'])

    def test_group_caption_is_not_one_button(self):
        result=map_text_to_components([box('Button',0,0,600,70),box('Button',450,10,130,40,outline=True)],
            [text('Docs',20,20,70,20),text('Help',200,20,70,20),text('Start',470,20,70,20)])
        self.assertEqual([c['class'] for c in result], ['Link','Link','Button'])

    def test_independent_columns_are_scale_invariant(self):
        items=[box('Heading',0,0,500,30,texts=['Workspace'])]
        for x in (0,350):
            items.extend(box('Paragraph',x,y,150,30,texts=['Content']) for y in (80,180,280))
        for factor in (1,3):
            scaled=[{k:v*factor if k in {'x1','x2','y1','y2'} else v for k,v in c.items()} for c in items]
            layout=reconstruct_layout(scaled)
            self.assertEqual(layout['mode'],'columns')
            self.assertEqual(len(layout['header']['rows']),1)
            self.assertEqual([len(c['rows']) for c in layout['columns']],[3,3])
            self.assertIn('data-layout-kind="columns"', generate_react_code(layout))

    def test_literal_text_is_safe_in_jsx(self):
        layout=reconstruct_layout([box('Heading',0,0,200,40,texts=['{user} <script> "Hello"'])])
        code=generate_react_code(layout)
        self.assertIn('{"{user} <script> \\"Hello\\""}', code)
        self.assertNotIn('position: absolute', code)



class GeneralizationTests(unittest.TestCase):
    def test_mapping_preserves_raw_evidence(self):
        detections = [box('Button', 0, 0, 200, 40, outline=True,
                          corrections=['Original evidence'])]
        words = [text('Enter city', 10, 10, 100, 20)]
        before = deepcopy((detections, words))
        map_text_to_components(detections, words)
        self.assertEqual((detections, words), before)

    def test_each_ocr_segment_assigned_once(self):
        words = [text('Overview', 20, 20, 100, 25),
                 text('Apply', 40, 95, 60, 20),
                 text('Unboxed note', 450, 50, 130, 20)]
        result = map_text_to_components(
            [box('Card', 0, 0, 400, 300), box('Button', 20, 90, 200, 40)], words)
        self.assertCountEqual(
            [o['ocr_id'] for c in result for o in c['ocr']], range(len(words)))
        self.assertEqual(next(c for c in result if c['class'] == 'Button')['texts'],
                         ['Apply'])

    def test_checkbox_keeps_nearby_link_separate(self):
        result = map_text_to_components(
            [box('Check Box', 0, 0, 20, 20)],
            [text('Read terms', 30, 0, 100, 20, underlined=True)])
        self.assertTrue(any(c['class'] == 'Link' for c in result))
        self.assertFalse(result[0]['texts'])

    def test_separate_ocr_links_are_not_merged(self):
        result = map_text_to_components([], [
            text('One', 0, 0, 60, 20, link_hint=True, separate_run=True),
            text('Two', 70, 0, 60, 20, link_hint=True, separate_run=True)])
        self.assertEqual([c['texts'] for c in result], [['One'], ['Two']])

    def test_coloured_title_alone_is_not_a_link(self):
        result = map_text_to_components(
            [], [text('Overview', 0, 0, 200, 40, coloured_text=True)])
        self.assertNotEqual(result[0]['class'], 'Link')

    def test_ocr_split_cannot_drop_words(self):
        self.assertTrue(same_text('Read the terms',
                                 [{'text': 'Read the'}, {'text': 'terms'}]))
        self.assertFalse(same_text('Read the terms', [{'text': 'Read terms'}]))

    def test_supported_themes_preserve_components(self):
        layout = reconstruct_layout([
            box('Textbox', 0, 0, 240, 40, texts=['City']),
            box('Button', 0, 70, 240, 40, texts=['Apply'], filled=True)])
        original = deepcopy(layout)
        baseline = generate_react_code(layout)
        for theme in ('light', 'dark', 'blue'):
            code = generate_react_code(layout, theme)
            self.assertEqual(code.replace('data-sketch-theme="' + theme + '"',
                                          'data-sketch-theme="light"'), baseline)
            self.assertIn(theme, THEMES)
        self.assertEqual(layout, original)
        self.assertEqual(generate_react_code(layout, 'unknown'), baseline)

    def test_embedded_image_and_unsafe_image_source(self):
        # Source validation is tested here; pixel decoding belongs to crop tests.
        src = 'data:image/png;base64,aGVsbG8='
        code = generate_component(box('Image', 0, 0, 200, 100, image_src=src))
        self.assertIn(src, code)
        self.assertIn('<img ', code)
        code = generate_component(box('Image', 0, 0, 200, 100,
                                      image_src='javascript:alert(1)'))
        self.assertNotIn('<img ', code)
        self.assertNotIn('javascript:', code)

    @staticmethod
    def row(kinds, positions):
        children = []
        for i, (kind, (x, width)) in enumerate(zip(kinds, positions)):
            c = box(kind, x, 0, width, 24, texts=['Segment ' + str(i)])
            children.append(dict(kind='component', component=c,
                                 **{k: c[k] for k in ('x1', 'y1', 'x2', 'y2')}))
        return dict(kind='row', children=children, x1=0, y1=0,
                    x2=children[-1]['x2'], y2=24)

    def test_inline_links_wrap_without_losing_control_or_order(self):
        row = self.row(['Check Box', 'Link', 'Paragraph', 'Link'],
                       [(0, 85), (95, 85), (190, 30), (230, 120)])
        code = render_layout_tree(row, .7)
        self.assertIn('data-layout-kind="inline"', code)
        self.assertEqual(code.count('<input '), 1)
        self.assertEqual(code.count('<a '), 2)
        self.assertEqual(sorted(code.index('Segment ' + str(i)) for i in range(4)),
                         [code.index('Segment ' + str(i)) for i in range(4)])
        self.assertNotIn('grid-cols-', code)

    def test_independent_rows_keep_geometric_tracks(self):
        examples = [
            (['Paragraph', 'Link'], [(0, 80), (300, 90)]),
            (['Link', 'Link'], [(0, 80), (90, 90)]),
            (['Button', 'Button', 'Button'], [(0, 80), (90, 80), (180, 80)]),
            (['Check Box', 'Check Box'], [(0, 80), (90, 80)]),
        ]
        for kinds, positions in examples:
            with self.subTest(kinds=kinds):
                code = render_layout_tree(self.row(kinds, positions), .7)
                self.assertIn('data-layout-kind="row"', code)
                self.assertIn('grid-cols-', code)

    def test_single_form_stays_single_column(self):
        items = [box('Heading', 0, 0, 240, 35, texts=['Your details']),
                 box('Textbox', 0, 60, 240, 40, texts=['City']),
                 box('Textbox', 0, 130, 240, 40, texts=['Region']),
                 box('Button', 0, 200, 240, 40, texts=['Apply'])]
        code = generate_react_code(reconstruct_layout(items))
        self.assertNotIn('data-layout-kind="columns"', code)
        self.assertEqual(code.count('<input '), 2)
        self.assertEqual(code.count('<button '), 1)


if __name__ == '__main__':
    unittest.main()
