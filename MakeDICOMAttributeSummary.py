import shutil, string, os, sys, glob, xml.dom.minidom, json
from sets import Set

# Given the location of data and a JSON configuration file that has the following
# structure:
#
# Studies: <list>
# SeriesTypes: <list of canonical names>
# Structures: <list of canonical structure types>
# DICOMTags: <list of DICOM tags to analyze>
# Readers: <list of reader IDs>
#
# find series that match the list (study and series type), compute all
# measurement types, and save them at the Measurements level.

data = sys.argv[1]

settingsFile= sys.argv[2]

settingsData = open(settingsFile).read()
settings = json.loads(settingsData)

def getElementValue(dom,name):
  elements = dom.getElementsByTagName('element')
  for e in elements:
    if e.getAttribute('name') == name:
      return e.childNodes[0].nodeValue

  return None

def checkTagExistence(dom,tag):
  elements = dom.getElementsByTagName('element')
  for e in elements:
    if e.getAttribute('tag') == tag:
      return True

  return False
 
def getValidDirs(dir):
  #dirs = [f for f in os.listdir(dir) if (not f.startswith('.')) and (not os.path.isfile(f))]
  dirs = os.listdir(dir)
  dirs = [f for f in dirs if os.path.isdir(dir+'/'+f)]
  dirs = [f for f in dirs if not f.startswith('.')]
  return dirs

def getCanonicalType(dom):
  import re
  desc = getElementValue(dom,'SeriesDescription')
  if re.search('[a-zA-Z]',desc) == None:
    return "sutract"
  elif re.search('AX',desc) and re.search('T2',desc):
    return "Axial T2"
  elif re.search('Apparent Diffusion',desc):
    # TODO: parse platform-specific b-values etc
    return 'ADC'
  elif re.search('Ax Dynamic',desc) or re.search('3D DCE',desc):
    return 'DCE'
  else:
    return "Unknown"

seriesDescription2Count = {}
seriesDescription2Type = {}

studies = getValidDirs(data)

totalSeries = 0
totalStudies = 0

mvalue = 0

# populate header during first pass
header = []
# keep adding table rows, each row is one pass over the outer loop
table = []

header = ["StudyID"]
headerInitialized = False

attributeValues = {}

for c in studies:
  print c

  try:
    if not c in settings['Studies']:
      continue
  except:
    # if Studies is not initialized, assume need to process all
    pass

  studyDir = os.path.join(data,c,'RESOURCES')

  try:
    series = os.listdir(studyDir)
  except:
    continue

  tableRow = [c]

  totalStudies = totalStudies+1
  seriesPerStudy = 0

  for stype in settings['SeriesTypes']:
    stypeFound = False
    
    for s in series:
      if stypeFound:
        break

      if s.startswith('.'):
        # handle '.DS_store'
        continue

      canonicalPath = os.path.join(studyDir,s,'Canonical')
      canonicalFile = os.path.join(canonicalPath,s+'.json')
      seriesAttributes = json.loads(open(canonicalFile,'r').read())

      # check if the series type is of interest
      if stype != seriesAttributes['CanonicalType']:
        continue

      segmentationsPath = os.path.join(studyDir,s,'Segmentations')
      try:
        # no segmentations for this series
        if len(os.listdir(segmentationsPath))==0:
          continue
      except:
        # no Segmentations directory
        continue

      stypeFound = True

      tags = None
      try:
        tags = settings['DICOMTags']
      except:
        sys.exit()

      for tag in tags:
        # check if segmentation is available for this series

        xmlFileName = os.path.join(studyDir, s,'Reconstructions',s+'.xml')
        try:
          dom = xml.dom.minidom.parse(xmlFileName)
        except:
          sys.exit()

        attr = getElementValue(dom, tag)
        print "\t",attr
        key = stype+'-'+tag
        try:
          attributeValues[key].add(attr)
        except:
          attributeValues[key] = Set([attr])

print attributeValues
