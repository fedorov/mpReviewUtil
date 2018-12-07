import shutil, string, os, sys, glob, xml.dom.minidom, json

import mpReviewUtil

import SimpleITK as sitk

RSQR_MIN = 0.0


def threshold(image,low,high):
  thresh = sitk.BinaryThresholdImageFilter()
  thresh.SetLowerThreshold(low)
  thresh.SetUpperThreshold(high)
  thresh.SetInsideValue(1)
  thresh.SetOutsideValue(0)
  return sitk.Cast(thresh.Execute(image),sitk.sitkInt16)

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
pkdata = sys.argv[2]

settingsFile= sys.argv[3]

settingsData = open(settingsFile).read()
settings = json.loads(settingsData)

def threshold(image,low,high):
  thresh = sitk.BinaryThresholdImageFilter()
  thresh.SetLowerThreshold(low)
  thresh.SetUpperThreshold(high)
  thresh.SetInsideValue(1)
  thresh.SetOutsideValue(0)
  return thresh.Execute(image)

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
      continue

    # check if the series type is of interest
    if not seriesAttributes['CanonicalType'] in settings['SeriesTypes']:
      continue

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

      # check if segmentation is available for this series
      segmentationsPath = os.path.join(studyDir,s,'Segmentations')

      for reader in settings['Readers']:
        segFiles = glob.glob(segmentationsPath+'/'+reader+'-'+structure+'*')

        if not len(segFiles):
          continue
        segFiles.sort()

        canonicalType = getCanonicalType(data,c,s)

        if canonicalType != 'SUB':
          continue

        # consider only the most recent seg file for the given reader
        segmentationFile = segFiles[-1]

        oqseries = glob.glob(pkdata+'/'+c+'/RESOURCES/*')[0].split('/')[3]
        maps = glob.glob(pkdata+'/'+c+'/RESOURCES/'+oqseries+'/OncoQuant/*nrrd')

        map2mask = {}
        map2validVoxels = {}
        #print segmentationFile
        segImage = sitk.ReadImage(str(segmentationFile)) > 0
        segStats = sitk.LabelStatisticsImageFilter()
        segStats.Execute(segImage,segImage)
        segCnt = segStats.GetCount(1)

        for m in maps:
          if m.find('Ve')<0 and m.find('Ktrans')<0:
            map2mask[m] = segmentationFile
            map2validVoxels[m] = 1
            continue
          if m.find('Ve')>0:
            veImage = sitk.ReadImage(m)
            rsqrMap = m.replace('Ve','PkRsqr')
            rsqrImage = sitk.ReadImage(rsqrMap)
            rsqrImage.SetSpacing(veImage.GetSpacing())
            segImage.SetSpacing(veImage.GetSpacing())
            rsqrImage.SetDirection(veImage.GetDirection())
            segImage.SetDirection(veImage.GetDirection())

            veThreshImage = threshold(veImage,0.001,1) & threshold(rsqrImage,RSQR_MIN,100) & threshold(segImage,1,100)
            veThreshImage = threshold(veImage,0.001,1) & threshold(segImage,1,100)
            segStats.Execute(veThreshImage,veThreshImage)
            veCnt = segStats.GetCount(1)
            if segCnt != 0:
              map2validVoxels[m] = float(veCnt)/float(segCnt)
            else:
              map2validVoxels[m] = 'NA'
            '''
            if veCnt != segCnt:
              print 've mismatch!'
              print veCnt,segCnt
              sys.exit()
            '''
            veThreshFileName = segmentationFile[:-5]+'-'+os.path.split(m)[1][:-5]+'.nrrd'
            #print 'Would save PK mask to',veThreshFileName
            sitk.WriteImage(veThreshImage,str(veThreshFileName))
            map2mask[m] = veThreshFileName
          if m.find('Ktrans')>0:
            ktransImage = sitk.ReadImage(m)
            rsqrMap = m.replace('Ktrans','PkRsqr')
            rsqrImage = sitk.ReadImage(rsqrMap)
            rsqrImage.SetSpacing(ktransImage.GetSpacing())
            segImage.SetSpacing(ktransImage.GetSpacing())
            rsqrImage.SetDirection(ktransImage.GetDirection())
            segImage.SetDirection(ktransImage.GetDirection())

            ktransThreshImage = threshold(ktransImage,0.001,5) & threshold(rsqrImage,RSQR_MIN,100) & threshold(segImage,1,100)
            ktransThreshImage = threshold(ktransImage,0.001,5) & threshold(segImage,1,100)
            segStats.Execute(ktransThreshImage,ktransThreshImage)
            ktransCnt = segStats.GetCount(1)
            if segCnt != 0:
              map2validVoxels[m] = float(ktransCnt)/float(segCnt)
            else:
              map2validVoxels[m] = 'NA'
            '''
            if ktransCnt != segCnt:
              print 'Ktrans mismatch!'
              print ktransCnt,segCnt
              sys.exit()
            '''
            ktransThreshFileName = segmentationFile[:-5]+'-'+os.path.split(m)[1][:-5]+'.nrrd'
            #print 'Would save PK mask to',ktransThreshFileName
            sitk.WriteImage(ktransThreshImage,str(ktransThreshFileName))
            map2mask[m] = ktransThreshFileName

        #print maps
        measurements = {}
        measurementsDir = os.path.join(studyDir,s,'Measurements')
        measurementsFile = os.path.join(measurementsDir,s+'-'+structure+'-'+reader+'.json')
        if os.path.exists(measurementsFile):
          # will need to append to the file
          measurements = json.loads(open(measurementsFile,'r').read())

        for m in maps:
          if m.endswith('.nrrd'):
            imageFile = m
            measurements = mpReviewUtil.computeMeasurements(imageFile,map2mask[imageFile],settings['MeasurementTypes'])
            measurements['ValidVoxelsPercentage'] = map2validVoxels[m]
            pkMasksDir = os.path.split(map2mask[imageFile])[0]+'/PKmasks'
            if len(os.path.split(map2mask[imageFile])[1].split('-'))>3:
              #print map2mask[imageFile]
              #print pkMasksDir
              try:
                os.mkdir(pkMasksDir)
              except:
                pass
              try:
                shutil.move(map2mask[imageFile],pkMasksDir)
              except:
                os.remove(pkMasksDir+'/'+os.path.split(map2mask[imageFile])[1])
                shutil.move(map2mask[imageFile],pkMasksDir)

            patientID = c.split('_')[0]
            date = c.split('_')[1]

            mAttrs = m.split('/')[-1].split('-')
            reportRow = [patientID,date,mAttrs[1],mAttrs[3].split('.')[0],structure]
            rowBase = ';'.join(reportRow)
            for mk,mv, in measurements.iteritems():
              if mk != 'SegmentationName':
                print rowBase+';'+str(mk)+';'+str(mv)

            '''
            try:
              os.mkdir(measurementsDir)
            except:
              pass
            '''


            # get rid of .nrrd
            measurementsFile = os.path.split(imageFile)[1][:-5]
            measurementsFile = measurementsFile+'-'+structure+'-'+reader+'.json'

            measurementsPath = os.path.join(measurementsDir,measurementsFile)
            #print 'Saving'
            #print measurements
            #print 'to',measurementsPath

            f = open(measurementsPath,'w')
            f.write(json.dumps(measurements))
            f.close()


          #mm.recordMeasurement(study=c,series=s,struct=structure,reader=reader,mtype=mtype,mvalue=mvalue)
          #mvalue = mvalue+1

        #print str(measurements)

print 'WARNING: ADD RESAMPLING OF THE LABEL TO IMAGE!!!'
