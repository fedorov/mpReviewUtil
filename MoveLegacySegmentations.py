import shutil, string, os, sys, glob, xml.dom.minidom, json

# Given the location of data, find all segmentation files that have the name
# like <reader>-<datetime>.nrrd, and move them under Legacy folder.
#

data = sys.argv[1]

def getValidDirs(dir):
  #dirs = [f for f in os.listdir(dir) if (not f.startswith('.')) and (not os.path.isfile(f))]
  dirs = os.listdir(dir)
  dirs = [f for f in dirs if os.path.isdir(dir+'/'+f)]
  dirs = [f for f in dirs if not f.startswith('.')]
  return dirs

studies = getValidDirs(data)

allDirs = glob.glob(data+'/*')

for dpath, dnames, fnames in os.walk(data):
  if not dpath.endswith('Segmentations'):
    continue
  globPath = os.path.join(dpath,'fionafennessy-[0-9][0-9]*.nrrd')
  print globPath
  legacyDir = os.path.join(dpath,'Legacy')
  legacySegs = glob.glob(globPath)
  try:
    os.mkdir(legacyDir)
  except:
    pass
  for s in legacySegs:
    shutil.move(s,legacyDir)

  # rename .nrrd.nrrd segmentations
  dupnrrdFiles = glob.glob(dpath+'/*nrrd.nrrd')
  for f in dupnrrdFiles:
    newName = f[:-5]
    shutil.move(f,newName)
