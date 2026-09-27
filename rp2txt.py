#!/usr/bin/env python
"""rp2txt.py -- turn a SillyTavern roleplay into the two files a music-video crew reads.

    python rp2txt.py --find <name>                  # chats whose character or file name matches (newest first)
    python rp2txt.py --grep "a phrase"              # chats whose MESSAGES contain it (slow on big archives)
    python rp2txt.py "<chat.jsonl>" --out notes/chat.txt [--card "<card name or .png>"] [--card-out notes/card.md]
                     [--world "<lorebook name or .json>"] [--persona "<persona name>"]
    add --st <folder> if SillyTavern isn't found by itself (its root, or its data/<user> folder), or set ST_DATA

chat.txt: every ACTIVE message (swipes skipped) as '##### [n] Name (user)  date' + the text. Everyone cites messages by
          n, and each painter gets a message RANGE in its brief.
card.md:  the card (creator notes, description, personality, scenario, first message, alternate greetings, examples:
          its AUTHOR is the credit to use, exactly), every embedded lorebook entry, a standalone lorebook with --world,
          and the user's persona description with --persona (from SillyTavern's settings).
Reads SillyTavern's files and never writes to them. Exported files work too: a chat exported as .jsonl from the chat
menu, and a character card exported as .png. Stdlib only.
"""
import argparse
import base64
import glob
import json
import os
import struct
import sys

ST = None


# ------------------------------------------------------------------ finding SillyTavern's data folder
def user_dir(root):
    """a SillyTavern root or data folder or user folder -> the user folder (the one holding chats/ and characters/)"""
    root = os.path.abspath(os.path.expanduser(root))
    if os.path.isdir(os.path.join(root, 'chats')) or os.path.isdir(os.path.join(root, 'characters')):
        return root
    for data in (os.path.join(root, 'data'), root):
        if not os.path.isdir(data):
            continue
        cands = [os.path.join(data, d) for d in os.listdir(data) if os.path.isdir(os.path.join(data, d, 'chats'))]
        if cands:
            pref = [c for c in cands if os.path.basename(c) == 'default-user']
            return (pref or sorted(cands, key=lambda c: -os.path.getmtime(os.path.join(c, 'chats'))))[0]
    return None


def find_st(given=None):
    if given:
        u = user_dir(given)
        if not u:
            sys.exit(f'no SillyTavern data under {given} (want a folder with data/<user>/chats)')
        return u
    if os.environ.get('ST_DATA'):
        return find_st(os.environ['ST_DATA'])
    home = os.path.expanduser('~')
    cands = [os.path.join(home, x) for x in ('SillyTavern', 'sillytavern', 'Documents/SillyTavern', 'Desktop/SillyTavern',
                                             'Downloads/SillyTavern', 'SillyTavern-Launcher/SillyTavern')]
    if os.name == 'nt':
        for drive in 'CDEF':
            cands += [f'{drive}:/SillyTavern', f'{drive}:/Program Files/SillyTavern']
    for c in cands:
        if os.path.isdir(c):
            u = user_dir(c)
            if u:
                return u
    for pat in ('*/SillyTavern*', '*/*/SillyTavern*'):             # one or two levels under home
        for c in glob.glob(os.path.join(home, pat)):
            u = user_dir(c) if os.path.isdir(c) else None
            if u:
                return u
    return None


def st():
    global ST
    if ST is None:
        ST = find_st()
        if not ST:
            sys.exit('SillyTavern not found: pass --st <its folder> (or set ST_DATA), or pass exported files directly')
    return ST


# ------------------------------------------------------------------ chats
def chat_files():
    root = st()
    out = []
    for sub in ('chats', 'group chats'):
        base = os.path.join(root, sub)
        if os.path.isdir(base):
            out += glob.glob(os.path.join(base, '**', '*.jsonl'), recursive=True)
    return out


def messages(path):
    msgs = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if isinstance(m, dict) and 'mes' in m:           # the first line is the chat's metadata: no 'mes'
                msgs.append(m)
    return msgs


def listing(hits):
    for mt, fp, n in sorted(hits, reverse=True):
        print(f'{n:6d} msgs  {fp}')
    print(len(hits), 'chat(s) in', st())


def find(term):
    t = term.lower()
    hits = []
    for fp in chat_files():
        if t in fp.lower():
            try:
                n = len(messages(fp))
            except OSError:
                n = -1
            hits.append((os.path.getmtime(fp), fp, n))
    listing(hits)


def grep(text):
    t = text.lower()
    hits = []
    for fp in chat_files():
        try:
            ms = messages(fp)
        except OSError:
            continue
        k = [i for i, m in enumerate(ms) if t in (m.get('mes') or '').lower()]
        if k:
            hits.append((os.path.getmtime(fp), fp + f'   (messages {", ".join(map(str, k[:8]))}{"..." if len(k) > 8 else ""})',
                         len(ms)))
    listing(hits)


def chat_txt(path, out):
    msgs = messages(path)
    buf = []
    for n, m in enumerate(msgs):
        who = m.get('name', '?') + (' (user)' if m.get('is_user') else '') + (' (system)' if m.get('is_system') else '')
        text = (m.get('mes') or '').replace('\r\n', '\n').strip()
        buf.append(f"##### [{n}] {who}  {m.get('send_date', '')}\n{text}\n")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(buf))
    users = sorted({m.get('name') for m in msgs if m.get('is_user')})
    chars = sorted({m.get('name') for m in msgs if not m.get('is_user') and not m.get('is_system')})
    print(f'{out}: {len(msgs)} messages (the user as: {", ".join(users) or "?"}; characters: {", ".join(chars) or "?"})')
    return users


# ------------------------------------------------------------------ cards, lorebooks, personas
def png_text(path):
    """a PNG's tEXt chunks as {keyword: text} (the card JSON lives in 'chara' (V2) or 'ccv3' (V3))"""
    out = {}
    with open(path, 'rb') as f:
        if f.read(8) != b'\x89PNG\r\n\x1a\n':
            raise SystemExit(f'not a PNG: {path}')
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            n, kind = struct.unpack('>I4s', head)
            data = f.read(n)
            f.read(4)
            if kind == b'tEXt':
                k, _, v = data.partition(b'\x00')
                out[k.decode('latin-1')] = v.decode('latin-1')
            if kind == b'IEND':
                break
    return out


def entries(book, label):
    out = [f'## Lorebook: {label}', '']
    es = book.get('entries', [])
    es = list(es.values()) if isinstance(es, dict) else es
    for e in es:
        keys = e.get('keys') or e.get('key') or []
        name = e.get('comment') or e.get('name') or ', '.join(keys[:2])
        off = e.get('disable') or (e.get('enabled') is False)
        out += [f"##### {name} | keys={keys} | disabled={bool(off)}", (e.get('content') or '').replace('\r\n', '\n'), '']
    return out, len(es)


def persona_md(name):
    """the user's persona description from SillyTavern's settings.json (personas: avatar -> name; descriptions)"""
    try:
        s = json.load(open(os.path.join(st(), 'settings.json'), encoding='utf-8'))
    except (OSError, ValueError, SystemExit):
        return []
    pu = s.get('power_user') or {}
    names, descs = pu.get('personas') or {}, pu.get('persona_descriptions') or {}
    out = []
    for avatar, nm in names.items():
        if nm and nm.lower() == name.lower():
            d = descs.get(avatar) or {}
            text = d.get('description') if isinstance(d, dict) else str(d)
            if text:
                out += [f'## Persona: {nm} (the user)', text.replace('\r\n', '\n'), '']
    return out


def card_md(card, out, world=None, personas=()):
    p = card if card.lower().endswith('.png') else os.path.join(st(), 'characters', f'{card}.png')
    if not os.path.isfile(p):
        sys.exit(f'no card at {p} (give the .png, or the name as SillyTavern shows it)')
    t = png_text(p)
    raw = t.get('ccv3') or t.get('chara')
    if not raw:
        raise SystemExit(f'no card JSON in {p}')
    j = json.loads(base64.b64decode(raw).decode('utf-8'))
    d = j.get('data', j)
    md = [f"# {d.get('name', '?')}: the card" + (f" (by {d.get('creator')})" if d.get('creator') else ''), '']
    for key, title in [('creator_notes', 'Creator notes'), ('description', 'Description'), ('personality', 'Personality'),
                       ('scenario', 'Scenario'), ('first_mes', 'First message'), ('mes_example', 'Example messages'),
                       ('system_prompt', 'System prompt'), ('post_history_instructions', 'Post-history instructions')]:
        v = (d.get(key) or '').strip()
        if v:
            md += [f'## {title}', v.replace('\r\n', '\n'), '']
    for i, g in enumerate(d.get('alternate_greetings') or []):
        md += [f'## Alternate greeting {i + 1}', g.replace('\r\n', '\n'), '']
    nbook = nworld = 0
    if d.get('character_book'):
        lines, nbook = entries(d['character_book'], 'embedded in the card')
        md += lines
    if world:
        wp = world if world.lower().endswith('.json') else os.path.join(st(), 'worlds', f'{world}.json')
        lines, nworld = entries(json.load(open(wp, encoding='utf-8')), f'world "{os.path.basename(wp)}"')
        md += lines
    for name in personas:
        md += persona_md(name)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(md))
    print(f"{out}: card '{d.get('name')}' by {d.get('creator') or '(no creator field: ask the user who made it)'}; "
          f"{nbook} embedded + {nworld} world lorebook entries")


def main():
    global ST
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('chat', nargs='?')
    ap.add_argument('--st', help="SillyTavern's folder (or its data/<user> folder)")
    ap.add_argument('--find')
    ap.add_argument('--grep')
    ap.add_argument('--out', default='notes/chat.txt')
    ap.add_argument('--card')
    ap.add_argument('--card-out', default='notes/card.md')
    ap.add_argument('--world')
    ap.add_argument('--persona', action='append', default=[], help="the user's persona name (repeatable)")
    a = ap.parse_args()
    if a.st:
        ST = find_st(a.st)
    if a.find:
        find(a.find)
        return
    if a.grep:
        grep(a.grep)
        return
    users = []
    if a.chat:
        path = a.chat if os.path.isfile(a.chat) else os.path.join(st(), 'chats', a.chat)
        users = chat_txt(path, a.out)
    if a.card:
        card_md(a.card, a.card_out, a.world, a.persona or [u for u in users if u])
    if not (a.chat or a.card):
        ap.print_help()


if __name__ == '__main__':
    main()
