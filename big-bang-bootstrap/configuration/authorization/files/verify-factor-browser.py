#!/usr/bin/env python3
"""Bounded PKCE browser-form checks for one approved disposable identity only.
No realm/user configuration API writes: Ansible owns create/reset/cleanup.
Never prints response bodies, cookies, URLs with codes, passwords or OTP seeds.
"""
import base64,hashlib,hmac,json,os,secrets,signal,struct,sys,time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,parse_qs
import requests

class Stop(Exception):pass
def require(value, label):
 if not value:raise Stop(label)
class Forms(HTMLParser):
 def __init__(self,text):
  super().__init__();self.forms={};self.links={};self.ids=set();self.secrets={};self.current=None;self.capture=None;self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);ident=a.get('id');self.ids.add(ident)
  if tag=='form':self.current=ident;self.forms[ident]={'action':a.get('action',''),'hidden':{},'inputs':{}}
  if tag=='input' and self.current and a.get('name'):
   self.forms[self.current]['inputs'][a['name']]=a
   if a.get('type')=='hidden':self.forms[self.current]['hidden'][a['name']]=a.get('value','')
  if tag=='a' and ident:self.links[ident]=a.get('href','')
  if tag=='span' and ident=='kc-totp-secret-key':self.capture=ident;self.secrets[ident]=''
 def handle_endtag(self,tag):
  if tag=='form':self.current=None
  if tag=='span':self.capture=None
 def handle_data(self,data):
  if self.capture:self.secrets[self.capture]+=data

def otp(seed,policy,counter=None):
 key=base64.b32decode(''.join(seed.split()).upper(),casefold=True)
 counter=int(time.time())//policy['period'] if counter is None else counter
 alg={'HmacSHA1':'sha1','HmacSHA256':'sha256','HmacSHA512':'sha512'}[policy['algorithm']]
 digest=hmac.new(key,struct.pack('>Q',counter),getattr(hashlib,alg)).digest();offset=digest[-1]&15
 return str((int.from_bytes(digest[offset:offset+4],'big')&0x7fffffff)%10**policy['digits']).zfill(policy['digits'])
def save_private(path,value):
 st=path.lstat();require(path.is_file() and not path.is_symlink() and st.st_uid==os.getuid() and st.st_mode&0o777==0o600,'private file metadata')
 fd=os.open(path,os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW)
 with os.fdopen(fd,'w') as out:json.dump(value,out)
class Browser:
 def __init__(self,config):
  self.c=config;self.s=requests.Session();self.s.trust_env=False;self.s.verify=config['ca'];self.base=config['url'];self.origin=urlsplit(self.base)[:2];self.callback=None;self.page=None;self.current=''
  self.verifier=secrets.token_urlsafe(48);self.state=secrets.token_urlsafe(24);self.nonce=secrets.token_urlsafe(24)
 def fetch(self,url,method='GET',data=None):
  for _ in range(10):
   require(urlsplit(url)[:2]==self.origin and urlsplit(url).scheme=='https','HTTPS origin')
   response=self.s.request(method,url,data=data,allow_redirects=False,timeout=20)
   if response.status_code in (301,302,303,307,308):
    target=urljoin(url,response.headers['Location']);q=parse_qs(urlsplit(target).query)
    if urlsplit(target).path==urlsplit(self.c['redirect']).path and ('code' in q or 'error' in q):
     require(urlsplit(target)[:2]==self.origin,'callback origin');self.callback=q;self.page=None;return
    if response.status_code not in (307,308):method='GET';data=None
    url=target;continue
   require(response.status_code in (200,400),'form HTTP status');self.current=response.url;self.page=Forms(response.text);return
  raise Stop('redirect bound')
 def start(self):
  challenge=base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip('=')
  query=requests.compat.urlencode({'client_id':'account-console','redirect_uri':self.c['redirect'],'response_type':'code','scope':'openid','code_challenge':challenge,'code_challenge_method':'S256','state':self.state,'nonce':self.nonce,'prompt':'login'})
  self.fetch(self.base+'/realms/perkforge/protocol/openid-connect/auth?'+query)
  require(self.page and 'kc-form-login' in self.page.forms,'password challenge')
 def submit(self,form_id,values):
  require(self.page is not None and form_id in self.page.forms,'expected form')
  form=self.page.forms[form_id];self.fetch(urljoin(self.current,form['action']),'POST',{**form['hidden'],**values})
 def password(self,value):self.submit('kc-form-login',{'username':self.c['username'],'password':value})
 def enroll(self,old_seed=None):
  require(self.page and 'kc-totp-settings-form' in self.page.forms,'TOTP enrollment challenge')
  require('mode-manual' in self.page.links,'supported manual enrollment view')
  self.fetch(urljoin(self.current,self.page.links['mode-manual']))
  seed=''.join(self.page.secrets.get('kc-totp-secret-key','').split())
  require(seed and seed!=old_seed,'new independent test factor')
  self.submit('kc-totp-settings-form',{'totp':otp(seed,self.c['policy']),'userLabel':'disposable-checkpoint'})
  return seed,int(time.time())//self.c['policy']['period']
 def token(self):
  require(self.callback and self.callback.get('state')==[self.state] and len(self.callback.get('code',[]))==1 and 'error' not in self.callback,'OIDC authorization success')
  r=self.s.post(self.base+'/realms/perkforge/protocol/openid-connect/token',data={'grant_type':'authorization_code','client_id':'account-console','redirect_uri':self.c['redirect'],'code_verifier':self.verifier,'code':self.callback['code'][0]},timeout=20,allow_redirects=False)
  require(r.status_code==200,'PKCE token exchange');tokens=r.json()
  r=self.s.get(self.base+'/realms/perkforge/protocol/openid-connect/userinfo',headers={'Authorization':'Bearer '+tokens['access_token']},timeout=20,allow_redirects=False)
  require(r.status_code==200 and r.json().get('sub')==self.c['uid'],'accepted test identity')
  return {k:tokens[k] for k in ['access_token','refresh_token','expires_in']}
 def close(self):self.s.close()

def run(config,phase):
 private=Path(config['private_file']);st=private.lstat();require(not private.is_symlink() and st.st_uid==os.getuid() and st.st_mode&0o777==0o600,'private input')
 secret=json.loads(private.read_text());require(secret['username']==config['username'] and config['username'].startswith('mfa-check-') and len(config['username'])==22,'test identity guard')
 config={**config,'username':secret['username']};result={'phase':phase,'passed':False,'coreyUsed':False};b=None
 try:
  if phase=='probe':
   b=Browser(config);b.start();result['passwordFormVerified']=True
  elif phase in ['enroll','recover']:
   b=Browser(config);b.start();b.password(secret['password']);seed,counter=b.enroll(secret.get('seed') if phase=='recover' else None);tokens=b.token()
   secret.update(seed=seed,last_counter=counter,tokens=tokens);secret.setdefault('issued_tokens',[]).append(tokens);save_private(private,secret)
   result.update(enrolled=True,tokenAcceptedForExactUID=True,newFactor=(phase=='recover'))
  elif phase=='negative':
   # Exactly one wrong-password, one missing-OTP and one wrong-OTP submission.
   pause=max(1.25,config['quick_login_ms']/1000+0.25)
   require(pause<=11,'failure pacing bound')
   b=Browser(config);b.start();b.password(secret['password']+'-incorrect')
   require(not b.callback and b.page and 'kc-form-login' in b.page.forms,'wrong-password denial');b.close();time.sleep(pause)
   for kind in ['missing','wrong']:
    b=Browser(config);b.start();b.password(secret['password']);require(b.page and 'kc-otp-login-form' in b.page.forms,'OTP challenge after password')
    counter=int(time.time())//config['policy']['period'];window=config['policy']['lookahead']+2
    forbidden={otp(secret['seed'],config['policy'],c) for c in range(max(0,counter-window),counter+window+1)}
    candidate=next(str(n).zfill(config['policy']['digits']) for n in range(100) if str(n).zfill(config['policy']['digits']) not in forbidden)
    b.submit('kc-otp-login-form',{'otp':'' if kind=='missing' else candidate})
    require(not b.callback and b.page and 'kc-otp-login-form' in b.page.forms and bool({'input-error-otp-code','input-error-otp'} & b.page.ids),kind+' OTP denial');b.close();time.sleep(pause)
   # One valid fresh-factor success confirms the negatives were not broken credentials.
   counter=int(time.time())//config['policy']['period']
   if counter<=secret['last_counter']:time.sleep(config['policy']['period']-time.time()%config['policy']['period']+1)
   b=Browser(config);b.start();b.password(secret['password']);b.submit('kc-otp-login-form',{'otp':otp(secret['seed'],config['policy'])});secret['tokens']=b.token();secret.setdefault('issued_tokens',[]).append(secret['tokens']);secret['last_counter']=int(time.time())//config['policy']['period'];save_private(private,secret)
   result.update(wrongPasswordDenied=True,missingOTPDenied=True,wrongOTPDenied=True,failedSubmissions=3,validFactorLoginPassed=True)
  elif phase=='revoked':
   s=requests.Session();s.trust_env=False;s.verify=config['ca'];issued=secret.get('issued_tokens',[])
   require(len(issued)<=3,'issued-token bound')
   for tokens in issued:
    r=s.get(config['url']+'/realms/perkforge/protocol/openid-connect/userinfo',headers={'Authorization':'Bearer '+tokens['access_token']},timeout=20,allow_redirects=False)
    require(r.status_code==401,'deleted identity bearer rejection')
    r=s.post(config['url']+'/realms/perkforge/protocol/openid-connect/token',data={'grant_type':'refresh_token','client_id':'account-console','refresh_token':tokens['refresh_token']},timeout=20,allow_redirects=False)
    require(r.status_code==400 and r.json().get('error')=='invalid_grant','deleted identity refresh rejection')
   result.update(revokedTokenPairs=len(issued),userinfoAndRefreshDenied=bool(issued),noTokenWasIssued=not issued)
   s.close();private.unlink();result['generatedCredentialFileRemoved']=not private.exists()
  else:raise Stop('unknown phase')
  result['passed']=True
  Path(config['evidence_dir'],phase+'.json').write_text(json.dumps(result,indent=2))
  print(json.dumps(result))
 finally:
  if b:b.close()
if __name__=='__main__':
 def deadline(*_):raise Stop('phase deadline')
 signal.signal(signal.SIGALRM,deadline);signal.alarm(180)
 try:run(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
 except Exception as error:
  print('STOP bounded identity check: '+type(error).__name__+(': '+str(error) if isinstance(error,Stop) else ''));sys.exit(1)
