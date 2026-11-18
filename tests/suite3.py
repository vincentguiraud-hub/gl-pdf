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
    warns=[]; pg.on('console',lambda m: m.type in ('warning','error') and warns.append(m.text[:200]))
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
    det=pg.evaluate("window.__glAnalyse(0,0)")
    SERIF={'PT Serif','Gelasio','Source Serif 4','Liberation Serif','Tinos','Caladea','EB Garamond','Merriweather','IBM Plex Serif','Noto Serif','DejaVu Serif','Noto Serif Condensed'}
    fam=lambda x: x.replace(' Gras','').replace(' Italique','').replace(' Medium','').replace(' Light','')
    # « ArialMT » qui est en réalité une police à empattements, « Times » qui est une Barlow, « Calibri » qui est une Poppins
    ok('analyse visuelle : noms trompeurs', fam(tops[0]) in SERIF and fam(tops[1]).startswith('Barlow') and fam(tops[2])=='Poppins', [tops, det['res'][:3]])
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
    # ---- d'office : police de chaque ligne détectée dès l'ouverture de « Modifier le texte » (sans cliquer)
    def attendre_polices(maxs=90):
        for _ in range(maxs):
            pg.wait_for_timeout(1000)
            tis=pg.locator('.ti').all()
            if tis and not pg.is_visible('#fScan') and all((x.get_attribute('title') or '').startswith('Police') for x in tis): return [x.get_attribute('title').split('\n')[0] for x in tis]
        return [x.get_attribute('title').split('\n')[0] for x in pg.locator('.ti').all()]
    pg.click('[data-t=select]'); pg.wait_for_timeout(200)
    pg.set_input_files('#fOpen',S+'/obf.pdf'); pg.wait_for_timeout(1500); pg.click('[data-t=edit]')
    t=attendre_polices()
    fams=['Barlow Condensed','PT Serif','IBM Plex Mono','Lato Gras','Fira Sans Extra Condensed','Ubuntu',('Arimo','Liberation Sans'),('Liberation Serif','Tinos'),'DejaVu Serif','DejaVu Sans Condensed']
    bons=sum(1 for x,w in zip(t,fams) if any(('Police : '+f+' (') in x for f in (w if isinstance(w,tuple) else (w,))))
    ok('d’office : police de chaque ligne détectée (%d/10)'%bons, bons>=9, t)
    # ---- document scanné : lecture automatique du texte, police ligne par ligne, modification et enregistrement
    pg.click('[data-t=select]'); pg.wait_for_timeout(200)
    pg.set_input_files('#fOpen',S+'/scan-polices.pdf'); pg.wait_for_timeout(1500); pg.click('[data-t=edit]')
    t=attendre_polices(120)
    attendu=[('Liberation Serif','Tinos'),('Arimo Gras','Liberation Sans Gras'),('Barlow Condensed',),('DejaVu Serif',),('Liberation Mono','Cousine')]
    bons=sum(1 for x,w in zip(t,attendu) if any(('Police : '+f+' ') in x for f in w))
    ok('scan : texte lu automatiquement (%d lignes)'%len(t), len(t)==5, t)
    ok('scan : police de chaque ligne (%d/5)'%bons, bons>=4, t)
    bb=pg.locator('.ti').nth(2).bounding_box(); pg.mouse.click(bb['x']+bb['width']-2,bb['y']+bb['height']/2); pg.wait_for_timeout(1500)
    pg.keyboard.press('End'); pg.keyboard.type(' et garde-corps'); pg.wait_for_timeout(300)
    ok('scan : ligne modifiée dans la police détectée', 'BarlowCondensed' in pg.evaluate("getComputedStyle(document.querySelector('.obj.txt .ed')).fontFamily"))
    pg.keyboard.press('Escape'); pg.mouse.click(1300,880)
    with pg.expect_download() as d: pg.click('#bSave')
    p=OUT+'/scan-out.pdf'; shutil.copy(d.value.path(), p)
    txt=subprocess.run(['pdftotext',p,'-'],capture_output=True,text=True).stdout
    ok('scan : enregistré avec le nouveau texte (cherchable), sans l’ancien', 'en acier Corten et garde-corps' in txt and txt.count('acier Corten')==1, txt[:300])
    ok('scan : police intégrée', 'BarlowCondensed' in subprocess.run(['pdffonts',p],capture_output=True,text=True).stdout)
    # ---- une zone de texte déplacée sur une ligne effacée reste visible (les caches passent dessous)
    pg.click('[data-t=select]'); pg.wait_for_timeout(200)
    pg.set_input_files('#fOpen',S+'/fond.pdf'); pg.wait_for_timeout(1500)
    pr=pg.locator('.page').first.bounding_box()
    pg.click('[data-t=text]'); pg.wait_for_timeout(200); pg.mouse.click(pr['x']+90, pr['y']+500); pg.wait_for_timeout(300)
    pg.keyboard.type('NOUVELLE ADRESSE'); pg.keyboard.press('Enter'); pg.keyboard.type('82270 MONTPEZAT'); pg.wait_for_timeout(200)
    pg.click('[data-t=edit]'); pg.wait_for_timeout(2500)
    bb=sorted([pg.locator('.ti').nth(k).bounding_box() for k in range(pg.locator('.ti').count())], key=lambda r: r['y'])[0]
    pg.mouse.click(bb['x']+bb['width']-2, bb['y']+bb['height']/2); pg.wait_for_timeout(1500)
    pg.keyboard.press('Control+a'); pg.keyboard.press('Delete'); pg.wait_for_timeout(200)
    pg.click('[data-t=select]'); pg.wait_for_timeout(400)
    tb=[o for o in pg.evaluate("window.__glState().pages[0].objs.map(o=>({id:o.id,type:o.type}))") if o['type']=='text'][0]
    obj=pg.locator('.obj.txt[data-id="%s"]'%tb['id']); obj.locator('.ed').click(); pg.wait_for_timeout(200)
    g=obj.locator('.grip').bounding_box(); e0=obj.locator('.ed').bounding_box()
    # déplacer la zone de texte pile sur la ligne effacée
    dx=bb['x']-e0['x']; dy=bb['y']-e0['y']
    pg.mouse.move(g['x']+g['width']/2, g['y']+g['height']/2); pg.mouse.down(); pg.mouse.move(g['x']+g['width']/2+dx, g['y']+g['height']/2+dy, steps=10); pg.mouse.up(); pg.wait_for_timeout(500)
    pg.mouse.click(1300,880); pg.wait_for_timeout(300)
    ordre=pg.evaluate("[...document.querySelector('.page .objs').children].map(c=>c.className.split(' ')[0])")
    ok('zone de texte déplacée sur une ligne effacée : caches dessous à l’écran', ordre.index('obj') > max(i for i,c in enumerate(ordre) if c=='wipe-under'), ordre)
    e1=obj.locator('.ed').bounding_box(); shot=pg.screenshot(clip={'x':e1['x'],'y':e1['y'],'width':e1['width'],'height':e1['height']})
    from PIL import Image; import io
    im=Image.open(io.BytesIO(shot)).convert('L'); dark=sum(1 for v in im.getdata() if v<100)
    ok('zone de texte déplacée : texte visible à l’écran', dark>150, dark)
    with pg.expect_download() as d: pg.click('#bSave')
    p=OUT+'/cache-out.pdf'; shutil.copy(d.value.path(), p)
    txt=subprocess.run(['pdftotext',p,'-'],capture_output=True,text=True).stdout
    subprocess.run(['pdftoppm','-r','72','-png','-singlefile',p,OUT+'/cache'],check=True)
    im=Image.open(OUT+'/cache.png').convert('L')
    zone=[im.getpixel((x,y)) for x in range(60,200) for y in range(68,86)]
    ok('enregistré : texte de la zone déplacée visible (pas recouvert)', 'NOUVELLE ADRESSE' in txt and sum(1 for v in zone if v<100)>40, sum(1 for v in zone if v<100))
    # ---- onglet CV : modèles France, Australie, Nouvelle-Zélande
    import base64 as _b64
    pg.evaluate("localStorage.removeItem('glpdf.cv')")
    pg.click('.stab[data-panel=cv]'); pg.wait_for_timeout(300)
    ok('CV : onglet avec les 3 pays', pg.locator('#pCV [data-cv]').count()==3)
    attendus={'fr':['Expérience professionnelle','Formation','Permis et habilitations'],'au':['EMPLOYMENT HISTORY','REFEREES','White Card','Working Holiday visa holder'],'nz':['WORK EXPERIENCE','REFEREES','Working Holiday Visa, open work rights']}
    for c in ['fr','au','nz']:
        pg.click('[data-cv=%s]'%c); pg.wait_for_timeout(500); pg.click('[data-ex]'); pg.wait_for_timeout(400)
        # coordonnées reprises du CV d'un autre pays : l'exemple demande confirmation
        if pg.locator('.modal .btn.pri:has-text("Remplacer")').count(): pg.click('.modal .btn.pri:has-text("Remplacer")')
        pg.wait_for_timeout(2500)
        ok('CV %s : aperçu affiché'%c, pg.locator('.cvpages canvas').count()>=1 and 'page' in pg.inner_text('.cvpinfo'), pg.inner_text('.cvpinfo'))
        ok('CV %s : photo proposée seulement en France'%c, (pg.locator('[data-photo]').count()==1)==(c=='fr'))
        for st in ['moderne','classique','epure']:
            r=pg.evaluate("""async ([c,st])=>{const d=JSON.parse(localStorage.getItem('glpdf.cv'))[c]; d.style=st; const r=await window.__glCvBuild(c,d); let s=''; const u=r.bytes; for(let i=0;i<u.length;i+=8192) s+=String.fromCharCode.apply(null,u.subarray(i,i+8192)); return {b:btoa(s),p:r.pages};}""",[c,st])
            f=OUT+'/cv-%s-%s.pdf'%(c,st); open(f,'wb').write(_b64.b64decode(r['b']))
            t=subprocess.run(['pdftotext',f,'-'],capture_output=True,text=True).stdout
            plat=t.replace(' ','').replace(chr(10),'').lower()
            manque=[x for x in attendus[c]+['Julien Martin'] if x.replace(' ','').lower() not in plat]
            ok('CV %s %s : contenu complet, %d page(s)'%(c,st,r['p']), not manque and r['p']<=3, manque)
        pg.click('[data-x]'); pg.wait_for_timeout(300)
    pg.click('[data-cv=nz]'); pg.wait_for_timeout(600); pg.click('[data-go]'); pg.wait_for_timeout(2500)
    ok('CV : « Créer le PDF » ouvre le CV dans l’éditeur', 'CV Julien Martin - Nouvelle-Zélande.pdf' in pg.inner_text('#fname') and pg.evaluate("window.__glState().pages.length")>=1, pg.inner_text('#fname'))
    pg.evaluate("localStorage.removeItem('glpdf.cv')")
    pg.click('.stab[data-panel=tools]')
    # ---- modifier une ligne ne doit laisser aucun bandeau gris (fond blanc = blanc pur ; fond coloré conservé)
    pg.set_input_files('#fOpen',S+'/fond.pdf'); pg.wait_for_timeout(800)
    # le CV qui vient d'être créé n'est pas encore enregistré : le logiciel le demande
    ok('CV : protégé tant qu’il n’est pas enregistré', pg.locator('.modal button:has-text("Ne pas enregistrer")').count()==1)
    if pg.locator('.modal button:has-text("Ne pas enregistrer")').count(): pg.click('.modal button:has-text("Ne pas enregistrer")')
    pg.wait_for_timeout(1500)
    pg.click('[data-t=edit]'); pg.wait_for_timeout(300)
    boxes=sorted([pg.locator('.ti').nth(k).bounding_box() for k in range(pg.locator('.ti').count())], key=lambda r: r['y'])
    for bb in boxes:
        pg.mouse.click(bb['x']+bb['width']-2,bb['y']+bb['height']/2); pg.wait_for_timeout(1500)
        pg.keyboard.press('End'); pg.keyboard.type(' OK'); pg.wait_for_timeout(200); pg.keyboard.press('Escape'); pg.mouse.click(1300,880); pg.wait_for_timeout(300)
    bgs=pg.evaluate("window.__glState().pages[0].objs.filter(o=>o.wipe).map(o=>o.bg)")
    ok('modifier : fond blanc recouvert en blanc pur, fond gris conservé', len(bgs)==2 and bgs[0]=='#ffffff' and bgs[1]!='#ffffff' and abs(int(bgs[1][1:3],16)-217)<=6, bgs)
    with pg.expect_download() as d: pg.click('#bSave')
    p=OUT+'/fond-out.pdf'; shutil.copy(d.value.path(), p)
    subprocess.run(['pdftoppm','-r','72','-png','-singlefile',p,OUT+'/fond'],check=True)
    from PIL import Image
    im=Image.open(OUT+'/fond.png').convert('RGB')
    # haut de la zone recouverte (au-dessus des lettres) : là où un bandeau gris apparaîtrait
    px=[im.getpixel((x,y)) for x in range(70,290) for y in range(69,72)]
    ok('enregistré : aucun bandeau gris sur fond blanc', min(min(c) for c in px)>=250, min(min(c) for c in px))
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
    # ---- fenêtre « Demander à Claude » (aucune clé ; fausse API GitHub en lecture : rien n'est envoyé)
    from urllib.parse import unquote
    def gh(route, req):
        u=req.url
        if '/comments' in u:
            n=int(u.split('/issues/')[1].split('/')[0])
            return route.fulfill(json=[{'body':'⏳ Claude a bien reçu votre demande'},{'body':'✅ **Corrigé dans la version 9.9.9.**\n\nTest.'}] if n==7 else [{'body':'🕓 Demande reçue.'}])
        if '/issues?' in u:
            return route.fulfill(json=[{'number':8,'title':'[G&L PDF] (Test) police différente','state':'open','comments':1,'updated_at':'b'},
                                       {'number':7,'title':'[G&L PDF] (Test) zoom trop lent','state':'closed','comments':2,'updated_at':'a','closed_at':'2099-01-01T00:00:00Z'},
                                       {'number':6,'title':'[G&L PDF] (Autre) pas à moi','state':'open','comments':0,'updated_at':'c'}])
        return route.fulfill(status=404, body='')
    pg=b.new_page(viewport={'width':1366,'height':900}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.route('https://api.github.com/**', gh); pg.goto(APP); pg.wait_for_timeout(1000)
    pg.click('#bClaude'); pg.wait_for_timeout(300)
    ok('Claude : prénom demandé au premier usage (pas de clé)', pg.locator('#clNom').count()==1 and pg.locator('input[type=password]').count()==0)
    pg.fill('#clNom','Test'); pg.click('[data-save]'); pg.wait_for_timeout(300)
    pg.fill('#clTxt','Ceci est une demande de test automatique.'); pg.click('[data-go]'); pg.wait_for_timeout(300)
    href=pg.get_attribute('[data-open]','href') or ''
    ok('Claude : lien GitHub prêt avec la demande', href.startswith('https://github.com/vincentguiraud-hub/gl-pdf/issues/new?') and '[G&L PDF] (Test) Ceci est une demande' in unquote(href) and 'Version de l’éditeur' in unquote(href), href[:160])
    pg.click('[data-ct=list]'); pg.wait_for_timeout(1500)
    sts=[x.inner_text() for x in pg.locator('.req .st').all()]
    ok('Claude : suivi (en attente / fait), seulement mes demandes', len(sts)==2 and 'validation' in sts[0] and '9.9.9' in sts[1], sts)
    pg.click('[data-back]'); pg.wait_for_timeout(300)
    href=unquote(pg.get_attribute('[data-open]','href') or '')
    ok('Claude : retour à la version précédente préparé', '[Retour version] (Test)' in href)
    ok('Claude : aucune erreur', not errs, errs[:3])
    b.close()
fails=[r for r in results if not r[1]]
print('\n%d tests, %d réussis, %d échecs' % (len(results), len(results)-len(fails), len(fails)))
for f in fails: print(' ✗', f[0], '—', str(f[2])[:300])
sys.exit(1 if fails else 0)
