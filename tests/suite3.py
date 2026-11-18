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
    # ---- onglet CV : éditeur complet (lignes prêtes, traduction, modèles, photo)
    import base64 as _b64, json as _json
    pg.route('**/api.mymemory.translated.net/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{"responseStatus":200,"responseData":{"translatedText":"I am a very motivated craftsman &amp; reliable."}}'))
    # reprise d'un CV de l'ancienne version
    pg.evaluate("""()=>{['glpdf.cv2','glpdf.cv2.migrated','glpdf.cv.mem','glpdf.cv.tab'].forEach(k=>localStorage.removeItem(k)); localStorage.setItem('glpdf.cv.web','yes');
      localStorage.setItem('glpdf.cv', JSON.stringify({fr:{name:'Ancien Nom',title:'Maçon',summary:'Ancien profil',exp:[{title:'Maçon',company:'SARL Test',start:'2019',end:'aujourd’hui',tasks:'Montage de murs\\nCoffrage'}],skills:'Coffrage\\nEnduit',langs:'Français (langue maternelle)'}}));}""")
    pg.click('.stab[data-panel=cv]'); pg.wait_for_timeout(300)
    st=pg.evaluate("window.__glCv.store()"); old=[c for c in st['cvs'].values() if c['name']=='Ancien Nom']
    ok('CV : ancien CV repris', len(old)==1 and old[0]['exp'][0]['end']['cur'] and len(old[0]['exp'][0]['tasks'])==2 and old[0]['exp'][0]['start']['y']=='2019', old[:1])
    pg.click('[data-cvnew]'); pg.wait_for_timeout(1200)
    ok('CV : éditeur ouvert avec toutes les rubriques', pg.locator('.cvnav [data-tab]').count()==15 and pg.locator('.cvpages canvas').count()>=1)
    for t in ['mes','design','photo','infos','profil','exp','edu','skills','langs','certs','plus','refs','sections','trad','check']:
        pg.click('.cvnav [data-tab=%s]'%t); pg.wait_for_timeout(150)
    ok('CV : toutes les rubriques s’affichent sans erreur', not errs, errs[:3])
    pg.click('.cvnav [data-tab=infos]'); pg.wait_for_timeout(200)
    pg.fill('[data-p=name][data-f=v]','Test Dupont'); pg.select_option('[data-p=trade]','metal'); pg.wait_for_timeout(200)
    pg.click('[data-pick=title]'); pg.wait_for_timeout(200); pg.locator('.cvpki').nth(1).click(); pg.wait_for_timeout(200)
    ok('CV : intitulé choisi dans la liste', pg.input_value('[data-p=title][data-f=fr]')=='Soudeur')
    pg.click('.cvnav [data-tab=exp]'); pg.click('[data-add=exp]'); pg.wait_for_timeout(200)
    pg.click('[data-pick=tasks]'); pg.wait_for_timeout(200)
    for k in range(3): pg.locator('.cvpki').nth(k).click()
    pg.locator('.cvpki').nth(0).click()  # déjà ajoutée : pas de doublon
    pg.click('[data-done]'); pg.wait_for_timeout(700)
    ok('CV : 3 missions ajoutées en un clic, sans doublon', pg.evaluate("window.__glCv.store().cvs[window.__glCv.store().current].exp[0].tasks.length")==3)
    pg.click('.cvnav [data-tab=profil]'); pg.fill('[data-p=summary][data-f=fr]','Je suis un artisan très motivé et fiable.'); pg.wait_for_timeout(300)
    # passage en Australie : tout se traduit tout seul
    pg.click('[data-tgt=au]'); pg.wait_for_timeout(4000)
    cur=lambda: pg.evaluate("(()=>{const s=window.__glCv.store(); return s.cvs[s.current];})()")
    c=cur()
    ok('CV : traduction automatique de vos phrases', c['summary']['en']=='I am a very motivated craftsman & reliable.' and c['summary']['auto'], c['summary'])
    ok('CV : lignes prêtes traduites par la banque de phrases', c['title']['en']=='Welder' and c['exp'][0]['tasks'][0]['en'].startswith('Fabricated'), [c['title'], c['exp'][0]['tasks'][0]])
    ok('CV : anglais affiché sous le français', pg.input_value('[data-p=summary][data-f=en]')=='I am a very motivated craftsman & reliable.')
    pg.fill('[data-p=summary][data-f=en]','Highly motivated and reliable tradesman.'); pg.wait_for_timeout(200)
    ok('CV : traduction modifiable', 'relu par vous' in pg.inner_text('[data-st=summary]'))
    pg.fill('[data-p=summary][data-f=fr]','Je suis un artisan très motivé, fiable et ponctuel.'); pg.wait_for_timeout(1800)
    c=cur()
    ok('CV : votre traduction n’est pas écrasée (signalée à relire)', c['summary']['en']=='Highly motivated and reliable tradesman.' and 'relire' in pg.inner_text('[data-st=summary]'), c['summary'])
    r=pg.evaluate("window.__glCv.translate(['Soudeur','Disponible immédiatement'],'au')")
    ok('CV : banque de phrases', r[0]['en']=='Welder' and r[1]['en']=='Available immediately', r)
    ok('CV : orthographe australienne', pg.evaluate("window.__glCv.gloss('permis de conduire')").lower().find('licence')>=0, pg.evaluate("window.__glCv.gloss('permis de conduire')"))
    # vérification : visa et referees demandés pour l'Australie
    pg.click('.cvnav [data-tab=check]'); pg.wait_for_timeout(1500)
    chk=pg.inner_text('.cvchl')
    ok('CV : vérification (visa, referees)', 'visa' in chk and 'referees' in chk, chk[:300])
    # rubriques : masquer et renommer
    ex=pg.evaluate("window.__glCv.example()")
    def build(d):
        r=pg.evaluate("""async d=>{const r=await window.__glCvBuild2(d); let s=''; const u=r.bytes; for(let i=0;i<u.length;i+=8192) s+=String.fromCharCode.apply(null,u.subarray(i,i+8192)); return {b:btoa(s),p:r.pages};}""",d)
        return r
    photo='data:image/jpeg;base64,'+_b64.b64encode(open(S+'/photo.jpg','rb').read()).decode()
    attendus={'fr':['Expérience professionnelle','Formation','Permis et habilitations','Métallier-serrurier'],'au':['EMPLOYMENT HISTORY','REFEREES','Working Holiday visa holder','Metal Fabricator'],'nz':['WORK EXPERIENCE','REFEREES','Working Holiday Visa, open work rights','Metal Fabricator']}
    maxp={'fr':2,'au':3,'nz':2}; bad=[]
    for tpl in ['moderne','droite','banniere','chrono','classique','elegant','epure','compact']:
        for tg in ['fr','au','nz']:
            d=_json.loads(_json.dumps(ex)); d['design']['tpl']=tpl; d['target']=tg; d['photo']['src']=photo
            r=build(d); f=OUT+'/cv2-%s-%s.pdf'%(tpl,tg); open(f,'wb').write(_b64.b64decode(r['b']))
            t=subprocess.run(['pdftotext',f,'-'],capture_output=True,text=True).stdout
            plat=t.replace(' ','').replace(chr(10),'').lower()
            manque=[x for x in attendus[tg]+['Julien Martin'] if x.replace(' ','').lower() not in plat]
            imgs=subprocess.run(['pdfimages','-list',f],capture_output=True,text=True).stdout.count('\n')-2
            if manque or r['p']>maxp[tg] or (imgs>0)!=(tg=='fr'): bad.append((tpl,tg,manque,r['p'],imgs))
    ok('CV : 8 modèles × 3 pays complets (photo seulement en France)', not bad, bad)
    d=_json.loads(_json.dumps(ex)); d['target']='au'; d['hidden']={'interests':True}; d['titles']={'langs':{'fr':'Langues parlées','en':'Spoken languages'}}
    d['design'].update({'levels':'bars','size':'compact','font':'garamond','color':'#123456','dateFmt':'year'})
    r=build(d); f=OUT+'/cv2-opts.pdf'; open(f,'wb').write(_b64.b64decode(r['b'])); t=subprocess.run(['pdftotext',f,'-'],capture_output=True,text=True).stdout
    ok('CV : rubrique masquée, titre renommé, options', 'INTERESTS' not in t.upper() and 'SPOKEN LANGUAGES' in t.upper() and 'Mar 2020' not in t and 'EBGaramond' in subprocess.run(['pdffonts',f],capture_output=True,text=True).stdout, t[:200])
    d=_json.loads(_json.dumps(ex)); d['target']='au'; d['photo']['src']=photo; d['photo']['english']=True; d['photo']['bw']=True; d['photo']['shape']='rounded'
    f=OUT+'/cv2-photo-au.pdf'; open(f,'wb').write(_b64.b64decode(build(d)['b']))
    ok('CV : photo possible en anglais si demandé', subprocess.run(['pdfimages','-list',f],capture_output=True,text=True).stdout.count('\n')-2>=1)
    # données abîmées ou anciennes : rien ne plante
    r=pg.evaluate("""async()=>{const out=[]; for (const x of [null, {}, {exp:'x', skills:[null,{t:'a'}], design:{tpl:'inconnu'}, target:'xx', langs:[{fr:'Basque',lvl:'Z9'}]}]){ const r=await window.__glCvBuild2(window.__glCv.fix(x)); out.push(r.pages);} return out;}""")
    ok('CV : données incomplètes acceptées', r==[1,1,1], r)
    # sauvegarde dans un fichier puis reprise
    pg.click('.cvnav [data-tab=mes]'); pg.wait_for_timeout(200)
    with pg.expect_download() as dl: pg.click('[data-cvexp]')
    bk=OUT+'/cv-sauvegarde.json'; shutil.copy(dl.value.path(), bk); n0=len(_json.load(open(bk))['cvs'])
    with pg.expect_file_chooser() as fc: pg.click('[data-cvimp]')
    fc.value.set_files(bk); pg.wait_for_timeout(800)
    ok('CV : sauvegarde et reprise', n0>=2 and len(pg.evaluate("window.__glCv.store()")['cvs'])==2*n0, n0)
    # suppression avec « Annuler »
    pg.click('.cvnav [data-tab=exp]'); pg.wait_for_timeout(200)
    n=pg.locator('.cvitem').count(); pg.locator('[data-del=exp]').first.click(); pg.wait_for_timeout(200)
    n1=pg.locator('.cvitem').count(); pg.click('.toast button'); pg.wait_for_timeout(300)
    ok('CV : suppression annulable', n1==n-1 and pg.locator('.cvitem').count()==n, (n,n1))
    # plusieurs CV : renommer, dupliquer, supprimer
    pg.click('.cvnav [data-tab=mes]'); pg.wait_for_timeout(200); k=pg.locator('.cvmi').count()
    pg.locator('[data-cvdup]').first.click(); pg.wait_for_timeout(500); pg.click('.cvnav [data-tab=mes]'); pg.wait_for_timeout(200)
    k2=pg.locator('.cvmi').count(); pg.locator('[data-cvdel]').first.click(); pg.click('.cvover [data-y]'); pg.wait_for_timeout(500)
    ok('CV : dupliquer et supprimer', k2==k+1 and pg.locator('.cvmi').count()==k, (k,k2))
    # ouvrir dans l'éditeur PDF
    pg.click('.cvnav [data-tab=mes]'); pg.locator('[data-cvex]').click(); pg.wait_for_timeout(800)
    pg.click('[data-tgt=au]'); pg.wait_for_timeout(1500)
    pg.click('[data-go]'); pg.wait_for_timeout(3000)
    ok('CV : « Ouvrir dans G&L PDF » ouvre le CV', 'CV Julien Martin - Australie.pdf' in pg.inner_text('#fname') and pg.evaluate("window.__glState().pages.length")>=1, pg.inner_text('#fname'))
    ok('CV : aucune erreur', not errs, errs[:3])
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
    # ---- CV au téléphone
    pg.evaluate("localStorage.removeItem('glpdf.cv2'); localStorage.setItem('glpdf.cv2.migrated','1')")
    pg.evaluate("document.body.classList.add('show-side'); document.querySelector('.stab[data-panel=cv]').click(); document.querySelector('[data-cvnew]').click()"); pg.wait_for_timeout(1200)
    ok('téléphone CV : éditeur plein écran', pg.locator('.cvw2').bounding_box()['width']>=pg.viewport_size['width']-2 and pg.evaluate("(()=>{const c=document.querySelector('.cvw2');return c.scrollWidth<=c.clientWidth+1})()"))
    pg.tap('.cvnav [data-tab=exp]'); pg.wait_for_timeout(300); pg.tap('[data-add=exp]'); pg.wait_for_timeout(300)
    pg.tap('[data-pick=tasks]'); pg.wait_for_timeout(300); pg.locator('.cvpki').nth(0).tap(); pg.tap('[data-done]'); pg.wait_for_timeout(300)
    ok('téléphone CV : ligne prête ajoutée au doigt', pg.locator('.cvli').count()==1)
    fs=pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.cvli input')).fontSize)")
    ok('téléphone CV : champs sans zoom automatique (16 px)', fs>=16, fs)
    pg.tap('.cvtog [data-v=prev]'); pg.wait_for_timeout(2500)
    ok('téléphone CV : aperçu', pg.locator('.cvpages canvas').count()>=1 and pg.locator('.cvpages canvas').first.bounding_box()['width']<=pg.viewport_size['width'])
    pg.tap('.cvtog [data-v=form]'); pg.tap('[data-x]'); pg.wait_for_timeout(300)
    ok('téléphone CV : aucune erreur', not errs, errs[:3])
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
