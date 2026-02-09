#!/usr/bin/env python3
#  xslt_run.py  –  one‑liner that works with any XSLT 1.0 stylesheet
#  usage:  python xslt_run.py source.xml stylesheet.xsl  >  result.xml
#  (or redirect the output to a file)

import sys, lxml.etree as ET

# 1️⃣  parse the two input files
xml_doc   = ET.parse(sys.argv[1])          # source XML
xslt_doc  = ET.parse(sys.argv[2])          # XSLT stylesheet

# 2️⃣  compile the stylesheet and apply it
result = ET.XSLT(xslt_doc)(xml_doc)        # → _XSLTResultTree

# 3️⃣  print the transformation result
#    * `str(result)` returns the serialized output (text or XML)
#    * no `.decode()` is needed – the object already gives a Python string
print(str(result))