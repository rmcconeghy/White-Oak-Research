"""Small read-only OOXML reader; preserves stored numbers (no display scaling)."""
import zipfile, xml.etree.ElementTree as ET, posixpath
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def sheets(path):
 with zipfile.ZipFile(path) as z:
  strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
  rel={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
  out={}
  for sh in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets',NS):
   target=rel[sh.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
   name=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
   rows={}
   for row in ET.fromstring(z.read(name)).find('m:sheetData',NS):
    cells={}
    for c in row:
     v=c.findtext('m:v',default='',namespaces=NS)
     if c.get('t')=='s': v=strings[int(v)]
     elif c.get('t')=='inlineStr': v=''.join(c.find('m:is',NS).itertext())
     cells[''.join(x for x in c.get('r') if x.isalpha())]=v
    rows[int(row.get('r'))]=cells
   out[sh.get('name')]=rows
  return out
