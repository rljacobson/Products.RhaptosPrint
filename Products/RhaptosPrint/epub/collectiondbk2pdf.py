# python -c "import collectiondbk2pdf; print collectiondbk2pdf.__doStuff('./tests', 'modern-textbook');" > result.pdf

import sys
import os
import Image
from StringIO import StringIO
from tempfile import mkdtemp
import subprocess

from lxml import etree
import urllib2

import module2dbk
import collection2dbk
import util

DEBUG=False

FOP_PATH = os.path.join('fop')
BASE_PATH = os.path.join(os.getcwd())
#PRINT_STYLE='modern-textbook' # 'modern-textbook-2column'

# XSL files
DOCBOOK_CLEANUP_XSL = util.makeXsl('dbk-clean-whole.xsl')
ALIGN_XSL = util.makeXsl('fo-align-math.xsl')
XCONF_XSL = util.makeXsl('fop.xconf.template.xsl')
XCONF_TEMPLATE = etree.parse(os.path.join(BASE_PATH, 'xsl', 'fop.xconf.template.xml'))
#MARGINALIA_XSL = util.makeXsl('fo-marginalia.xsl')

#XINCLUDE_XPATH = etree.XPath('//xi:include', namespaces=util.NAMESPACES)

MODULES_XPATH = etree.XPath('//col:module/@document', namespaces=util.NAMESPACES)
IMAGES_XPATH = etree.XPath('//c:*/@src[not(starts-with(.,"http:"))]', namespaces=util.NAMESPACES)

def __doStuff(dir, printStyle):
  collxml = etree.parse(os.path.join(dir, 'collection.xml'))
  
  moduleIds = MODULES_XPATH(collxml)
  
  modules = {} # {'m1000': (etree.Element, {'file.jpg':'23947239874'})}
  allFiles = {}
  for moduleId in moduleIds:
    print >> sys.stderr, "LOG: Starting on %s" % (moduleId)
    moduleDir = os.path.join(dir, moduleId)
    if os.path.isdir(moduleDir):
      cnxml, files = loadModule(moduleDir)
      for f in files:
        allFiles[os.path.join(moduleId, f)] = files[f]

      modules[moduleId] = (cnxml, files)

  dbk, newFiles = collection2dbk.convert(collxml, modules, svg2png=False, math2svg=True)
  allFiles.update(newFiles)
  pdf, stdErr = convert(dbk, allFiles, printStyle)
  return pdf

def __doStuffModule(moduleId, dir, printStyle):
  cnxml, files = loadModule(dir)
  _, newFiles = module2dbk.convert(moduleId, cnxml, files, {}) # Last arg is coll params
  dbkStr = newFiles['index.standalone.dbk']
  dbk = etree.parse(StringIO(dbkStr))
  allFiles = {}
  allFiles.update(files)
  allFiles.update(newFiles)
  pdf, stdErr = convert(dbk, allFiles, printStyle)
  return pdf

# Given a directory of files (containing an index.cnxml) load it into memory
def loadModule(moduleDir):
  # Try autogenerated CNXML 1st
  cnxmlPath = os.path.join(moduleDir, 'index_auto_generated.cnxml')
  if not os.path.exists(cnxmlPath):
    cnxmlPath = os.path.join(moduleDir, 'index.cnxml')
  cnxmlStr = open(cnxmlPath).read()
  cnxml = etree.parse(StringIO(cnxmlStr))
  files = {}
  for f in IMAGES_XPATH(cnxml):
    try:
      data = open(os.path.join(moduleDir, f)).read()
      files[f] = data
      #print >> sys.stderr, "LOG: Image ADDED! %s %s" % (module, f)
    except IOError:
      print >> sys.stderr, "LOG: Image not found %s %s" % (os.path.basename(moduleDir), f)
  return (cnxml, files)

# Use Apache FOP to convert the XSL-FO to PDF
def fo2pdf(fo, files, tempdir):
  # Write all of the files into tempdir
  for fname, content in files.items():
    fpath = os.path.join(tempdir, fname)
    fdir = os.path.dirname(fpath)
    if not os.path.isdir(fdir):
      os.makedirs(fdir)
    #print >> sys.stderr, "LOG: Writing to %s" % fpath
    f = open(fpath, 'w')
    f.write(content)
    f.close()
  
  # Generate a custom XCONF file that points to the STIX fonts
  XCONF_PATH = os.path.join(tempdir, '_fop.xconf')

  xconfXml = XCONF_XSL(XCONF_TEMPLATE, **({'cnx.basepath': "'%s'" % BASE_PATH}))
  xconf = open(XCONF_PATH, 'w')
  xconf.write(etree.tostring(xconfXml))
  xconf.close()
  
  # Run FOP to generate an abstract tree 1st
  # strCmd = [FOP_PATH, ', '-c', XCONF_PATH, '/dev/stdin']
  strCmd = [FOP_PATH, '-q', '-c', XCONF_PATH, '-at', 'application/pdf', '/dev/stdout', '/dev/stdin']
  env = {'FOP_OPTS': '-Xmx14000M'}

  # run the program with subprocess and pipe the input and output to variables
  p = subprocess.Popen(strCmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True, env=env)
  # set STDIN and STDOUT and wait untill the program finishes
  stdOut, stdErr = p.communicate(etree.tostring(fo))
  abstractTree = stdOut
  if DEBUG:
    open('temp-collection5.at','w').write(abstractTree)

  strCmd = [FOP_PATH, '-q', '-c', XCONF_PATH, '-atin', '/dev/stdin', '/dev/stdout']

  # run the program with subprocess and pipe the input and output to variables
  p = subprocess.Popen(strCmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True, env=env)
  # set STDIN and STDOUT and wait untill the program finishes
  stdOut, stdErr2 = p.communicate(abstractTree)

  # Clean up the tempdir
  # Remove added files
  for fname in files:
    fpath = os.path.join(tempdir, fname)
    os.remove(fpath)
    fdir = os.path.dirname(fpath)
    if len(os.listdir(fdir)) == 0:
      os.rmdir(fdir)

  return stdOut, stdErr

def convert(dbk1, files, printStyle):
  tempdir = mkdtemp(suffix='-fo2pdf')

  def transform(xslDoc, xmlDoc):
    """ Performs an XSLT transform and parses the <xsl:message /> text """
    ret = xslDoc(xmlDoc, **({'cnx.output.fop': '1', 'cnx.tempdir.path':"'%s'" % tempdir}))
    for entry in xslDoc.error_log:
      # TODO: Log the errors (and convert JSON to python) instead of just printing
      print >> sys.stderr, entry
    return ret

  DOCBOOK2FO_XSL=util.makeXsl('%s.xsl' % printStyle)

  # Step 0 (Sprinkle in some index hints whenever terms are used)
  # termsprinkler.py $DOCBOOK > $DOCBOOK2
  if DEBUG:
    open('temp-collection1.dbk','w').write(etree.tostring(dbk1,pretty_print=True))

  # Step 1 (Cleaning up Docbook)
  dbk2 = transform(DOCBOOK_CLEANUP_XSL, dbk1)
  if DEBUG:
    open('temp-collection2.dbk','w').write(etree.tostring(dbk2,pretty_print=True))

  # Step 2 (Docbook to XSL:FO)
  fo1 = transform(DOCBOOK2FO_XSL, dbk2)
  if DEBUG:
    open('temp-collection3.fo','w').write(etree.tostring(fo1,pretty_print=True))

  # Step 3 (Aligning math in XSL:FO)
  fo = transform(ALIGN_XSL, fo1)
  if DEBUG:
    open('temp-collection4.fo','w').write(etree.tostring(fo,pretty_print=True))

  #import pdb; pdb.set_trace()
  # Step 4 Converting XSL:FO to PDF (using Apache FOP)
  # Change to the collection dir so the relative paths to images work
  pdf, stdErr = fo2pdf(fo, files, tempdir)
  #os.rmdir(tempdir)
  
  return pdf, stdErr

