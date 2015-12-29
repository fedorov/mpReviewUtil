import shutil, string, os, sys, glob, xml.dom.minidom, dicom

# Iterate over all series in the directory that follows PCampReview convention,
# use rules defined in getCanonicalType() to 'tag' series according to the
# types of typical interest.
#
# Input argument: directory with the data

data = sys.argv[1]

def getDWIbValue(studyDir,seriesStr):
  print studyDir,seriesStr
  dwiFiles = glob.glob(studyDir+'/'+str(int(seriesStr)/100)+'/DICOM/*dcm')
  bVals = set()
  for d in dwiFiles:
    dcm = dicom.read_file(d)
    try:
      sl = dcm[0x0043,0x1039]
    except:
      print 'No clue what to do'
    bValue = sl.value[0]
    if bValue>100000:
      bValue = bValue % 100000

    bVals.add(bValue)
  bVals = [i for i in bVals]
  bVals.sort(reverse=True)
  print bVals
  return bVals

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
    return "SUB"
  elif (re.search('AX ',desc) and re.search('T2 ',desc)) or (desc == 'AX FRFSE-XL T2'):
    return "T2AX"
  elif desc.startswith('Apparent Diffusion Coefficient'):
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

for c in studies:
  studyDir = os.path.join(data,c,'RESOURCES')

  try:
    series = os.listdir(studyDir)
  except:
    continue

  totalStudies = totalStudies+1
  seriesPerStudy = 0

  for s in series:
    canonicalPath = os.path.join(studyDir,s,'Canonical')
    try:
      os.mkdir(canonicalPath)
    except:
      pass

    xmlFileName = os.path.join(studyDir,s,'Reconstructions',s+'.xml')

    try:
      dom = xml.dom.minidom.parse(xmlFileName)
    except:
      continue

    desc = getElementValue(dom, 'SeriesDescription')
    seriesType = getCanonicalType(dom)
    totalSeries = totalSeries+1
    seriesPerStudy = seriesPerStudy+1

    try:
      seriesDescription2Count[desc]=seriesDescriptionMap[desc]+1
    except:
      seriesDescription2Count[desc]=1


    f = open(os.path.join(canonicalPath,s+'.json'),'w')

    manufacturer = ''
    model = ''
    import json
    if seriesType == "ADC": # try to figure out the b-values
      print desc
      dicomFiles = glob.glob(os.path.join(studyDir,s,'DICOM')+'/*dcm')
      try:
        dcm = dicom.read_file(dicomFiles[0])
      except:
        print 'Failed to read',studyDir+'/'+s+'/DICOM'
      model = dcm.ManufacturerModelName
      manufacturer = dcm.Manufacturer
      try:
        sl = dcm[0x0043,0x1039]
        if sl.VR == 'UN':
          bValue = sl.value.split('\\')[0]
        else:
          bValue = sl[0]
      except:
        sl = getDWIbValue(studyDir,s)
        bValue = sl[0]
      seriesType = seriesType+str(bValue)
      #print seriesType

    seriesDescription2Type[desc] = seriesType
    attrs = {'CanonicalType':seriesType,'Manufacturer':manufacturer,
        'ManufacturerModelName':model}
    f.write(json.dumps(attrs))
    f.close

  #print 'Total series for study ',c,':',seriesPerStudy

#print "Total series: ",totalSeries,' map size: ',len(seriesDescription2Count)
#print seriesDescription2Count

for k in seriesDescription2Type.keys():
  if seriesDescription2Type[k].startswith('ADC'):
    print k,' ==> ',seriesDescription2Type[k]
