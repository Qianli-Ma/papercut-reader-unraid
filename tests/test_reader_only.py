"""Focused regression checks: parsing stays enabled and AI never contacts Ollama."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_tmp = tempfile.TemporaryDirectory()
os.environ['PAPER_READER_LIBRARY'] = _tmp.name
os.environ['PAPERCUT_READER_ONLY'] = '1'
os.environ['PAPERCUT_WORKER'] = '0'
from fastapi.testclient import TestClient
from app import jobs, library, llm
from app.main import app

class ReaderOnlyTests(unittest.TestCase):
    def test_all_llm_entrypoints_fail_before_network(self):
        with patch('httpx.post', side_effect=AssertionError('network')), patch('httpx.stream', side_effect=AssertionError('network')), patch('httpx.get', side_effect=AssertionError('network')):
            self.assertTrue(llm.status()['reader_only'])
            for call in [lambda: llm.chat([]), lambda: llm.embed(['x'],'x'), lambda: list(llm.stream_chat([])), lambda: list(llm.stream_turn([],[]))]:
                with self.assertRaisesRegex(RuntimeError,'AI is disabled'):
                    call()

    def test_ai_routes_disabled_and_reader_flag_served(self):
        client = TestClient(app)
        for suffix in ['ask','highlight','summary','cards','insights','explain','explain-float','translate']:
            self.assertEqual(client.post('/api/papers/abcd/'+suffix, json={}).status_code,409)
        self.assertEqual(client.post('/api/library/organize',json={}).status_code,409)
        self.assertIn('data-reader-only="1"',client.get('/').text)
        self.assertTrue(client.get('/api/info').json()['reader_only'])

    def test_upload_queues_full_parse_without_ai(self):
        import pymupdf
        pdf=pymupdf.open();p=pdf.new_page();p.insert_text((72,72),'Parser remains enabled')
        client=TestClient(app)
        response=client.post('/api/papers',files={'file':('test.pdf',pdf.tobytes(),'application/pdf')})
        self.assertEqual(response.status_code,200)
        pid=response.json()['id']
        self.assertIn([pid,'full'], jobs._pending)
        before=list(jobs._pending)
        jobs.submit(pid,kind='summary')
        self.assertEqual(jobs._pending,before)
        self.assertTrue(library.pdf_path(pid).is_file())

    def test_ruled_code_figure_keeps_both_panels_in_one_crop(self):
        import pymupdf
        from app.parse import _tables_from_rules
        pid='abcdef02'
        library.assets_dir(pid).mkdir(parents=True,exist_ok=True)
        pdf=pymupdf.open(); page=pdf.new_page(width=300,height=400)
        for y in [40,55,130,145,240]: page.draw_line((30,y),(270,y))
        page.insert_text((35,52),'Panel 1')
        page.insert_text((35,80),'1  const first = 1;')
        page.insert_text((24,80),'1',fontsize=5)
        page.insert_text((35,142),'Panel 2')
        page.insert_text((35,180),'2  const second = 2;')
        raw=[{'type':'heading','text':'Panel 1','region':'body','_pos':(1,30,40,270,55)},
             {'type':'code','text':'first','region':'body','_pos':(1,35,65,260,90)},
             {'type':'heading','text':'Panel 2','region':'body','_pos':(1,30,130,270,145)},
             {'type':'code','text':'second','region':'body','_pos':(1,35,160,260,200)},
             {'type':'caption','text':'Figure 6: Two code panels.','region':'body','_pos':(1,30,250,270,265),'provs':[(1,(30,250,270,265))]}]
        out,n=_tables_from_rules(raw,pdf,pid,0)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['type'],'figure')
        self.assertEqual(out[0]['_pos'],(1,23.0,40.0,270.0,240.0))
        pix=pymupdf.Pixmap(library.paper_dir(pid)/out[0]['image'])
        self.assertGreater(pix.height,800)
        self.assertIn('Two code panels',out[0]['_captions'][0]['text'])

    def test_worker_parses_and_saves_without_highlighting(self):
        # Run exactly one queue item, then stop the loop with a sentinel exception.
        pid='abcdef01'
        library.paper_dir(pid).mkdir(parents=True,exist_ok=True)
        library.pdf_path(pid).write_bytes(b'test')
        paper={'id':pid,'status':{'parsed':True,'classified':False}}
        class StopWorker(BaseException): pass
        with patch.object(jobs._queue,'get',side_effect=[(pid,'full'),StopWorker()]), patch.object(jobs._queue,'task_done'), patch.object(jobs,'parse_paper',return_value=paper) as parse, patch.object(jobs,'_highlight',side_effect=AssertionError('AI called')):
            with self.assertRaises(StopWorker): jobs._worker()
            parse.assert_called_once()
        saved=library.load_paper(pid)
        self.assertTrue(saved['status']['reader_only'])
        self.assertEqual(jobs.status(pid)['state'],'done')

if __name__=='__main__':
    unittest.main(verbosity=2)
