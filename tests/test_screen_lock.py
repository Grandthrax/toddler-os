"""Child sessions, idle expiry, password changes and parent-only administration."""
import http.cookiejar
import json
from pathlib import Path
import tempfile
import threading
import unittest
import sys
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from admin_server import AdminServer
from core import Problem
from screen_lock import ScreenLock, LockSettings, COOKIE
from server import Application


class LockTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'lock.json'
        self.config=LockSettings(self.path);self.config.update(True,300,'practice')
        self.now=0.;self.lock=ScreenLock(self.path,clock=lambda:self.now)

    def tearDown(self):self.temp.cleanup()

    def test_password_is_hashed_and_never_in_public_status(self):
        self.assertNotIn('practice',self.path.read_text())
        self.assertEqual(set(self.config.public()),{'enabled','idle_seconds','password_set'})
        self.assertEqual(set(self.lock.status()),{'enabled','idle_seconds','locked'})
        with self.assertRaises(Problem):self.lock.unlock('wrong')
        token,state=self.lock.unlock('PRACTICE');self.assertFalse(state['locked'])
        self.assertTrue(self.lock.status(COOKIE+'=forged')['locked'])
        self.assertTrue(ScreenLock(self.path).status(COOKIE+'='+token)['locked'])

    def test_activity_idle_expiry_explicit_lock_and_password_change(self):
        token,_=self.lock.unlock('practice');cookie=COOKIE+'='+token
        self.now=290;self.lock.activity(cookie);self.now=580
        self.assertFalse(self.lock.status(cookie)['locked'])
        self.now=590;self.assertTrue(self.lock.status(cookie)['locked'])
        with self.assertRaises(Problem):self.lock.activity(cookie)
        token,_=self.lock.unlock('practice');cookie=COOKIE+'='+token
        self.assertTrue(self.lock.lock(cookie)['locked'])
        token,_=self.lock.unlock('practice');cookie=COOKIE+'='+token
        self.config.update(True,300,'another');self.assertTrue(self.lock.status(cookie)['locked'])
        self.config.update(False,300);self.assertFalse(self.lock.status(cookie)['locked'])

    def test_retry_throttle_and_invalid_parent_settings(self):
        for _ in range(8):
            with self.assertRaises(Problem):self.lock.unlock('wrong')
        with self.assertRaises(Problem) as error:self.lock.unlock('practice')
        self.assertEqual(error.exception.status,429)
        self.now=61;self.assertFalse(self.lock.unlock('practice')[1]['locked'])
        for enabled,seconds,password in ((True,0,''),('yes',300,''),(True,300,[]),(True,300,' '*3)):
            with self.assertRaises(Problem):self.config.update(enabled,seconds,password)
        self.path.write_text('{}')
        with self.assertRaises(Problem):self.lock.status()


class LockHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.path=self.folder/'parent'/'lock.json';LockSettings(self.path).update(True,300,'practice')
        self.app=Application(0,self.folder/'data',lock_settings=self.path)
        self.admin=AdminServer(0,self.path,self.folder/'parent'/'access.key')
        self.threads=[]
        for server in (self.app,self.admin):
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();self.threads.append(thread)
        self.browser=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def tearDown(self):
        for server in (self.app,self.admin):server.shutdown();server.server_close()
        for thread in self.threads:thread.join()
        self.temp.cleanup()

    def request(self,server,path,body=None,method=None,origin=None):
        base=f'http://127.0.0.1:{server.server_port}'
        headers={'Origin':origin or base,'X-Little-Pages':'1','Content-Type':'application/json'}
        try:r=self.browser.open(Request(base+path,json.dumps(body).encode() if body is not None else None,headers,method=method),timeout=5)
        except HTTPError as error:r=error
        with r:return r.status,json.loads(r.read()) if 'json' in r.headers.get('Content-Type','') else r.read()

    def test_child_unlock_protects_read_and_write_and_never_exposes_admin(self):
        self.assertEqual(self.request(self.app,'/api/stories')[0],423)
        self.assertEqual(self.request(self.app,'/api/ninja/start',{})[0],423)
        self.assertEqual(self.request(self.app,'/api/lock/unlock',{'password':'wrong'})[0],403)
        self.assertEqual(self.request(self.app,'/api/lock/unlock',{'password':'practice'},origin='https://example.com')[0],403)
        self.assertEqual(self.request(self.app,'/api/lock/unlock',{'password':'PRACTICE'})[0],200)
        self.assertEqual(self.request(self.app,'/api/stories')[0],200)
        self.assertEqual(self.request(self.admin,'/api/config')[0],401)
        self.assertEqual(self.request(self.app,'/admin.js')[0],404)
        self.request(self.app,'/api/lock/lock',{})
        self.assertEqual(self.request(self.app,'/api/stories')[0],423)

    def test_only_parent_key_changes_config_and_invalidates_child_session(self):
        self.request(self.app,'/api/lock/unlock',{'password':'practice'})
        body={'enabled':True,'idle_minutes':5,'password':'replacement'}
        self.assertEqual(self.request(self.admin,'/api/config',body,'PUT')[0],401)
        self.assertEqual(self.request(self.admin,'/api/session',{'token':'practice'})[0],403)
        self.assertEqual(self.request(self.admin,'/api/session',{'token':self.admin.token})[0],200)
        self.assertEqual(self.request(self.admin,'/api/config',body,'PUT',origin='https://example.com')[0],403)
        self.assertEqual(self.request(self.admin,'/api/config',body,'PUT')[0],200)
        self.assertEqual(self.request(self.app,'/api/stories')[0],423)
        self.assertEqual(self.request(self.app,'/api/lock/unlock',{'password':'replacement'})[0],200)
        self.assertEqual(self.request(self.admin,'/api/config')[1],{'enabled':True,'idle_seconds':300,'password_set':True})
