#!/usr/bin/env python3
"""Finalize hashes AFTER current mesh and previews, without any supplier access."""
import hashlib,json,pathlib,re,zipfile
root=pathlib.Path(__file__).parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
mesh=json.loads((root/'mesh-check.json').read_text())
assert mesh['outline_source_sha256']==sha(root/'outline-study.json')
assert mesh['mesh_sha256']==sha(root/'views/board-envelope.stl')
assert mesh['watertight'] and mesh['winding_consistent'] and mesh['volume_mm3']>0
for f,h in json.loads((root/'views/render-provenance.json').read_text()).items():assert sha(root/'views'/f)==h,f
with zipfile.ZipFile(root/'manufacturing-draft.zip') as z:
    assert set(z.namelist())=={f.name for f in (root/'manufacturing').iterdir() if f.is_file()}
    for name in z.namelist():assert z.read(name)==(root/'manufacturing'/name).read_bytes(),name
for file in [*root.glob('*.md'),root/'../../kb/pcb-design.md']:
    for target in re.findall(r'\]\(([^)]+)\)',file.read_text()):
        if not target.startswith(('https:','http:','#')):assert (file.parent/target.split('#')[0]).exists(),(file,target)
files=['feeder.kicad_sch','feeder.kicad_pcb','feeder.kicad_pro','feeder-unrouted.kicad_pcb','feeder-unrouted.kicad_pro',
       'feeder.dsn','feeder.ses','assembly-bom.csv','assembly-cpl.csv','assembly-bom-all.csv','assembly-cpl-all.csv',
       'quotation-bom-all.csv','design-bom.csv','connectivity.json','schematic-netlist.xml','stock-evidence.json',
       'assembly-reconciliation.json','review-baseline.json','review-fix-validation.json',
       'manufacturing-draft.zip','erc.rpt','drc.rpt','validation.json','outline-study.json','mesh-check.json',
       'fp-lib-table','sym-lib-table','Dockerfile','../../kb/pcb-design.md']
files += [str(f.relative_to(root)) for pattern in ['*.py','*.md','feeder.pretty/*.kicad_mod','views/*','manufacturing/*'] for f in sorted(root.glob(pattern)) if f.is_file()]
assert len(files)==len(set(files))
(root/'checksums.json').write_text(json.dumps({f:sha(root/f) for f in files},indent=2)+'\n')
print(f'Finalized {len(files)} hashes; ZIP, mesh provenance, rendered views and documentation links verified.')
print('checksums.json SHA256',sha(root/'checksums.json'))
