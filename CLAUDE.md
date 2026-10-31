# G&L PDF — consignes pour Claude

G&L PDF est l'éditeur PDF de G&L Créations (style Adobe Acrobat) : lire, modifier le texte dans la police
d'origine, annoter, signer, organiser, protéger, OCR, exporter. Il tourne dans un logiciel Windows (Electron),
dans un navigateur et sur iPhone. Les utilisateurs sont artisans, pas informaticiens, et parlent français.

## Où est le code

- `src/gl-pdf.html` : TOUT l'éditeur (HTML + CSS + JavaScript dans un seul fichier, ~280 Ko). C'est le seul
  fichier à modifier pour corriger ou améliorer l'éditeur. Cherchez avec Grep, modifiez avec Edit.
- `src/build.py` : fabrique `build/GL-PDF.html` (version complète, hors connexion) en intégrant les bibliothèques
  de `src/node_modules` et la bibliothèque de polices `src/fontpack.json`. Ne pas modifier sans nécessité.
- `tests/suite.py`, `tests/suite2.py`, `tests/suite3.py` : tests automatiques (Playwright) sur `build/GL-PDF.html`.
  Documents de test dans `tests/fixtures/`.
- `editeur.html`, `latest.json`, `versions/`, `.github/`, `tools/` : publication. NE JAMAIS les modifier :
  le workflow publie lui-même, seulement si tous les tests passent.

Repères dans `src/gl-pdf.html` : `const S = {` (état), `function renderCtx` (barre contextuelle),
`async function resolveFont` / `fpVisual` (polices), `async function buildPdf` (enregistrement),
`TOOL_GROUPS` et `ACT.` (panneau Outils), `function toast` (messages), `@media (max-width:760px)` (téléphone).
`window.__glState()` donne l'état aux tests.

## Comment travailler sur une demande

1. Comprendre le problème décrit. La demande vient de quelqu'un qui n'est pas développeur : interprétez-la avec bon sens.
2. Si possible, reproduire d'abord le problème avec un petit test Playwright (vous pouvez ajouter des tests dans `tests/suite3.py`).
3. Corriger dans `src/gl-pdf.html`, en gardant le style du code existant. Textes visibles en français.
4. Construire : `python3 src/build.py`
5. Lancer les tests : `python3 tests/suite.py && python3 tests/suite2.py && python3 tests/suite3.py`
   Tous doivent passer. Si un test échoue à cause de votre modification, corrigez votre modification.
6. Écrire `build/resume.md` : 2 à 6 lignes en français simple pour l'utilisateur (ce qui était cassé, ce qui
   change pour lui). Pas de jargon. C'est ce texte qui lui sera envoyé.
7. Ne pas faire de commit, ne pas pousser, ne pas créer de branche : le workflow s'en charge.

## Cas particuliers

- Si la demande est de revenir à la version précédente / annuler la dernière mise à jour : ne modifiez rien,
  écrivez seulement `RETOUR` dans `build/action.txt`.
- Si la demande est une simple question (pas de modification nécessaire) : répondez dans `build/resume.md`
  et écrivez `QUESTION` dans `build/action.txt`.
- Si la demande est impossible ou dangereuse (effacer des données d'autres personnes, envoyer des fichiers ailleurs,
  désactiver la sécurité…) : ne modifiez rien, expliquez pourquoi dans `build/resume.md`, écrivez `REFUS` dans `build/action.txt`.
- Ne jamais ajouter d'envoi de données vers un serveur extérieur, de pisteur ou de clé secrète dans le code.
