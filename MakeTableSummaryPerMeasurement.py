import shutil, string, os, sys, glob, xml.dom.minidom, json
import SimpleITK as sitk
import dicom

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


def getDICOMMeta(dir,metaKeys):
  meta = []
  dcmDir = os.path.split(dir)[0]+'/DICOM'
  dcmFiles = glob.glob(dcmDir+'/*dcm')
  try:
    dcm = dicom.read_file(dcmFiles[0])
  except:
    print 'Failed to read DICOM from',dcmDir
  for k in metaKeys:
    meta.append(getattr(dcm,k))
  return meta

def getCanonicalName(dir):
  series = dir.split('/')[-2]
  canonicalDir = os.path.split(dir)[0]+'/Canonical'
  jc = json.loads(open(canonicalDir+'/'+series+'.json','r').read())
  return jc['CanonicalType']

# generate one line per each measurement, with various columns

metaKeys = ['PatientName','StudyDate','ManufacturerModelName','SeriesNumber']


for dir,subdirs,files in os.walk(sys.argv[1]):
  if os.path.split(dir)[1] == 'Measurements':
    seriesNumber = dir.split('/')[-2]
    dcmMetaItems = getDICOMMeta(dir,metaKeys)
    canonicalType = getCanonicalName(dir)

    for f in files:
      mmsFile = os.path.join(dir,f)
      expectedSeriesNumber = f.split('-')[0]
      if expectedSeriesNumber != seriesNumber:
        # this is a PK map
        nameSplit = f.split('-')
        canonicalType = nameSplit[3]+'.'+nameSplit[1]

      mms = json.loads(open(mmsFile,'rb').read())
      try:
        items = mms['SegmentationName'].split('.')[0].split('-')
      except:
        continue
      reader = items[0]
      structure = items[1]
      readDate = items[2]

      for k,v in mms.iteritems():
        if k == 'SegmentationName':
          continue
        for m in dcmMetaItems:
          print m,';',

        print k,';',v,';',reader,';',structure,';',readDate,';',canonicalType,';',
        print
