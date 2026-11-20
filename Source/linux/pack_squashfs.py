#!/usr/bin/env python3
"""Minimal standards-format SquashFS 4 writer for this small, single-metadata-block AppDir.
Uses zlib, no fragments; all paths and inode records must fit single 8KiB metadata blocks.
"""
from pathlib import Path
import struct, stat, sys, zlib, time
P=struct.pack
ROOT=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2])
BS=131072
NODES=[]

def add(path,parent):
    s=path.lstat()
    typ=1 if path.is_dir() else 2
    if path.is_symlink(): typ=2
    node={'path':path,'name':path.name,'parent':parent,'type':typ,'mode':(s.st_mode & 0o777) if typ==1 else (0o755 if s.st_mode & 0o111 else 0o644),'mtime':int(time.time()),'num':len(NODES)+1,'children':[]}
    NODES.append(node)
    if parent is not None:parent['children'].append(node)
    if typ==1:
        for child in sorted(path.iterdir(),key=lambda p:p.name):add(child,node)
    return node
root=add(ROOT,None)
blob=bytearray(b'\x00'*96)
for n in NODES:
    if n['type']!=2:continue
    content=n['path'].read_bytes()
    n['size']=len(content)
    n['start']=len(blob)
    n['blocks']=[]
    for pos in range(0,len(content),BS):
        chunk=content[pos:pos+BS]
        compressed=zlib.compress(chunk,9)
        if len(compressed)<len(chunk):data=compressed; size=len(data)
        else:data=chunk;size=(len(chunk)|0x01000000)
        n['blocks'].append(size)
        blob.extend(data)
# Calculate fixed inode offsets (all in one 8KiB metadata block)
inode_stream=bytearray()
for n in NODES:
    n['inode_off']=len(inode_stream)
    nsize=32 if n['type']==1 else 32+4*len(n['blocks'])
    inode_stream+=b'\x00'*nsize
assert len(inode_stream)<=8192
# create the directory stream and store offset/length for each directory
dir_stream=bytearray()
for n in NODES:
    if n['type']!=1:continue
    n['dir_off']=len(dir_stream)
    children=n['children']
    if children:
        base=children[0]['num']
        dir_stream += P('<III',len(children)-1,0,base)
        for c in children:
            name=c['name'].encode()
            assert 1<=len(name)<=255 and b'/' not in name
            dir_stream+=P('<HhHH',c['inode_off'],c['num']-base,c['type'],len(name)-1)+name
    n['dir_size']=len(dir_stream)-n['dir_off']+3
assert len(dir_stream)<=8192
# Fill fixed-size inode structure
inode_stream=bytearray()
for n in NODES:
    assert len(inode_stream)==n['inode_off']
    inode_stream+=P('<HHHHII',n['type'],n['mode'],0,0,n['mtime'],n['num'])
    if n['type']==1:
        inode_stream+=P('<IIHHI',0,len(n['children'])+2,n['dir_size'],n['dir_off'],n['parent']['num'] if n['parent'] else 0)
    else:
        inode_stream+=P('<IIII',n['start'],0xffffffff,0,n['size'])
        for x in n['blocks']:inode_stream+=P('<I',x)

def append_metadata(raw):
    compressed=zlib.compress(raw,9)
    if len(compressed)<len(raw): return P('<H',len(compressed))+compressed
    return P('<H',0x8000|len(raw))+raw
inode_start=len(blob);blob+=append_metadata(inode_stream)
dir_start=len(blob);blob+=append_metadata(dir_stream)
id_data_start=len(blob);blob+=append_metadata(P('<I',0))
id_ptr_start=len(blob);blob+=P('<Q',id_data_start)
used=len(blob)
blob+=b'\x00'*(-len(blob)%4096)
missing=0xffffffffffffffff
superblock=P('<IIIIIHHHHHHQQQQQQQQ',0x73717368,len(NODES),int(time.time()),BS,0,1,17,0x10|0x200,1,4,0,root['inode_off'],used,id_ptr_start,missing,inode_start,dir_start,missing,missing)
assert len(superblock)==96
blob[:96]=superblock
OUT.write_bytes(blob)
print(f'SquashFS v4: {len(NODES)} inodes, {used} bytes used, {len(blob)} bytes padded, directory offsets {len(dir_stream)} bytes')
