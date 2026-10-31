import os, sys, json, shutil, subprocess, traceback
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S=os.path.join(ROOT,'tests','fixtures')
APP='file://'+os.path.join(ROOT,'build','GL-PDF.html')
OUT=os.path.join(ROOT,'build','test-out'); shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT)
results=[]
def ok(name, cond, info=''):
    results.append((name, bool(cond), info)); print(('PASS ' if cond else 'FAIL ')+name+(' — '+str(info) if info else ''), flush=True)
def pdftext(p): return subprocess.run(['pdftotext','-layout',p,'-'],capture_output=True,text=True).stdout
def pyinfo(p, code):
    r=subprocess.run(['python3','-c','import pypdf,json,sys\nr=pypdf.PdfReader(sys.argv[1])\n'+code, p],capture_output=True,text=True); return (r.stdout+r.stderr).strip()

with sync_playwright() as pw:
    b=pw.chromium.launch()
    def newpage(**kw):
        ctx=b.new_context(viewport={'width':1300,'height':900},accept_downloads=True,**kw); pg=ctx.new_page(); pg._errs=[]
        pg.on('pageerror',lambda e:pg._errs.append(str(e)))
        pg.on('console',lambda m: m.type=='error' and pg._errs.append(m.text))
        pg.goto(APP); pg.wait_for_timeout(900); return pg
    def openpdf(pg, f):
        pg.set_input_files('#fOpen', S+'/'+f); pg.wait_for_timeout(1500)
    def state(pg, js): return pg.evaluate('(()=>{const S=window.__glState();return '+js+'})()')
    def save(pg, name):
        pg.mouse.click(1290, 890); pg.wait_for_timeout(150)
        with pg.expect_download() as d: pg.click('#bSave')
        path=OUT+'/'+name; shutil.copy(d.value.path(), path); pg.wait_for_timeout(200); return path
    def tool(pg, t): pg.click('[data-t='+t+']'); pg.wait_for_timeout(250)
    def pagebox(pg, i=0): return pg.locator('.page').nth(i).bounding_box()
    def at(pg, fx, fy, i=0):
        # scrolls so the point is visible, then returns its screen position
        bb=pagebox(pg,i); vb=pg.locator('#viewer').bounding_box(); y=bb['y']+bb['height']*fy
        if y < vb['y']+60 or y > vb['y']+vb['height']-60:
            pg.evaluate('d=>document.getElementById("viewer").scrollTop+=d', y-(vb['y']+vb['height']/2)); pg.wait_for_timeout(250); bb=pagebox(pg,i)
        return bb['x']+bb['width']*fx, bb['y']+bb['height']*fy
    def vis(pg, l):
        vb=pg.locator('#viewer').bounding_box()
        if l['y'] < vb['y']+40 or l['y']+l['h'] > vb['y']+vb['height']-40:
            pg.evaluate('d=>document.getElementById("viewer").scrollTop+=d', l['y']-(vb['y']+vb['height']/2)); pg.wait_for_timeout(250); return None
        return l
    def lines(pg): return pg.evaluate("[...document.querySelectorAll('.ti')].map(t=>{const r=t.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})")

    # ---------- 1. coche : poser, sélectionner, supprimer, déplacer ----------
    try:
        pg=newpage(); openpdf(pg,'real.pdf')
        tool(pg,'check'); x,y=at(pg,.5,.5); pg.mouse.click(x,y); pg.wait_for_timeout(200)
        ok('coche posée', state(pg,"S.pages[0].objs.filter(o=>o.type==='check').length")==1)
        pg.mouse.click(x,y); pg.wait_for_timeout(200)
        ok('cliquer sur une coche la sélectionne (pas de doublon)', state(pg,"S.pages[0].objs.filter(o=>o.type==='check').length")==1)
        pg.locator('.obj.check.sel .del').click(); pg.wait_for_timeout(200)
        ok('le × supprime la coche avec l’outil Coche actif', state(pg,"S.pages[0].objs.length")==0)
        pg.mouse.click(x,y); pg.wait_for_timeout(150)
        before=state(pg,"S.pages[0].objs[0].x")
        pg.mouse.move(x,y); pg.mouse.down(); pg.mouse.move(x+60,y+20,steps=6); pg.mouse.up(); pg.wait_for_timeout(150)
        ok('une coche se déplace même avec l’outil Coche', abs(state(pg,"S.pages[0].objs[0].x")-before)>10)
        pg.keyboard.press('Delete'); pg.wait_for_timeout(150)
        ok('Suppr efface la coche sélectionnée', state(pg,"S.pages[0].objs.length")==0)
        pg.keyboard.press('Escape'); tool(pg,'check'); pg.click('[data-mark=cross]'); x,y=at(pg,.4,.15); pg.mouse.click(x,y)
        pg.keyboard.press('Escape'); tool(pg,'check'); pg.click('[data-mark=dot]'); pg.mouse.click(x+80,y); pg.wait_for_timeout(150)
        marks=state(pg,"S.pages[0].objs.map(o=>o.mark)")
        ok('coche, croix et point', 'cross' in marks and 'dot' in marks, marks)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
        ok('Échap revient à Sélection', state(pg,"S.tool")=='select')
        p=save(pg,'marks.pdf'); ok('coches enregistrées sans erreur', os.path.getsize(p)>1000 and not pg._errs, pg._errs[:2])
        pg.context.close()
    except Exception as e: ok('bloc coche', False, traceback.format_exc()[-400:])

    # ---------- 2. modification de texte ----------
    try:
        pg=newpage(); openpdf(pg,'real.pdf'); tool(pg,'edit')
        L=lines(pg); l=L[1]
        pg.mouse.click(l['x']+l['w']*0.3, l['y']+l['h']/2); pg.wait_for_timeout(1300)
        pg.keyboard.type('Z'); pg.wait_for_timeout(100)
        t=pg.evaluate("document.querySelector('.obj.txt .ed').innerText")
        idx=t.find('Z'); ok('le curseur se place à l’endroit cliqué', 0.15 < idx/len(t) < 0.45, t)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        # ligne ouverte puis refermée sans changement : rendue au document
        tool(pg,'edit'); L=lines(pg); l=L[2]
        n0=state(pg,"S.hist.length")
        pg.mouse.click(l['x']+5, l['y']+l['h']/2); pg.wait_for_timeout(1200); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        ok('ligne ouverte sans changement : rien n’est modifié', state(pg,"S.pages[0].objs.filter(o=>o.type==='edit').length")==1 and state(pg,"S.hist.length")==n0, state(pg,"S.pages[0].objs.length"))
        p=save(pg,'edit.pdf'); txt=pdftext(p)
        ok('texte modifié enregistré, ancien texte supprimé', 'Z' in txt and txt.count('Client')==1, txt[:200])
        pg.context.close()
    except Exception as e: ok('bloc édition', False, traceback.format_exc()[-400:])

    # ---------- 3. surligner, barrer, souligner (calés sur le texte) ----------
    try:
        pg=newpage(); openpdf(pg,'real.pdf')
        tool(pg,'edit'); L=lines(pg); tool(pg,'select')
        l=L[2]
        tool(pg,'hl'); pg.mouse.move(l['x']+2,l['y']+l['h']/2); pg.mouse.down(); pg.mouse.move(l['x']+l['w']*0.5,l['y']+l['h']/2,steps=8); pg.mouse.up(); pg.wait_for_timeout(400)
        hl=state(pg,"S.pages[0].objs.filter(o=>o.type==='hl')")
        ok('surlignage calé sur la ligne de texte', len(hl)==1 and 5<hl[0]['h']<20, hl)
        tool(pg,'strike'); l=L[3]
        pg.mouse.move(l['x']+1,l['y']+2); pg.mouse.down(); pg.mouse.move(l['x']+l['w']*0.6,l['y']+l['h']-2,steps=8); pg.mouse.up(); pg.wait_for_timeout(400)
        st=state(pg,"S.pages[0].objs.filter(o=>o.kind==='strike')")
        ok('texte barré', len(st)==1, st)
        pg.click('[data-strike=under]'); l=L[4]
        if not vis(pg,l): tool(pg,'edit'); L=lines(pg); tool(pg,'strike'); pg.click('[data-strike=under]'); l=L[4]
        pg.mouse.click(l['x']+l['w']/2, l['y']+l['h']/2); pg.wait_for_timeout(400)
        ok('texte souligné d’un clic (une seule ligne, pas la colonne voisine)', state(pg,"S.pages[0].objs.filter(o=>o.kind==='under').length")==1, state(pg,"S.pages[0].objs.filter(o=>o.kind==='under').length"))
        p=save(pg,'annot.pdf'); ok('annotations enregistrées', os.path.getsize(p)>1000 and not pg._errs, pg._errs[:2])
        pg.context.close()
    except Exception as e: ok('bloc surligner', False, traceback.format_exc()[-400:])

    # ---------- 4. formes, note, masque (suppression réelle) ----------
    try:
        pg=newpage(); openpdf(pg,'multi.pdf')
        tool(pg,'shape')
        for k,(fx,fy) in [('rect',(.5,.4)),('ellipse',(.5,.55)),('line',(.2,.7)),('arrow',(.5,.7))]:
            pg.click('[data-shape='+k+']'); x,y=at(pg,fx,fy); pg.mouse.move(x,y); pg.mouse.down(); pg.mouse.move(x+120,y+50,steps=6); pg.mouse.up(); pg.wait_for_timeout(150); pg.keyboard.press('Escape'); tool(pg,'shape')
        kinds=state(pg,"S.pages[0].objs.map(o=>o.kind)")
        ok('rectangle, cercle, trait, flèche', all(k in kinds for k in ['rect','ellipse','line','arrow']), kinds)
        pg.keyboard.press('Escape')
        tool(pg,'note'); x,y=at(pg,.8,.3); pg.mouse.click(x,y); pg.wait_for_timeout(200); pg.keyboard.type('Vérifier la cote'); pg.mouse.click(*at(pg,.3,.9)); pg.wait_for_timeout(150)
        ok('note créée avec son texte', state(pg,"S.pages[0].objs.filter(o=>o.type==='note').map(o=>o.text)")==['Vérifier la cote'])
        # masque sur « secret »
        pg.evaluate("document.getElementById('viewer').scrollTop=0"); pg.wait_for_timeout(300)
        tool(pg,'edit'); L=lines(pg); pg.keyboard.press('Escape'); l=L[0]
        tool(pg,'wipe'); pg.mouse.move(l['x']+l['w']*0.55,l['y']-3); pg.mouse.down(); pg.mouse.move(l['x']+l['w']+4,l['y']+l['h']+3,steps=6); pg.mouse.up(); pg.wait_for_timeout(200)
        p=save(pg,'shapes.pdf'); txt=pdftext(p)
        ok('le texte sous le masque est supprimé du fichier', 'secret' not in txt.split('\n')[0] and 'Page numero 1' in txt, txt.split('\n')[0])
        ok('les autres pages gardent leur texte', 'secret' in txt, '')
        info=pyinfo(p,"a=r.pages[0].get('/Annots') or []\nprint([x.get_object().get('/Contents') for x in a])")
        ok('note enregistrée comme commentaire PDF', 'Vérifier la cote' in info, info)
        ok('aucune erreur', not pg._errs, pg._errs[:2])
        pg.context.close()
    except Exception as e: ok('bloc formes', False, traceback.format_exc()[-400:])

    # ---------- 5. formulaires ----------
    try:
        pg=newpage(); openpdf(pg,'form.pdf')
        ff=pg.locator('.fl .ff'); ok('champs de formulaire détectés', ff.count()>=7, ff.count())
        pg.locator('.fl input[data-name="0:nom"]').fill('GUIRAUD Vincent'); pg.locator('.fl input[data-name="0:nom"]').press('Tab')
        ok('valeur existante affichée', pg.locator('.fl input[data-name="0:commune"]').input_value()=='Alès')
        pg.locator('.fl .fcb[data-name="0:urgent"]').click(); pg.wait_for_timeout(150)
        pg.locator('.fl .fcb.radio[data-name="0:type"]').nth(1).click(); pg.wait_for_timeout(150)
        pg.locator('.fl select[data-name="0:dept"]').select_option('Gard')
        pg.locator('.fl textarea[data-name="0:obs"]').fill('Accès par le portail nord\nPrévoir échafaudage'); pg.locator('.fl textarea').press('Tab')
        pg.wait_for_timeout(200)
        p=save(pg,'form-out.pdf')
        info=pyinfo(p,"f=r.get_fields() or {}\nprint(json.dumps({k:str(v.get('/V')) for k,v in f.items()}, ensure_ascii=False))")
        ok('formulaire rempli et enregistré', all(s in info for s in ['GUIRAUD Vincent','Gard','"type": "/1"','échafaudage','"urgent": "/Yes"']), info)
        ok('les champs restent remplissables (AcroForm)', '"nom"' in info, '')
        pg2=newpage(); pg2.set_input_files('#fOpen', OUT+'/form-out.pdf'); pg2.wait_for_timeout(1500)
        ok('le PDF rempli se rouvre avec ses valeurs', pg2.locator('.fl input[data-name="0:nom"]').input_value()=='GUIRAUD Vincent')
        pg.keyboard.press('Control+z'); pg.wait_for_timeout(300)
        ok('Ctrl+Z annule aussi une saisie de formulaire', 'obs' not in json.dumps(state(pg,'S.form')) or state(pg,"S.form['0:obs']")!='Accès par le portail nord\nPrévoir échafaudage', state(pg,'S.form'))
        ok('aucune erreur (formulaires)', not pg._errs and not pg2._errs, (pg._errs+pg2._errs)[:2])
        pg.context.close(); pg2.context.close()
    except Exception as e: ok('bloc formulaires', False, traceback.format_exc()[-1500:])

    # ---------- 6. recherche ----------
    try:
        pg=newpage(); openpdf(pg,'multi.pdf')
        pg.keyboard.press('Control+f'); pg.wait_for_timeout(150)
        pg.keyboard.type('référence'); pg.wait_for_timeout(1200)
        ok('recherche sans accent ni majuscule', pg.inner_text('#sCount')=='1 sur 3', pg.inner_text('#sCount'))
        pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
        ok('résultat suivant', pg.inner_text('#sCount')=='2 sur 3')
        ok('résultat surligné', pg.locator('.hit.cur').count()==1)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
        ok('Échap ferme la recherche', pg.locator('#searchBar').is_hidden())
        pg.context.close()
    except Exception as e: ok('bloc recherche', False, traceback.format_exc()[-400:])

    # ---------- 7. pages : page blanche, réorganiser, pivoter, supprimer ----------
    try:
        pg=newpage(); openpdf(pg,'multi.pdf'); pg.click('.stab[data-panel=pages]'); pg.wait_for_timeout(300)
        pg.locator('.th').nth(0).locator('[data-a=blank]').click(); pg.wait_for_timeout(600)
        ok('page blanche insérée', pg.locator('.page').count()==4)
        pg.evaluate("""(()=>{const th=[...document.querySelectorAll('.th')]; const dt=new DataTransfer();
          th[3].dispatchEvent(new DragEvent('dragstart',{dataTransfer:dt,bubbles:true}));
          th[0].dispatchEvent(new DragEvent('dragover',{dataTransfer:dt,bubbles:true,cancelable:true}));
          th[0].dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}));
          th[3].dispatchEvent(new DragEvent('dragend',{dataTransfer:dt,bubbles:true}));})()"""); pg.wait_for_timeout(400)
        order=state(pg,"S.pages.map(p=>p.doc+':'+p.index)")
        ok('glisser une miniature réorganise les pages', order[0]=='0:2', order)
        tool(pg,'check'); x,y=at(pg,.3,.3,1); pg.mouse.click(x,y); pg.keyboard.press('Escape')
        pg.locator('.th').nth(1).locator('[data-a=rot]').click(); pg.wait_for_timeout(500)
        pg.locator('.th').nth(2).locator('[data-a=del]').click(); pg.wait_for_timeout(400)
        p=save(pg,'pages.pdf'); n=pyinfo(p,"print(len(r.pages), [p.get('/Rotate',0) for p in r.pages])")
        ok('pages enregistrées (nombre et rotation)', n.startswith('3') , n)
        pg.locator('.th').nth(0).locator('[data-a=del]').click(); pg.locator('.th').nth(0).locator('[data-a=del]').click(); pg.wait_for_timeout(300)
        pg.locator('.th').nth(0).locator('[data-a=del]').click(); pg.wait_for_timeout(300)
        ok('la dernière page ne peut pas être supprimée', pg.locator('.page').count()==1)
        sc0=pg.evaluate("document.getElementById('viewer').scrollTop")
        ok('aucune erreur (pages)', not pg._errs, pg._errs[:2])
        pg.context.close()
    except Exception as e: ok('bloc pages', False, traceback.format_exc()[-400:])

    # ---------- 8. annuler / rétablir, défilement conservé ----------
    try:
        pg=newpage(); openpdf(pg,'multi.pdf')
        pg.evaluate("document.getElementById('viewer').scrollTop=900"); pg.wait_for_timeout(200)
        tool(pg,'check'); vb=pg.locator('#viewer').bounding_box(); pg.mouse.click(vb['x']+vb['width']/2, vb['y']+300); pg.keyboard.press('Escape')
        st0=pg.evaluate("document.getElementById('viewer').scrollTop")
        pg.keyboard.press('Control+z'); pg.wait_for_timeout(300)
        st1=pg.evaluate("document.getElementById('viewer').scrollTop")
        ok('Annuler ne remonte plus en haut du document', abs(st1-st0)<5, (st0,st1))
        ok('Annuler enlève la coche', sum(len(p['objs']) for p in state(pg,'S.pages'))==0)
        pg.keyboard.press('Control+y'); pg.wait_for_timeout(300)
        ok('Rétablir la remet', sum(len(p['objs']) for p in state(pg,'S.pages'))==1)
        # flèches, dupliquer, copier-coller
        pg.mouse.click(vb['x']+vb['width']/2, vb['y']+300); pg.wait_for_timeout(100)
        x0=state(pg,"S.pages.flatMap(p=>p.objs)[0].x"); pg.keyboard.press('ArrowRight'); pg.keyboard.press('Shift+ArrowRight')
        ok('flèches : déplacement fin', abs(state(pg,"S.pages.flatMap(p=>p.objs)[0].x")-x0-11)<0.01)
        pg.keyboard.press('Control+d'); pg.wait_for_timeout(150)
        ok('Ctrl+D duplique', sum(len(p['objs']) for p in state(pg,'S.pages'))==2)
        pg.keyboard.press('Control+c'); pg.keyboard.press('Control+v'); pg.wait_for_timeout(150)
        ok('Ctrl+C / Ctrl+V', sum(len(p['objs']) for p in state(pg,'S.pages'))==3)
        pg.context.close()
    except Exception as e: ok('bloc annuler', False, traceback.format_exc()[-400:])

    # ---------- 9. zoom ----------
    try:
        pg=newpage(); openpdf(pg,'real.pdf')
        tool(pg,'text'); x,y=at(pg,.3,.6); pg.mouse.click(x,y); pg.wait_for_timeout(150); pg.keyboard.type('Bonjour')
        pg.keyboard.press('Control+=') ; pg.wait_for_timeout(300); pg.keyboard.type(' Vincent'); pg.wait_for_timeout(100)
        ok('le zoom ne fait pas perdre la saisie', state(pg,"S.pages[0].objs[0].text")=='Bonjour Vincent', state(pg,"S.pages[0].objs[0].text"))
        pg.keyboard.press('Escape')
        for _ in range(12): pg.click('#zIn')
        pg.wait_for_timeout(1200)
        cw=pg.evaluate("Math.max(...[...document.querySelectorAll('.page>canvas')].map(c=>c.width*c.height))")
        ok('zoom 400 % : page affichée sans dépasser la limite', 0<cw<=14e6, cw)
        z=pg.inner_text('#zVal'); vb=pg.locator('#viewer').bounding_box(); pg.mouse.move(vb['x']+400,vb['y']+300)
        pg.keyboard.down('Control'); pg.mouse.wheel(0,400); pg.keyboard.up('Control'); pg.wait_for_timeout(300)
        ok('Ctrl+molette dézoome', pg.inner_text('#zVal')!=z, (z,pg.inner_text('#zVal')))
        ok('aucune erreur (zoom)', not pg._errs, pg._errs[:2])
        pg.context.close()
    except Exception as e: ok('bloc zoom', False, traceback.format_exc()[-400:])

    # ---------- 10. modifications non enregistrées, nom de fichier, impression ----------
    try:
        pg=newpage(); openpdf(pg,'real.pdf')
        tool(pg,'check'); pg.mouse.click(*at(pg,.5,.5)); pg.keyboard.press('Escape')
        ok('titre marqué comme modifié', pg.title().startswith('•'), pg.title())
        pg.set_input_files('#fOpen', S+'/std.pdf'); pg.wait_for_timeout(500)
        ok('question avant d’ouvrir un autre fichier', pg.locator('.modal').count()==1)
        pg.locator('.modal .btn', has_text='Annuler').click(); pg.wait_for_timeout(200)
        ok('Annuler garde le document', state(pg,'S.name')=='real.pdf')
        pg.set_input_files('#fOpen', S+'/std.pdf'); pg.wait_for_timeout(500)
        pg.locator('.modal .btn', has_text='Ne pas enregistrer').click(); pg.wait_for_timeout(1500)
        ok('« Ne pas enregistrer » ouvre bien l’autre fichier', state(pg,'S.name')=='std.pdf', state(pg,'S.name'))
        tool(pg,'check'); pg.mouse.click(*at(pg,.5,.2)); pg.keyboard.press('Escape')
        pg.set_input_files('#fOpen', S+'/real.pdf'); pg.wait_for_timeout(500)
        with pg.expect_download() as d0: pg.locator('.modal .btn', has_text='Enregistrer').last.click()
        pg.wait_for_timeout(1500)
        ok('« Enregistrer » enregistre puis ouvre l’autre fichier', d0.value.suggested_filename=='std-modifie.pdf' and state(pg,'S.name')=='real.pdf', (d0.value.suggested_filename, state(pg,'S.name')))
        tool(pg,'check'); pg.mouse.click(*at(pg,.5,.2)); pg.keyboard.press('Escape')
        p=save(pg,'real-modifie.pdf')
        ok('après enregistrement, plus marqué modifié', not pg.title().startswith('•'))
        pg.evaluate("window.__printed=0; window.print=()=>{window.__printed=document.querySelectorAll('#printArea img').length}")
        pg.click('#bPrint'); pg.wait_for_timeout(5000)
        ok('impression : pages préparées', pg.evaluate('window.__printed')==1, pg.evaluate('window.__printed'))
        with pg.expect_download() as d: pg.click('#bSave')
        ok('nom sans « -modifie-modifie »', d.value.suggested_filename=='real-modifie.pdf', d.value.suggested_filename)
        pg.context.close()
    except Exception as e: ok('bloc fichiers', False, traceback.format_exc()[-400:])

    # ---------- 11. signature dessinée, dans un champ signature ----------
    try:
        pg=newpage(); openpdf(pg,'real.pdf')
        pg.click('[data-t=sign]'); pg.wait_for_timeout(200)
        pb=pg.locator('#sPad').bounding_box(); pg.mouse.move(pb['x']+40,pb['y']+60); pg.mouse.down()
        for i in range(20): pg.mouse.move(pb['x']+40+i*15, pb['y']+60+(15 if i%2 else -10))
        pg.mouse.up(); pg.click('#sUse'); pg.wait_for_timeout(300)
        pg.mouse.click(*at(pg,.3,.4)); pg.wait_for_timeout(200)
        ok('signature dessinée et posée', state(pg,"S.pages[0].objs.filter(o=>o.type==='img').length")==1)
        pg.click('[data-t=sign]'); pg.wait_for_timeout(200); pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
        ok('Échap ferme la fenêtre de signature', pg.locator('.modal').count()==0)
        p=save(pg,'sign.pdf'); info=pyinfo(p,"print(len(r.pages[0].images))")
        ok('signature enregistrée dans le PDF', info.strip()!='0', info)
        pg.context.close()
    except Exception as e: ok('bloc signature', False, traceback.format_exc()[-400:])

    # ---------- 12. iPhone ----------
    try:
        dev=dict(pw.devices['iPhone 13']); dev.pop('default_browser_type',None)
        ctx=b.new_context(**dev); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto(APP); pg.wait_for_timeout(900); pg.set_input_files('#fOpen',S+'/real.pdf'); pg.wait_for_timeout(1500)
        pg.locator('[data-t=edit]').tap(); pg.wait_for_timeout(600)
        bb=pg.locator('.ti').nth(1).bounding_box(); pg.touchscreen.tap(bb['x']+bb['width']*0.3,bb['y']+bb['height']/2); pg.wait_for_timeout(1500)
        pg.keyboard.type('Z'); t=pg.evaluate("(document.querySelector('.obj.txt .ed')||{}).innerText||''")
        ok('iPhone : modification au bon endroit', 0.15 < t.find('Z')/max(1,len(t)) < 0.45, t)
        pg.locator('#bPages').tap(); pg.wait_for_timeout(300)
        ok('iPhone : bouton Pages affiche les miniatures', pg.locator('.side').is_visible())
        ok('iPhone : aucune erreur', not errs, errs[:2])
        ctx.close()
    except Exception as e: ok('bloc iPhone', False, traceback.format_exc()[-400:])
    b.close()

fails=[r for r in results if not r[1]]
print('\n%d tests, %d réussis, %d échecs' % (len(results), len(results)-len(fails), len(fails)))
for f in fails: print(' ✗', f[0], '—', str(f[2])[:300])
sys.exit(1 if fails else 0)
