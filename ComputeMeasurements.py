import shutil, string, os, sys, glob, xml.dom.minidom, json

import mpReviewUtil

# Given the location of data and a JSON configuration file that has the following
# structure:
#
# Studies: <list>
# SeriesTypes: <list of canonical names>
# Structures: <list of canonical structure types>
# MeasurementTypes: <list of canonical names for the series>
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

def getCanonicalType(rootDir,study,series):
  canonicalPath = os.path.join(rootDir,study,'RESOURCES',series,'Canonical')
  canonicalFile = os.path.join(canonicalPath,s+'.json')
  print(canonicalFile)
  try:
    seriesAttributes = json.loads(open(canonicalFile,'r').read())
    return seriesAttributes['CanonicalType']
  except:
    return None

seriesDescription2Count = {}
seriesDescription2Type = {}

studies = getValidDirs(data)

totalSeries = 0
totalStudies = 0

mvalue = 0

# resample label to the image reference
# should probably be done once during preprocessing
resampleLabel = False

for c in studies:

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

  totalStudies = totalStudies+1
  seriesPerStudy = 0

  for s in series:
    if s.startswith('.'):
      # handle '.DS_store'
      continue

    canonicalPath = os.path.join(studyDir,s,'Canonical')
    canonicalFile = os.path.join(canonicalPath,s+'.json')
    try:
      seriesAttributes = json.loads(open(canonicalFile,'r').read())
    except:
      print("Failed to load canonical json")
      continue

    # check if the series type is of interest
    if not seriesAttributes['CanonicalType'] in settings['SeriesTypes']:
      continue

    print("Processing "+seriesAttributes['CanonicalType'])
    # if no structures specified in the config file, consider all
    allStructures = None
    try:
      allStructures = settings['Structures']
    except:
      allStructures = ['WholeGland','PeripheralZone',
          'TumorROI_PZ_1',
          'TumorROI_CGTZ_1',
          'TumorROI_PZ_2',
          'TumorROI_CGTZ_2',
          'BPHROI_1',
          'NormalROI_PZ_1',
          'NormalROI_CGTZ_1']

    for structure in allStructures:
      print("Processing "+structure)
      # check if segmentation is available for this series
      segmentationsPath = os.path.join(studyDir,s,'Segmentations')

      for reader in settings['Readers']:
        globPattern = segmentationsPath+'/'+reader+'-'+structure+'*'
        segFiles = glob.glob(globPattern)

        if not len(segFiles):
          print("ERROR: Failed to find segmentations that match "+globPattern)
          continue
        segFiles.sort()

        canonicalType = getCanonicalType(data,c,s)
        print('Canonical type:'+seriesAttributes['CanonicalType'])

        # consider only the most recent seg file for the given reader
        segmentationFile = segFiles[-1]

        imageFile = os.path.join(studyDir,s,'Reconstructions',s+'.nrrd')

        measurements = mpReviewUtil.computeMeasurements(imageFile,segmentationFile,settings['MeasurementTypes'])

        measurementsDir = os.path.join(studyDir,s,'Measurements')
        try:
          os.mkdir(measurementsDir)
        except:
          pass
          '''
          import shutil
          oldDir = os.path.join(studyDir,s,'Measurements-old')
          if not os.path.exists(oldDir):
            shutil.move(measurementsDir, oldDir)
            os.mkdir(measurementsDir)
          '''
        measurementsFile = os.path.join(measurementsDir,s+'-'+structure+'-'+reader+'.json')
        f = open(measurementsFile,'w')
        print(str(measurements))
        f.write(json.dumps(measurements))
        f.close()


          #mm.recordMeasurement(study=c,series=s,struct=structure,reader=reader,mtype=mtype,mvalue=mvalue)
          #mvalue = mvalue+1

        #print str(measurements)

print('WARNING: ADD RESAMPLING OF THE LABEL TO IMAGE!!!')
