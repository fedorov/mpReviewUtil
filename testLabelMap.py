import SimpleITK as sitk


segmentationFile = '/Users/fedorov/ImageData/QIN/Repeatability/Repeat_studies/10/RESOURCES/701/Segmentations/fionafennessy-BPHROI_1-20150402222621.nrrd'
label = sitk.ReadImage(str(segmentationFile))
#f = sitk.LabelImageToLabelMapFilter()
f = sitk.LabelStatisticsImageFilter()
f.Execute(label,label)

print f.GetLabels()
