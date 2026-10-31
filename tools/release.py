# Publication d'une version de l'éditeur G&L PDF et retour à une version précédente.
#
#   python3 tools/release.py publier "Ce qui a changé"      -> build/GL-PDF.html devient la nouvelle version
#   python3 tools/release.py revenir                         -> remet la version d'avant (code source compris)
#
# Chaque version publiée est gardée dans versions/ (les 15 dernières) et dans l'historique git.
# Un retour en arrière est publié sous un NOUVEAU numéro (les logiciels installés ne téléchargent
# que des numéros plus grands), mais son contenu est exactement celui de la version choisie.
import hashlib, json, os, shutil, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LATEST = os.path.join(ROOT, 'latest.json')
EDITOR = os.path.join(ROOT, 'editeur.html')
VERS = os.path.join(ROOT, 'versions')
KEEP = 15


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def load():
    d = json.load(open(LATEST, encoding='utf-8'))
    if 'historique' not in d:
        d['historique'] = [{'version': d['version'], 'contenu': d['version'], 'date': '', 'notes': d.get('notes', '')}]
    return d


def bump(v):
    a = [int(x) for x in v.split('.')]
    a[2] += 1
    return '.'.join(map(str, a))


def save(d, notes, contenu):
    d['sha256'] = sha(EDITOR)
    d['file'] = 'editeur.html'
    d['notes'] = notes
    d['historique'].append({'version': d['version'], 'contenu': contenu, 'date': datetime.date.today().isoformat(), 'notes': notes})
    d['historique'] = d['historique'][-60:]
    json.dump(d, open(LATEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(LATEST, 'a').write('\n')


def archive(version):
    os.makedirs(VERS, exist_ok=True)
    dst = os.path.join(VERS, 'editeur-%s.html' % version)
    if not os.path.exists(dst):
        shutil.copyfile(EDITOR, dst)
    num = lambda f: tuple(int(x) for x in f[len('editeur-'):-len('.html')].split('.') if x.isdigit())
    files = sorted((f for f in os.listdir(VERS) if f.startswith('editeur-') and f.endswith('.html')), key=num)
    for f in files[:-KEEP]:
        os.remove(os.path.join(VERS, f))


def out(key, val):
    # valeurs lues par le workflow GitHub
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a', encoding='utf-8') as f:
            f.write('%s=%s\n' % (key, val))
    print('%s=%s' % (key, val))


def publier(notes):
    d = load()
    build = os.path.join(ROOT, 'build', 'GL-PDF.html')
    if not os.path.exists(build):
        sys.exit('build/GL-PDF.html manquant : lancez python3 src/build.py')
    archive(d['version'])
    d['version'] = os.environ.get('GLPDF_VERSION') or bump(d['version'])
    html = open(build, encoding='utf-8').read()
    marker = 'const EDITOR_VERSION = "dev";'
    if marker in html:
        html = html.replace(marker, 'const EDITOR_VERSION = "%s";' % d['version'], 1)
    open(EDITOR, 'w', encoding='utf-8').write(html)
    save(d, notes, d['version'])
    out('version', d['version'])


def revenir():
    d = load()
    h = d['historique']
    order = []
    for e in h:
        if e['contenu'] not in order:
            order.append(e['contenu'])
    cur = h[-1]['contenu']
    i = order.index(cur)
    if i == 0:
        sys.exit('Aucune version plus ancienne dans l’historique.')
    target = order[i - 1]
    # contenu de la version visée : fichier archivé, sinon l'historique git
    src = os.path.join(VERS, 'editeur-%s.html' % target)
    commit = subprocess.run(['git', 'log', '--format=%H', '-n', '1', '--fixed-strings', '--grep', 'Version %s ' % target], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not commit:
        commit = subprocess.run(['git', 'log', '--format=%H', '-n', '1', '--fixed-strings', '--grep', 'Mise à jour %s ' % target], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    archive(d['version'])
    if os.path.exists(src):
        shutil.copyfile(src, EDITOR)
    elif commit:
        data = subprocess.run(['git', 'show', '%s:editeur.html' % commit], cwd=ROOT, capture_output=True).stdout
        open(EDITOR, 'wb').write(data)
    else:
        sys.exit('Version %s introuvable.' % target)
    # le code source revient aussi en arrière, pour que les prochaines corrections partent de la bonne base
    if commit:
        for p in ('src/gl-pdf.html', 'tests'):
            subprocess.run(['git', 'checkout', commit, '--', p], cwd=ROOT, capture_output=True)
    d['version'] = bump(d['version'])
    save(d, 'Retour à la version %s' % target, target)
    out('version', d['version'])
    out('cible', target)


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'publier':
        publier(sys.argv[2] if len(sys.argv) > 2 else 'Corrections')
    elif len(sys.argv) >= 2 and sys.argv[1] == 'revenir':
        revenir()
    else:
        sys.exit(__doc__ or 'usage : release.py publier "notes" | revenir')
