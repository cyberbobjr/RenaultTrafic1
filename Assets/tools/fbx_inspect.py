"""Minimal binary FBX reader: global axes, unit scale, Model nodes with their local transforms
and parents, deformers (skin clusters) per mesh, animation stacks.
Usage: python fbx_inspect.py <file.fbx>"""
import struct, sys, zlib


def read_node(f, ver):
    if ver >= 7500:
        end, nprops, plen = struct.unpack('<QQQ', f.read(24))
    else:
        end, nprops, plen = struct.unpack('<III', f.read(12))
    nlen = f.read(1)[0]
    name = f.read(nlen).decode('latin-1')
    if end == 0:
        return None
    props = []
    for _ in range(nprops):
        t = f.read(1).decode()
        if t == 'Y': props.append(struct.unpack('<h', f.read(2))[0])
        elif t == 'C': props.append(f.read(1)[0] != 0)
        elif t == 'I': props.append(struct.unpack('<i', f.read(4))[0])
        elif t == 'F': props.append(struct.unpack('<f', f.read(4))[0])
        elif t == 'D': props.append(struct.unpack('<d', f.read(8))[0])
        elif t == 'L': props.append(struct.unpack('<q', f.read(8))[0])
        elif t in 'fdlib':
            n, enc, clen = struct.unpack('<III', f.read(12))
            data = f.read(clen)
            if enc == 1:
                data = zlib.decompress(data)
            fmt = {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': 'B'}[t]
            props.append(list(struct.unpack('<%d%s' % (n, fmt), data)))
        elif t in 'SR':
            n = struct.unpack('<I', f.read(4))[0]
            raw = f.read(n)
            props.append(raw.decode('latin-1') if t == 'S' else raw)
    children = []
    while f.tell() < end:
        c = read_node(f, ver)
        if c is None:
            break
        children.append(c)
    f.seek(end)
    return (name, props, children)


def load(path):
    with open(path, 'rb') as f:
        f.read(23)
        ver = struct.unpack('<I', f.read(4))[0]
        nodes = []
        while True:
            n = read_node(f, ver)
            if n is None:
                break
            nodes.append(n)
    return ver, nodes


def child(node, name):
    return [c for c in node[2] if c[0] == name]


def p70(node):
    out = {}
    for pp in child(node, 'Properties70'):
        for p in pp[2]:
            out[p[1][0]] = p[1][4:]
    return out


def main(path):
    ver, nodes = load(path)
    top = {n[0]: n for n in nodes}
    gs = p70(child(top['GlobalSettings'], 'Properties70') and top['GlobalSettings'])
    print('FBX', ver, {k: gs.get(k) for k in ('UpAxis', 'UpAxisSign', 'FrontAxis', 'FrontAxisSign', 'CoordAxis',
                                              'CoordAxisSign', 'UnitScaleFactor', 'OriginalUnitScaleFactor')})
    objs = {}
    for o in top['Objects'][2]:
        objs[o[1][0]] = o
    parent = {}
    for c in top['Connections'][2]:
        if c[1][0] == 'OO':
            parent.setdefault(c[1][1], []).append(c[1][2])
    names = {k: (o[0], o[1][1].split('\x00')[0], o[1][2] if len(o[1]) > 2 else '') for k, o in objs.items()}
    for k, o in objs.items():
        if o[0] != 'Model':
            continue
        p = p70(o)
        par = [names[x][1] for x in parent.get(k, []) if x in names and names[x][0] == 'Model'] or ['<root>']
        tr = {n: [round(v, 3) for v in p[n]] for n in ('Lcl Translation', 'Lcl Rotation', 'Lcl Scaling', 'PreRotation',
                                                        'PostRotation', 'GeometricTranslation', 'GeometricRotation') if n in p}
        print('Model', names[k][1], names[k][2], 'parent:', par[0], tr)
    for k, o in objs.items():
        if o[0] == 'Deformer' and names[k][2] == 'Cluster':
            tl = child(o, 'TransformLink')
            t = child(o, 'Transform')
            if tl:
                m = tl[0][1][0]
                print('Cluster', names[k][1], 'TransformLink T', [round(m[12], 2), round(m[13], 2), round(m[14], 2)],
                      'X', [round(v, 2) for v in m[0:3]], 'Y', [round(v, 2) for v in m[4:7]])
            if t:
                m = t[0][1][0]
                print('        Transform T', [round(m[12], 2), round(m[13], 2), round(m[14], 2)],
                      'X', [round(v, 2) for v in m[0:3]], 'Y', [round(v, 2) for v in m[4:7]])
    # animated nodes: AnimationCurveNode -OP-> Model, curve node -OO-> layer -OO-> stack
    target = {}
    for c in top['Connections'][2]:
        if c[1][0] == 'OP' and c[1][1] in names and names[c[1][1]][0] == 'AnimationCurveNode':
            target[c[1][1]] = (names.get(c[1][2], ('', '?'))[1], c[1][3])
    owner = {}
    for c in top['Connections'][2]:
        if c[1][0] == 'OO':
            owner[c[1][1]] = c[1][2]
    per_stack = {}
    for cn, (model, prop) in target.items():
        layer = owner.get(cn)
        stack = names.get(owner.get(layer), ('', '?'))[1]
        per_stack.setdefault(stack, set()).add('%s.%s' % (model, prop.replace('Lcl ', '')[0]))
    for k, o in objs.items():
        if o[0] == 'AnimationStack':
            print('AnimStack', names[k][1], sorted(per_stack.get(names[k][1], [])))


if __name__ == '__main__':
    main(sys.argv[1])
