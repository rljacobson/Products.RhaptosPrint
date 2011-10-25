# python -c "import collectiondbk2pdf; print collectiondbk2pdf.__doStuff('./tests');" > result.pdf

import sys
import os
import Image
from StringIO import StringIO
from tempfile import mkdtemp
import subprocess

from lxml import etree
import urllib2

import collection2dbk
import util

FOP_PATH = os.path.join(os.getcwd(), 'fop', 'fop')
XCONF_PATH = os.path.join(os.getcwd(), 'lib', 'fop.xconf')
PRINT_STYLE='modern-textbook'

# XSL files
DOCBOOK2FO_XSL=util.makeXsl('%s.xsl' % PRINT_STYLE)
DOCBOOK_CLEANUP_XSL = util.makeXsl('dbk-clean-whole.xsl')
ALIGN_XSL = util.makeXsl('fo-align-math.xsl')
#MARGINALIA_XSL = util.makeXsl('fo-marginalia.xsl')

#XINCLUDE_XPATH = etree.XPath('//xi:include', namespaces=util.NAMESPACES)

def __doStuff(dir):
  collxml = etree.parse(os.path.join(dir, 'collection.xml'))
  
  MODULES_XPATH = etree.XPath('//col:module/@document', namespaces=util.NAMESPACES)
  IMAGES_XPATH = etree.XPath('//c:*/@src[not(starts-with(.,"http:"))]', namespaces=util.NAMESPACES)
  moduleIds = MODULES_XPATH(collxml)
  
  modules = {}
  allFiles = {}
  for module in moduleIds:
    #print >> sys.stderr, "LOG: Starting on %s" % (module)
    moduleDir = os.path.join(dir, module)
    if os.path.isdir(moduleDir):
      cnxmlStr = open(os.path.join(moduleDir, 'index.cnxml')).read()
      cnxml = etree.parse(StringIO(cnxmlStr))
      files = {}
      for f in IMAGES_XPATH(cnxml):
          try:
            data = open(os.path.join(moduleDir, f)).read()
            files[f] = data
            allFiles[os.path.join(module, f)] = data
            #print >> sys.stderr, "LOG: Image ADDED! %s %s" % (module, f)
          except IOError:
            print >> sys.stderr, "LOG: Image not found %s %s" % (module, f)
      modules[module] = (cnxml, files)

  dbk, newFiles = collection2dbk.convert(collxml, modules)
  allFiles.update(newFiles)
  pdf, stdErr = convert(dbk, allFiles)
  return pdf

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
    
  # Run FOP to generate an abstract tree 1st
  # strCmd = [FOP_PATH, '-c', XCONF_PATH, '/dev/stdin']
  strCmd = [FOP_PATH, '-c', XCONF_PATH, '-at', 'application/pdf', '/dev/stdout', '/dev/stdin']

  # run the program with subprocess and pipe the input and output to variables
  p = subprocess.Popen(strCmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
  # set STDIN and STDOUT and wait untill the program finishes
  stdOut, stdErr = p.communicate(etree.tostring(fo))
  abstractTree = stdOut

  strCmd = [FOP_PATH, '-c', XCONF_PATH, '-atin', '/dev/stdin', '/dev/stdout']

  # run the program with subprocess and pipe the input and output to variables
  p = subprocess.Popen(strCmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
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

def convert(dbk1, files):
  tempdir = mkdtemp(suffix='-fo2pdf')

  def transform(xslDoc, xmlDoc):
    """ Performs an XSLT transform and parses the <xsl:message /> text """
    ret = xslDoc(xmlDoc, **({'cnx.output.fop': '1', 'cnx.tempdir.path':"'%s'" % tempdir}))
    for entry in xslDoc.error_log:
      # TODO: Log the errors (and convert JSON to python) instead of just printing
      print >> sys.stderr, entry
    return ret

  # Step 0 (Sprinkle in some index hints whenever terms are used)
  # termsprinkler.py $DOCBOOK > $DOCBOOK2

  # Step 1 (Cleaning up Docbook)
  dbk2 = transform(DOCBOOK_CLEANUP_XSL, dbk1)

  # Step 2 (Docbook to XSL:FO)
  fo1 = transform(DOCBOOK2FO_XSL, dbk2)

  # Step 3 (Aligning math in XSL:FO)
  fo = transform(ALIGN_XSL, fo1)

  #import pdb; pdb.set_trace()
  # Step 4 Converting XSL:FO to PDF (using Apache FOP)
  # Change to the collection dir so the relative paths to images work
  pdf, stdErr = fo2pdf(fo, files, tempdir)
  #os.rmdir(tempdir)
  
  return pdf, stdErr