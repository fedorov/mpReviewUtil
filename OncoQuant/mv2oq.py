import SimpleITK as sitk
import sys

mv = sitk.ReadImage(sys.argv[1])
print 'Multivolume:',mv.GetSize()

oq = sitk.JoinSeries([sitk.VectorIndexSelectionCast(mv,i) for i in range(mv.GetNumberOfComponentsPerPixel())])

sitk.WriteImage(oq, sys.argv[2], True)

print 'OncoQuant:',oq.GetSize()
