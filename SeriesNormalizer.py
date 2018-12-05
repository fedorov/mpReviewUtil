import shutil, string, os, sys, glob, xml.dom.minidom, pydicom

# Iterate over all series in the directory that follows PCampReview convention,
# use rules defined in getCanonicalType() to 'tag' series according to the
# types of typical interest.
#
# Input argument: directory with the data

data = sys.argv[1]

def getDWIbValue(studyDir,seriesStr):
  #print studyDir,seriesStr
  if int(seriesStr)>100:
    dwiFiles = glob.glob(studyDir+'/'+str(int(seriesStr)/100)+'/DICOM/*dcm')
  else:
    dwiFiles = glob.glob(studyDir+'/'+seriesStr+'/DICOM/*dcm')
  bVals = set()
  for d in dwiFiles:
    try:
      dcm = pydicom.read_file(d)
    except:
      continue
    try:
      if dcm.Manufacturer == "SIEMENS":
        bValue = int(dcm[0x0019,0x100c].value)
      else:
        sl = dcm[0x0043,0x1039]
        value = dcm[0x0043,0x1039].value.decode('ascii')
        vr = dcm[0x0043,0x1039].VR
        if vr == 'UN':
          bValue = int(value.split('\\')[0])
        else:
          bValue = sl[0]
    except Exception as e:
      print("ERROR processing "+d)
      print(e)
    if int(bValue)>100000:
      bValue = bValue % 100000
    bVals.add(bValue)
  bVals = [i for i in bVals]
  bVals.sort(reverse=True)
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
  elif desc.startswith('Apparent Diffusion Coefficient') or desc.endswith('ADC'):
    # TODO: parse platform-specific b-values etc
    return 'ADC'
  elif re.search('Ax Dynamic',desc) or re.search('3D DCE',desc):
    return 'DCE'
  elif re.search("DWI",desc):
    return 'DWI'
  else:
    return "Unknown"

seriesDescription2Count = {}
seriesDescription2Type = {}

studies = getValidDirs(data)

totalSeries = 0
totalStudies = 0

for c in studies:
  print(c)

  studyDir = os.path.join(data,c,'RESOURCES')

  try:
    series = os.listdir(studyDir)
  except:
    continue

  totalStudies = totalStudies+1
  seriesPerStudy = 0

  # process in numeric order, so that we parse DWI before ADC, and take b-value
  # from there
  seriesNumeric = [int(s) for s in series if str.isdigit(s)]
  seriesNumeric.sort()
  series = [str(s) for s in seriesNumeric]

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
    attrs = {}

    dicomFiles = glob.glob(os.path.join(studyDir,s,'DICOM')+'/*dcm')

    try:
      dcm = pydicom.read_file(dicomFiles[0])
    except:
      print('Failed to read'+dicomFiles[0])
      continue

    model = dcm.ManufacturerModelName
    manufacturer = dcm.Manufacturer

    if seriesType == "DWI":
      # get all b-values used
      bvals = getDWIbValue(studyDir,s)
      attrs['b-values'] = bvals
    if seriesType == "ADC": # try to figure out the b-values
      bValues = getDWIbValue(studyDir, s)
      if len(bValues) == 0:
        # try to get them from the DWI series
        dwiSeries = str(int(int(s) / 100))
        dwiCanonicalPath = os.path.join(studyDir,dwiSeries,'Canonical',dwiSeries+".json")
        with open(dwiCanonicalPath,'r') as dwiFile:
          dwiJson = json.load(dwiFile)
          bValues = dwiJson["b-values"]

      attrs["b-values"] = bValues
      seriesType = seriesType+str(dwiJson["b-values"][0])

    seriesDescription2Type[desc] = seriesType
    attrs['CanonicalType'] = seriesType
    attrs['Manufacturer'] = manufacturer
    attrs['ManufacturerModelName'] = model
    if seriesType != "Unknown":
      print("    "+s+" is "+seriesType)
    f.write(json.dumps(attrs))
    f.close

  #print 'Total series for study ',c,':',seriesPerStudy

#print "Total series: ",totalSeries,' map size: ',len(seriesDescription2Count)
#for k in seriesDescription2Count.keys():
#  print k,seriesDescription2Count[k]

#for k in seriesDescription2Type.keys():
#  if seriesDescription2Type[k].startswith('ADC'):
#    print k,' ==> ',seriesDescription2Type[k]
