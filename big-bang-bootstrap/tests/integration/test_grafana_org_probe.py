import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).parents[1]/'runtime/grafana_org_probe.py'
spec=importlib.util.spec_from_file_location('probe',path)
probe=importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)

class ProbeTest(unittest.TestCase):
    def run_probe(self, leak=False, approved=True, malformed=False):
        calls=[]; receipts=[]; deleted=False
        def api(method,path,headers,body):
            nonlocal deleted
            calls.append((method,path))
            if path=='/api/orgs/2': return 200,{'id':2,'name':'Tenant'}
            if method=='POST' and path=='/api/serviceaccounts/':
                return 201,dict(body,id=7,orgId=2)
            if path.endswith('/tokens'): return 200,{'key':'synthetic'}
            if method=='DELETE': deleted=True; return 200,{}
            if path=='/api/serviceaccounts/7': return 404,{}
            if deleted:return 401,{}
            if malformed and path=='/api/ds/query':return 400,{'message':'malformed'}
            if path=='/api/datasources':return 200,[{'uid':'own'}]
            if path=='/api/datasources/uid/own':return 200,{'orgId':2}
            if '/proxy/uid/own' in path:return 200,{'status':'success','data':{'result':[{'values':[['1','benign']]}]}}
            return (200 if leak else 403),{}
        try:
            return probe.verify(api,receipts.append,approved=approved,org_id=2,
                org_name='Tenant',own_uid='own',foreign_uids=['platform'],
                marker='benign',query='/loki/api/v1/query_range?limit=5')
        finally:
            self.calls=calls;self.receipts=receipts;self.deleted=deleted
    def test_success_cleanup(self):
        self.assertTrue(self.run_probe()['cleaned'])
        self.assertTrue(self.receipts[-1]['passed'])
    def test_failure_cleanup(self):
        with self.assertRaises(probe.ProbeFailure):self.run_probe(leak=True)
        self.assertTrue(self.deleted);self.assertTrue(self.receipts[-1]['cleaned'])
        self.assertFalse(self.receipts[-1]['passed'])
    def test_inert_without_approval(self):
        with self.assertRaises(probe.ProbeFailure):self.run_probe(approved=False)
        self.assertEqual(self.calls,[])

    def test_malformed_query_is_not_denial(self):
        with self.assertRaises(probe.ProbeFailure):self.run_probe(malformed=True)
        self.assertTrue(self.deleted);self.assertFalse(self.receipts[-1]['passed'])
