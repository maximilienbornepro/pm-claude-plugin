"""Crée des brouillons .eml « non envoyés » à partir de textes validés.

Chaque fichier texte d'entrée a la forme :
    À : a@x; b@y
    Cc : c@z
    Objet : ...
    (ligne vide)
    corps...

Pour chaque texte : un .eml (X-Unsent: 1) est gardé en copie locale, puis le message est ouvert dans
Outlook via un lien mailto: (fenêtre de rédaction avec le compte de l'utilisateur en expéditeur). Le
brouillon atterrit dans Brouillons quand la fenêtre est fermée. Le .eml ouvert directement n'a pas
d'expéditeur et n'est pas enregistré en brouillon (nouvel Outlook, constaté le 12/10).
Rien n'est envoyé par ce script.
"""
import argparse, subprocess, sys
from urllib.parse import quote
from email.message import EmailMessage
from pathlib import Path


def parse(texte: str):
    entete, _, corps = texte.strip("\n").partition("\n\n")
    champs = {}
    for ligne in entete.splitlines():
        cle, _, val = ligne.partition(":")
        champs[cle.strip().lower()] = val.strip()
    def adr(v):
        return ", ".join(a.strip() for a in v.replace(",", ";").split(";") if a.strip())
    return adr(champs.get("à", champs.get("a", ""))), adr(champs.get("cc", "")), champs.get("objet", ""), corps.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--file", nargs="+", required=True)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    out = Path(a.dir); out.mkdir(parents=True, exist_ok=True)
    for f in a.file:
        to, cc, objet, corps = parse(Path(f).read_text(encoding="utf-8"))
        if not to or not objet:
            sys.exit(f"{f} : destinataire ou objet manquant")
        m = EmailMessage()
        m["To"] = to
        if cc:
            m["Cc"] = cc
        m["Subject"] = objet
        m["X-Unsent"] = "1"
        m.set_content(corps)
        p = out / (Path(f).stem + ".eml")
        p.write_bytes(bytes(m))
        print(p)
        if not a.no_open:
            # mailto: dans Outlook explicitement (`open` seul lance Mail ; le .eml n'a pas d'expéditeur)
            url = ("mailto:" + to.replace(" ", "") + "?cc=" + quote(cc.replace(" ", ""), safe="@,")
                   + "&subject=" + quote(objet) + "&body=" + quote(corps.strip().replace("\n", "\r\n")))
            subprocess.run(["open", "-a", "Microsoft Outlook", url], check=False)


if __name__ == "__main__":
    main()
