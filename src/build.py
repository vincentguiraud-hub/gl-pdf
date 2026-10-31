# Construit l'éditeur complet hors connexion : build/GL-PDF.html
# Usage : (cd src && npm ci) puis python3 src/build.py
import base64,re,os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
os.makedirs(os.path.join(ROOT,'build'),exist_ok=True)
s=open(os.path.join(HERE,'gl-pdf.html'),encoding='utf-8').read()
old="if (!dl){ toast('L’enregistrement n’est pas disponible dans cet affichage. Ouvrez la page dans claude.ai.'); return; }"
new="if (!dl){ const u = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' })); const a = document.createElement('a'); a.href = u; a.download = fname; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 4000); toast('Enregistré : ' + fname + ' (dossier Téléchargements)'); return; }"
if old in s: s=s.replace(old,new)
nm=os.path.join(HERE,'node_modules')+'/'
def f64(p): return base64.b64encode(open(nm+p,'rb').read()).decode()
faces=[('Barlow',400,'@fontsource/barlow/files/barlow-latin-400-normal.woff2'),('Barlow',500,'@fontsource/barlow/files/barlow-latin-500-normal.woff2'),('Barlow',600,'@fontsource/barlow/files/barlow-latin-600-normal.woff2'),
('Barlow Condensed',600,'@fontsource/barlow-condensed/files/barlow-condensed-latin-600-normal.woff2'),('Barlow Condensed',700,'@fontsource/barlow-condensed/files/barlow-condensed-latin-700-normal.woff2'),
('Caveat',500,'@fontsource/caveat/files/caveat-latin-500-normal.woff2'),('Mrs Saint Delafield',400,'@fontsource/mrs-saint-delafield/files/mrs-saint-delafield-latin-400-normal.woff2')]
css=''.join("@font-face{font-family:'%s';font-weight:%d;font-style:normal;font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}"%(a,w,f64(p)) for a,w,p in faces)
o=s
o=re.sub(r'<link rel="preconnect"[^>]*>\n','',o)
o=re.sub(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>','<style>'+css+'</style>',o)
o=o.replace('<meta name="claude:viewport-fit-sides" content="cover">','<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
def inl(path): return '<script>'+open(nm+path,encoding='utf-8').read().replace('</script','<\\/script')+'</script>'
# real background worker in the offline build (keeps the window responsive on big PDFs)
wtag='<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js"></script>'
assert wtag in o
o=o.replace(wtag,'<script type="text/js-worker" id="pdfw">'+open(nm+'pdfjs-dist/build/pdf.worker.min.js',encoding='utf-8').read().replace('</script','<\\/script')+'</script>'+inl('pdfjs-dist/build/pdf.worker.min.js'))
ws='pdfjs.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";'
assert ws in o
o=o.replace(ws,"try { pdfjs.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([document.getElementById('pdfw').textContent], { type: 'text/javascript' })); } catch(e){}")
for url,path in [('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js','pdfjs-dist/build/pdf.min.js'),
 ('https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js','pdf-lib/dist/pdf-lib.min.js'),('https://cdn.jsdelivr.net/npm/@cantoo/pdf-lib@2.11.1/dist/pdf-lib.min.js','@cantoo/pdf-lib/dist/pdf-lib.min.js'),('https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js','jszip/dist/jszip.min.js'),('https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.min.js','pptxgenjs/dist/pptxgen.min.js'),('https://cdn.jsdelivr.net/npm/@pdf-lib/fontkit@1.1.1/dist/fontkit.umd.min.js','@pdf-lib/fontkit/dist/fontkit.umd.min.js')]:
    tag='<script src="%s"></script>'%url; assert tag in o, url; o=o.replace(tag,inl(path))
ocr=('<script type="text/js-worker" id="tessCore">'+open(nm+'tesseract.js-core/tesseract-core-simd-lstm.wasm.js',encoding='utf-8').read().replace('</script','<\\/script')+'</script>'
  +'<script type="text/js-worker" id="tessWorker">'+open(nm+'tesseract.js/dist/worker.min.js',encoding='utf-8').read().replace('</script','<\\/script')+'</script>'
  +'<script type="text/plain" id="tessFra">'+base64.b64encode(open(nm+'@tesseract.js-data/fra/4.0.0_best_int/fra.traineddata.gz','rb').read()).decode()+'</script>'
  +inl('tesseract.js/dist/tesseract.min.js'))
o=o.replace('<div id="printArea"></div>','<div id="printArea"></div>\n'+ocr,1)
# bibliothèque de 57 familles de polices libres (version logiciel et hors connexion)
o=o.replace('<div id="printArea"></div>','<div id="printArea"></div>\n<script type="application/json" id="fontPack">'+open(os.path.join(HERE,'fontpack.json'),encoding='utf-8').read()+'</script>',1)
k='</style>\n\n<div class="app tool-select"'; assert o.count(k)==1
o=o.replace(k,'</style>\n</head>\n<body>\n<div class="app tool-select"')
o='<!doctype html>\n<html lang="fr">\n<head>\n'+o+'\n</body>\n</html>\n'
open(os.path.join(ROOT,'build','GL-PDF.html'),'w',encoding='utf-8').write(o); print(len(o)//1024,'Ko')
