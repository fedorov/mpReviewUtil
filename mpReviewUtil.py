import SimpleITK as sitk

def computeMeasurements(imageFile,segmentationFile,measurementTypes,resampleLabel=False):
  label = sitk.ReadImage(str(segmentationFile))
  image = sitk.ReadImage(imageFile)

  if resampleLabel:
    resample = sitk.ResampleImageFilter()
    resample.SetReferenceImage(image)
    resample.SetInterpolator(sitk.sitkNearestNeighbor)
    label = resample.Execute(label)

  image.SetDirection(label.GetDirection())
  image.SetSpacing(label.GetSpacing())
  image.SetOrigin(label.GetOrigin())

  if image.GetSize()[2] != label.GetSize()[2]:
    print 'ERROR: Image/label sizes do not match!'
    abort()

  stats = sitk.LabelStatisticsImageFilter()
  stats.Execute(label,label)
  totalLabels = stats.GetNumberOfLabels()
  if totalLabels<2:
    print segmentationFile
    print "ERROR: Segmentation should have exactly 2 labels!"
    return {}

  # threshold to label 1
  thresh = sitk.BinaryThresholdImageFilter()
  thresh.SetLowerThreshold(1)
  thresh.SetUpperThreshold(100)
  thresh.SetInsideValue(1)
  thresh.SetOutsideValue(0)
  label = thresh.Execute(label)

  stats.Execute(image,label)

  measurements = {}
  measurements['SegmentationName'] = segmentationFile.split('/')[-1]

  for mtype in measurementTypes:

    if mtype == "Mean":
      measurements["Mean"] = stats.GetMean(1)
    if mtype == "Median":
      measurements["Median"] = stats.GetMedian(1)
    if mtype == "StandardDeviation":
      measurements["StandardDeviation"] = stats.GetSigma(1)
    if mtype == "Minimum":
      measurements["Minimum"] = stats.GetMinimum(1)
    if mtype == "Maximum":
      measurements["Maximum"] = stats.GetMaximum(1)
    if mtype == "Volume":
      spacing = label.GetSpacing()
      measurements["Volume"] = stats.GetCount(1)*spacing[0]*spacing[1]*spacing[2]
    if mtype == "Count":
      measurements["Count"] = stats.GetCount(1)
    if mtype.startswith("Percentile"):
      npImage = sitk.GetArrayFromImage(image)
      npLabel = sitk.GetArrayFromImage(label)
      pixels = npImage[npLabel==1]
      pixels.sort()
      percent = float(mtype[10:])/100.
      measurements[mtype] = float(pixels[len(pixels)*percent])
    if mtype == "PixelValues":
      import numpy
      npImage = sitk.GetArrayFromImage(image)
      npLabel = sitk.GetArrayFromImage(label)
      nz = numpy.where(npLabel!=0)
      result = ""
      for p in range(nz[0].size):
        result = result+'('+ str(nz[0][p])+','+str(nz[1][p])+','+str(nz[2][p])+'):'+str(npImage[nz[0][p],nz[1][p],nz[2][p]])+','
      measurements[mtype] = result
  return measurements
