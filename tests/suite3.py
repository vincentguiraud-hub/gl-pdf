# Tests polices (analyse visuelle) et téléphone (au doigt)
import os, sys, shutil, subprocess
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=os.path.join(ROOT,'tests','fixtures'); APP='file://'+os.path.join(ROOT,'build','GL-PDF.html')
OUT=os.path.join(ROOT,'build','test-out3'); shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT)
results=[]
def ok(n,c,info=''): results.append((n,bool(c),info)); print(('PASS ' if c else 'FAIL ')+n+('' if c else ' — '+str(info)[:300]), flush=True)
with sync_playwright() as pw:
    b=pw.chromium.launch()
    # ---- polices : analyse visuelle (noms codés et noms trompeurs)
    pg=b.new_page(viewport={'width':1366,'height':900},accept_downloads=True); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(APP); pg.wait_for_timeout(1200)
    pg.set_input_files('#fOpen',S+'/obf.pdf'); pg.wait_for_timeout(2000)
    want=['Barlow Condensed','PT Serif','IBM Plex Mono','Lato','Fira Sans Extra Condensed','Ubuntu',('Arimo','Liberation Sans'),('Liberation Serif','Tinos'),'DejaVu Serif','DejaVu Sans Condensed']
    good=0
    for j,w in enumerate(want):
        r=pg.evaluate(f"window.__glAnalyse(0,{j})"); top=r['res'][0][0] if r['res'] else ''
        fam=top.replace(' Gras','').replace(' Italique','').replace(' Medium','')
        good+= (fam in w) if isinstance(w,tuple) else (fam==w)
    ok('analyse visuelle : polices aux noms codés (%d/10)'%good, good>=9)
    pg.set_input_files('#fOpen',S+'/lie.pdf'); pg.wait_for_timeout(2000)
    tops=[pg.evaluate(f"window.__glAnalyse(0,{j})")['res'][0][0] for j in range(3)]
    ok('analyse visuelle : noms trompeurs', tops==['PT Serif','Barlow Semi Condensed','Poppins'], tops)
    # modification avec lettres absentes : écrites dans la police la plus proche
    pg.set_input_files('#fOpen',S+'/din.pdf'); pg.wait_for_timeout(2000)
    pg.click('[data-t=edit]'); l=pg.locator('.ti').nth(1); bb=l.bounding_box(); pg.mouse.click(bb['x']+bb['width']-2,bb['y']+bb['height']/2); pg.wait_for_timeout(2500)
    pg.keyboard.press('End'); pg.keyboard.type(' QUEZAC 2026 XYZ'); pg.wait_for_timeout(400)
    ok('police proche à l’écran', 'Barlow' in pg.evaluate("getComputedStyle(document.querySelector('.obj.txt .ed')).fontFamily"))
    pg.keyboard.press('Escape'); pg.mouse.click(1300,880)
    with pg.expect_download() as d: pg.click('#bSave')
    p=OUT+'/din-out.pdf'; shutil.copy(d.value.path(), p)
    ok('texte modifié enregistré', 'QUEZAC 2026 XYZ' in subprocess.run(['pdftotext',p,'-'],capture_output=True,text=True).stdout)
    ok('police intégrée au PDF', 'Barlow' in subprocess.run(['pdffonts',p],capture_output=True,text=True).stdout)
    ok('polices : aucune erreur', not errs, errs[:3])
    # ---- téléphone
    d=dict(pw.devices['iPhone 13']); d.pop('default_browser_type',None)
    ctx=b.new_context(**d, accept_downloads=True); pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    cdp=ctx.new_cdp_session(pg)
    def touch(seq):
        for typ,pts in seq: cdp.send('Input.dispatchTouchEvent',{'type':typ,'touchPoints':[{'x':x,'y':y,'id':i} for i,(x,y) in enumerate(pts)]}); pg.wait_for_timeout(16)
    st=lambda js: pg.evaluate('(()=>{const S=window.__glState();return '+js+'})()')
    nobj=lambda: st('S.pages.reduce((a,p)=>a+p.objs.length,0)')
    def tool(t): pg.evaluate("document.querySelector('[data-t="+t+"]').scrollIntoView({inline:'center'})"); pg.tap('[data-t='+t+']'); pg.wait_for_timeout(300)
    pg.goto(APP); pg.wait_for_timeout(1200)
    ok('téléphone : pas de défilement horizontal', pg.evaluate("document.documentElement.scrollWidth<=innerWidth"))
    ok('téléphone : barre du haut sur une ligne', pg.locator('header.top').bounding_box()['height']<80)
    pg.set_input_files('#fOpen',S+'/real.pdf'); pg.wait_for_timeout(2000)
    pr=pg.locator('.page').first.bounding_box()
    tool('edit'); bb=pg.locator('.ti').nth(0).bounding_box(); pg.tap('.ti >> nth=0', position={'x':bb['width']-3,'y':bb['height']/2}); pg.wait_for_timeout(1500)
    pg.keyboard.type(' bis'); pg.wait_for_timeout(300)
    ok('téléphone : modifier le texte', 'bis' in (pg.evaluate("document.activeElement && document.activeElement.textContent") or ''))
    pg.touchscreen.tap(200,780); pg.wait_for_timeout(400)
    tool('text'); n0=nobj(); pg.touchscreen.tap(pr['x']+60,pr['y']+300); pg.wait_for_timeout(500); pg.keyboard.type('Bonjour'); pg.wait_for_timeout(200)
    ok('téléphone : ajouter du texte', nobj()==n0+1)
    pg.touchscreen.tap(200,780); pg.wait_for_timeout(300)
    tool('draw'); n0=nobj(); touch([('touchStart',[(pr['x']+40,pr['y']+350)])]+[('touchMove',[(pr['x']+40+i*6,pr['y']+350+(i%5)*4)]) for i in range(1,25)]+[('touchEnd',[])]); pg.wait_for_timeout(300)
    ok('téléphone : dessiner', nobj()==n0+1)
    tool('check'); n0=nobj(); top0=pg.evaluate('viewer.scrollTop')
    touch([('touchStart',[(200,600)])]+[('touchMove',[(200,600-i*20)]) for i in range(1,15)]+[('touchEnd',[])]); pg.wait_for_timeout(600)
    ok('téléphone : défiler avec l’outil coche ne pose rien', nobj()==n0)
    pr=pg.locator('.page').first.bounding_box(); pg.touchscreen.tap(pr['x']+200,pr['y']+400); pg.wait_for_timeout(300)
    ok('téléphone : poser une coche', nobj()==n0+1)
    tool('select'); cb=pg.locator('.obj.check').first.bounding_box(); pg.touchscreen.tap(cb['x']+cb['width']+6, cb['y']+cb['height']/2); pg.wait_for_timeout(300)
    ok('téléphone : sélectionner une petite coche', pg.is_visible('#cDel'))
    z0=pg.inner_text('#zVal')
    touch([('touchStart',[(150,500),(240,500)])]+[('touchMove',[(150-i*8,500),(240+i*8,500)]) for i in range(1,10)]+[('touchEnd',[])]); pg.wait_for_timeout(800)
    ok('téléphone : pincer pour zoomer', pg.inner_text('#zVal')!=z0)
    pg.tap('#bMore'); pg.wait_for_timeout(200)
    ok('téléphone : menu ⋯', pg.evaluate("secBar.classList.contains('open')"))
    pg.tap('#bFind'); pg.wait_for_timeout(300)
    ok('téléphone : menu se ferme', not pg.evaluate("secBar.classList.contains('open')") and pg.is_visible('#searchBar'))
    pg.keyboard.press('Escape')
    with pg.expect_download() as dl: pg.tap('#bSave')
    p=OUT+'/mob.pdf'; shutil.copy(dl.value.path(), p); t=subprocess.run(['pdftotext',p,'-'],capture_output=True,text=True).stdout
    ok('téléphone : enregistrer', 'bis' in t and 'Bonjour' in t)
    ok('téléphone : aucune erreur', not errs, errs[:3])
    # ---- fenêtre « Demander à Claude » (fausse API GitHub : rien n'est envoyé)
    import json as _j
    issues={}
    def gh(route, req):
        u=req.url
        if req.method=='POST' and u.endswith('/issues'):
            n=100+len(issues); issues[n]=_j.loads(req.post_data); return route.fulfill(status=201, json={'number':n})
        if '/comments' in u: return route.fulfill(json=[{'body':'✅ **Corrigé dans la version 9.9.9.**\n\nTest.'}])
        if '/issues/' in u: return route.fulfill(json={'state':'closed'})
        return route.fulfill(json=[])
    pg=b.new_page(viewport={'width':1366,'height':900}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.route('https://api.github.com/**', gh); pg.goto(APP); pg.wait_for_timeout(1000)
    pg.click('#bClaude'); pg.wait_for_timeout(300)
    ok('Claude : réglages demandés au premier usage', pg.locator('#clTok').count()==1)
    pg.fill('#clNom','Test'); pg.fill('#clTok','github_pat_'+'A'*40); pg.click('[data-save]'); pg.wait_for_timeout(1500)
    pg.fill('#clTxt','Ceci est une demande de test automatique.'); pg.click('[data-go]'); pg.wait_for_timeout(1500)
    ok('Claude : demande envoyée avec le contexte', issues.get(100,{}).get('title','').startswith('[G&L PDF]') and 'Version de l’éditeur' in issues[100]['body'])
    ok('Claude : suivi de la demande', '9.9.9' in pg.locator('.req .st').first.inner_text())
    pg.click('[data-back]'); pg.wait_for_timeout(300); pg.click('.modal .btn.pri'); pg.wait_for_timeout(1200)
    ok('Claude : retour à la version précédente demandé', issues.get(101,{}).get('title','').startswith('[Retour version]'))
    ok('Claude : aucune erreur', not errs, errs[:3])
    b.close()
fails=[r for r in results if not r[1]]
print('\n%d tests, %d réussis, %d échecs' % (len(results), len(results)-len(fails), len(fails)))
for f in fails: print(' ✗', f[0], '—', str(f[2])[:300])
sys.exit(1 if fails else 0)
