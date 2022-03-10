from enum import Enum
from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node, Workflow, Function, MapNode
import nipype.interfaces.io as nio
import nipype.interfaces.fsl as fsl
from nipype.algorithms.confounds import TSNR
import pandas as pd
import json
import os
import glob

class GeomType(Enum):
    UNKNOWN = 0
    CYLINDER = 1
    SPHERE = 2

class Geometry:
    '''Phantom Geometry'''
    def __init__(self,geom,height=0,length=0,width=0,depth=0,diameter=0,radius=0):
        self.geomtype = geom
        self.height=height
        self.width=width
        self.depth=depth
        self.diameter=diameter
        self.radius=radius
        self.length=length
        # Consistency checks
        if self.geomtype == GeomType.CYLINDER:
            if self.diameter > 0:
                self.radius = diameter/2
                self.width = diameter
                self.depth = diameter
            elif self.radius > 0:
                self.diameter = radius * 2
                self.width = diameter
                self.depth = diameter
            elif self.width > 0:
                self.diameter = width
                self.radius = diameter/2
                self.depth = diameter   
            elif self.depth > 0:
                self.diameter = depth
                self.radius = diameter/2
                self.width = diameter
                
            if self.height > 0:
                self.length=height
            elif self.length > 0:
                self.height=length

class Phantom:
    '''Phantom class'''
    def __init__(self,myID='Phantom',Geom=Geometry(GeomType.UNKNOWN)):
        self.PhID=myID
        self.PhGeom = Geom

class ACR(Phantom):
    '''ACR Phantom class'''
    def __init__(self,myID='ACR Phantom',Geom=Geometry(GeomType.CYLINDER)):
        super().__init__(myID,Geom)

class ACRMedium(ACR):
    '''ACR Medium Phantom class'''
    def __init__(self,myID='ACR Medium Phantom'):
        Geom=Geometry(GeomType.CYLINDER, diameter=165,height=134)
        super().__init__(myID,Geom)

#

def save_image_to_disk(in_file,newimgdata,output_file):
    from nilearn.image import new_img_like
    import nibabel
    
    img = nibabel.load(in_file)
    img_dtype = img.header.get_data_dtype()

    data_to_save=newimgdata.astype(img_dtype)

    new_img=new_img_like(img, data_to_save,copy_header=True)
    nibabel.nifti1.save(new_img, output_file)  


def calc_snr_proc(in_file,in_signal_roifile,in_noise_roifile,in_roidir=""):
    import nibabel
    import numpy as np
    import os
    from nipype.interfaces.base import Undefined
    import json
    from pathlib import Path

    img = nibabel.load(in_file)
    data=img.get_fdata()
    img_dtype = img.header.get_data_dtype()
    
    basefile=os.path.basename(in_file).split('.')[0]
    dims = nibabel.load(in_file).shape

    # if signal path doesn't exist then tack on to in_file location
    if not Path(in_signal_roifile).exists():
        in_signal_roifile=os.path.join(in_roidir,in_signal_roifile)
    # if noise path doesn't exist then tack on to in_file location
    if not Path(in_noise_roifile).exists():
        in_noise_roifile=os.path.join(in_roidir,in_noise_roifile)
    
    signalimg = nibabel.load(in_signal_roifile)
    signaldata_mask = signalimg.get_fdata().astype(np.int16)
    signalmask = signaldata_mask[:,:,:] > 0 

    signal=data.copy().astype(img_dtype)
    # if func then take signal from 1st volume?
    if len(dims) > 3:
        signal=np.squeeze(signal[:,:,:,1])

    signal[~signalmask] = 0
    signal_valuesfile=os.path.join(os.getcwd(),basefile + '_signal_values.nii.gz') 
    save_image_to_disk(in_file,signal,signal_valuesfile)
    mean_signal = np.mean(signal[signalmask])

    noiseimg = nibabel.load(in_noise_roifile)
    noisedata_mask = noiseimg.get_fdata().astype(np.int16)
    noisemask = noisedata_mask[:,:,:] > 0

    noise = data.copy().astype(img_dtype)
    # if func then take signal from 1st volume?
    if len(dims) > 3:
        noise=np.squeeze(noise[:,:,:,0])

    noise[~noisemask] = 0
    noise_valuesfile = os.path.join(os.getcwd(),basefile + '_noise_values.nii.gz')
    save_image_to_disk(in_file,noise,noise_valuesfile)
    stdev = np.std(noise[noisemask]) 
   
    rl_factor = 0.66
    snr = (mean_signal/stdev)
    snr_rcorr = snr*rl_factor
    
    snr_data = {}
    snr_data['in_file'] = in_file
    snr_data['signal_roi'] = in_signal_roifile
    snr_data['noise_roi'] = in_noise_roifile
    snr_data['mean'] = mean_signal
    snr_data['stdev'] = stdev
    snr_data['snr'] = snr
    snr_data['snr_rcorr'] = snr_rcorr
    
    snr_file=os.path.join(os.getcwd(),basefile + '_snr.json')
    with open(snr_file, 'w') as outfile:
            json.dump(snr_data, outfile,indent=2)
            
    #populate file list
    out_file_list=[]
    out_file_list.insert(0,signal_valuesfile)
    out_file_list.insert(1,noise_valuesfile)
    out_file_list.insert(2,snr_file)
    
    return {"signal_valuesfile":signal_valuesfile,"noise_valuesfile":noise_valuesfile,
                "mean_signal":mean_signal,"stdev":stdev,
                "snr":snr,"snr_rcorr":snr_rcorr,"snr_file":snr_file,
             "out_files":out_file_list}    


class CalcSNRInputSpec(BaseInterfaceInputSpec):
    in_file = File( mandatory=True, desc='the input file')
    in_signal_roifile = File(mandatory=True, desc='signal roi')
    in_noise_roifile = File(mandatory=True, desc='noise roi')
    in_roidir = traits.String("", mandatory=False, desc='directory path of rois to allow iterables to be less wordy', usedefault=True)

class CalcSNROutputSpec(TraitedSpec):
    signal_valuesfile=File(desc='the signal values within roi')
    noise_valuesfile = File(desc='the noise values within roi')
    mean_signal = traits.Float(desc='mean signal value')
    stdev = traits.Float(desc='std deviation of noise')
    snr = traits.Float(desc='snr')
    snr_rcorr = traits.Float(desc='rayleigh corrected snr')
    snr_file = File(desc='snr json file')
    out_files = traits.List(desc='list of files')
    
class CalcSNR(BaseInterface):
    input_spec = CalcSNRInputSpec
    output_spec = CalcSNROutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = calc_snr_proc(
            self.inputs.in_file,
            self.inputs.in_signal_roifile,
            self.inputs.in_noise_roifile,
            self.inputs.in_roidir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results



def calc_snr_native_proc(in_file,in_signal_roifile,in_noise_roifile, in_mat, in_roidir=""):
    import nibabel
    import numpy as np
    import os
    import nipype.interfaces.fsl as fsl
    from nipype.interfaces.base import Undefined
    import json
    from pathlib import Path

    img = nibabel.load(in_file)
    data=img.get_fdata()
    img_dtype = img.header.get_data_dtype()
    
    basefile=os.path.basename(in_file).split('.')[0]
    dims = nibabel.load(in_file).shape

    # if signal path doesn't exist then tack on to in_file location
    if not Path(in_signal_roifile).exists():
        in_signal_roifile=os.path.join(in_roidir,in_signal_roifile)
    # if noise path doesn't exist then tack on to in_file location
    if not Path(in_noise_roifile).exists():
        in_noise_roifile=os.path.join(in_roidir,in_noise_roifile)

    basefile_in_mat=os.path.basename(in_mat).split('.')[0]
    out_mat=os.path.join(os.getcwd(),basefile_in_mat + '_inverse.mat')
    # invert the input transform
    invt = fsl.ConvertXFM()
    invt.inputs.in_file = in_mat
    invt.inputs.invert_xfm = True
    invt.inputs.out_file = out_mat
    res1 = invt.run()

    # transform signal and noise rois to native space
    basefile_signal=os.path.basename(in_signal_roifile).split('.')[0]
    in_signal_roifile_native=os.path.join(os.getcwd(),basefile_signal + '_native.nii.gz')
    flt = fsl.FLIRT()
    flt.inputs.apply_xfm = True
    flt.inputs.interp = 'nearestneighbour'
    flt.inputs.in_matrix_file = out_mat
    flt.inputs.in_file=in_signal_roifile
    flt.inputs.reference = in_file
    flt.inputs.out_file = in_signal_roifile_native
    res2 = flt.run()

    # transform signal and noise rois to native space
    basefile_noise=os.path.basename(in_noise_roifile).split('.')[0]
    in_noise_roifile_native=os.path.join(os.getcwd(),basefile_noise + '_native.nii.gz')
    flt = fsl.FLIRT()
    flt.inputs.apply_xfm = True
    flt.inputs.interp = 'nearestneighbour'
    flt.inputs.in_matrix_file = out_mat
    flt.inputs.in_file=in_noise_roifile
    flt.inputs.reference = in_file
    flt.inputs.out_file = in_noise_roifile_native
    res3 = flt.run()

    signalimg = nibabel.load(in_signal_roifile_native)
    signaldata_mask = signalimg.get_fdata().astype(np.int16)
    signalmask = signaldata_mask[:,:,:] > 0 

    signal=data.copy().astype(img_dtype)
    # if func then take signal from 1st volume?
    if len(dims) > 3:
        signal=np.squeeze(signal[:,:,:,1])

    signal[~signalmask] = 0
    signal_valuesfile_native=os.path.join(os.getcwd(),basefile + '_signal_values_native.nii.gz') 
    save_image_to_disk(in_file,signal,signal_valuesfile_native)
    mean_signal = np.mean(signal[signalmask])

    noiseimg = nibabel.load(in_noise_roifile_native)
    noisedata_mask = noiseimg.get_fdata().astype(np.int16)
    noisemask = noisedata_mask[:,:,:] > 0

    noise = data.copy().astype(img_dtype)
    # if func then take signal from 1st volume?
    if len(dims) > 3:
        noise=np.squeeze(noise[:,:,:,0])

    noise[~noisemask] = 0
    noise_valuesfile_native = os.path.join(os.getcwd(),basefile + '_noise_values_native.nii.gz')
    save_image_to_disk(in_file,noise,noise_valuesfile_native)
    stdev = np.std(noise[noisemask]) 
   
    rl_factor = 0.66
    snr = (mean_signal/stdev)
    snr_rcorr = snr*rl_factor
    
    snr_data = {}
    snr_data['in_file_native'] = in_file
    snr_data['signal_valuesfile_native'] = signal_valuesfile_native
    snr_data['noise_valuesfile_native'] = noise_valuesfile_native
    snr_data['in_signal_roifile_native'] = in_signal_roifile_native
    snr_data['in_noise_roifile_native'] = in_noise_roifile_native
    snr_data['out_mat_base2native'] = out_mat
    snr_data['mean_native'] = mean_signal
    snr_data['stdev_native'] = stdev
    snr_data['snr_native'] = snr
    snr_data['snr_rcorr_native'] = snr_rcorr
    
    snr_file=os.path.join(os.getcwd(),basefile + '_snr_native.json')
    with open(snr_file, 'w') as outfile:
            json.dump(snr_data, outfile,indent=2)
            
    #populate file list
    out_file_list=[]
    out_file_list.insert(0,signal_valuesfile_native)
    out_file_list.insert(1,noise_valuesfile_native)
    out_file_list.insert(2,in_signal_roifile_native)
    out_file_list.insert(3,in_noise_roifile_native)
    out_file_list.insert(4,snr_file)
    out_file_list.insert(5,out_mat)
    
    return {"signal_valuesfile_native":signal_valuesfile_native,"noise_valuesfile_native":noise_valuesfile_native,
            "in_signal_roifile_native":in_signal_roifile_native,"in_noise_roifile_native":in_noise_roifile_native,
                "mean_signal_native":mean_signal,"stdev_native":stdev,
                "snr_native":snr,"snr_rcorr_native":snr_rcorr,"snr_file_native":snr_file,
                "out_mat_base2native":out_mat,
             "out_files":out_file_list}    


class CalcSNRNativeInputSpec(BaseInterfaceInputSpec):
    in_file = File( mandatory=True, desc='the input file')
    in_signal_roifile = File(mandatory=True, desc='signal roi')
    in_noise_roifile = File(mandatory=True, desc='noise roi')
    in_mat = File(mandatory=True, desc='Transformation matrix from native to roi space ')
    in_roidir = traits.String("", mandatory=False, desc='directory path of rois to allow iterables to be less wordy', usedefault=True)

class CalcSNRNativeOutputSpec(TraitedSpec):
    signal_valuesfile_native=File(desc='the signal values within roi')
    noise_valuesfile_native = File(desc='the noise values within roi')
    in_signal_roifile_native=File(desc='the signal values within roi')
    in_noise_roifile_native = File(desc='the noise values within roi')
    mean_signal_native = traits.Float(desc='mean signal value')
    stdev_native = traits.Float(desc='std deviation of noise')
    snr_native = traits.Float(desc='snr')
    snr_rcorr_native = traits.Float(desc='rayleigh corrected snr')
    snr_file_native = File(desc='snr json file')
    out_mat_base2native = File(mandatory=True, desc='Transformation matrix from roi space to native space ')
    out_files = traits.List(desc='list of files')

    
class CalcSNRNative(BaseInterface):
    input_spec = CalcSNRNativeInputSpec
    output_spec = CalcSNRNativeOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = calc_snr_native_proc(
            self.inputs.in_file,
            self.inputs.in_signal_roifile,
            self.inputs.in_noise_roifile,
            self.inputs.in_mat,
            self.inputs.in_roidir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results



def reg_func_func_proc(in_source_func,ref_file,ref_vol=0,cost_func='mutualinfo'):
    import nibabel
    import numpy as np
    import os
    from nipype.interfaces.base import Undefined
    import nipype.interfaces.fsl as fsl
    import json


    refbasename=os.path.basename(ref_file).split('.')[0]    
    out_vol=os.path.join(os.getcwd(),refbasename + '_vol_{}.nii.gz'.format(str(ref_vol)))
    fslROI=fsl.ExtractROI()
    fslROI.inputs.in_file=ref_file
    fslROI.inputs.roi_file=out_vol
    fslROI.inputs.t_min=ref_vol
    fslROI.inputs.t_size=1
    res1=fslROI.run()
    
    funcbasename=os.path.basename(in_source_func).split('.')[0]    
    out_file=os.path.join(os.getcwd(), funcbasename + '_registered.nii.gz')
    tmp_file=os.path.join(os.getcwd(), funcbasename + '_registered_tmp.nii.gz')
    flt = fsl.FLIRT(cost_func=cost_func)
    flt.inputs.in_file=in_source_func
    flt.inputs.reference = out_vol
    flt.inputs.out_file = tmp_file
    res2 = flt.run()
    out_mat=res2.outputs.out_matrix_file

    flt.inputs.apply_xfm = True
    flt.inputs.in_matrix_file = out_mat
    flt.inputs.in_file=in_source_func
    flt.inputs.reference = ref_file
    flt.inputs.out_file = out_file
    res3 = flt.run()
            
    #populate file list
    out_file_list=[]
    out_file_list.insert(0,out_file)
    out_file_list.insert(1,out_vol)
    out_file_list.insert(2,out_mat)
    
    return {"out_file":out_file,"out_vol":out_vol,
                "out_mat":out_mat,
             "out_files":out_file_list}    



class RegFuncFuncInputSpec(BaseInterfaceInputSpec):
    in_source_func = File( mandatory=True, desc='the input functional')
    ref_file = File(mandatory=True, desc='The reference functional')
    ref_vol = traits.Int(mandatory=False, desc='Reference volume to use for registration')

class RegFuncFuncOutputSpec(TraitedSpec):
    out_file=File(desc='the func file in reference space')
    out_vol=File(desc='the reference volume used for registration')
    out_mat = File(desc='the transformation matrix')
    out_files = traits.List(desc='list of files')
    
class RegFuncFunc(BaseInterface):
    input_spec = RegFuncFuncInputSpec
    output_spec = RegFuncFuncOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = reg_func_func_proc(
            self.inputs.in_source_func,
            self.inputs.ref_file,
            self.inputs.ref_vol
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results



def collate_avscale_proc(in_mat):
    import nibabel
    import numpy as np
    from nipype.interfaces.fsl import AvScale 
    import json
    import os

    avscale = AvScale()
    avscale.inputs.mat_file = in_mat
    res = avscale.run()  
    geom_transform={}
    geom_transform["determinant"]=res.outputs.determinant
    geom_transform["average_scaling"]=res.outputs.average_scaling
    geom_transform["scales"]=res.outputs.scales
    geom_transform["skews"]=res.outputs.skews
    geom_transform["rotation_translation_matrix"]=res.outputs.rotation_translation_matrix

    basefile=os.path.basename(in_mat).split('.')[0]
    avscale_file=os.path.join(os.getcwd(),basefile + '_avscale.json')
    with open(avscale_file, 'w') as outfile:
            json.dump(geom_transform, outfile,indent=2)
            
    #populate file list
    out_files=[]
    out_files.insert(0,avscale_file)
    
    return { "avscale_file":avscale_file,
             "out_files":out_files}    

class CollateAvscaleInputSpec(BaseInterfaceInputSpec):
    in_mat = File( mandatory=True, desc='the affine linear transformaton matrix')

class CollateAvscaleOutputSpec(TraitedSpec):
    avscale_file = File(desc='avscale json file')
    out_files = traits.List(desc='list of files')
    
class CollateAvscale(BaseInterface):
    input_spec = CollateAvscaleInputSpec
    output_spec = CollateAvscaleOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = collate_avscale_proc(
            self.inputs.in_mat
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


# pass in an func and calculate snr as well - this is being done because the TSNR() default code from 
# nipype uses the input file header as basis but for int16 this is vausing low precision. Might be possible to 
# do this in anoher way by changing the data type.
def calc_teesnr_inroi_proc(in_file,in_signal_roifile,in_roidir=""):
    import nibabel as nib
    import numpy as np
    import os
    from nipype.interfaces.base import Undefined
    import json
    from pathlib import Path

    img = nib.load(in_file)
    header = img.header.copy()
    data=img.get_fdata()
    img_dtype=img.get_data_dtype()

    if img_dtype.kind == "i":
        header.set_data_dtype(np.float32)
        data = data.astype(np.float32)

    meanimg = np.mean(data, axis=3)
    stddevimg = np.std(data, axis=3)
    tsnr = np.zeros_like(meanimg)
    stddevimg_nonzero = stddevimg > 1.0e-3
    tsnr[stddevimg_nonzero] = (
            meanimg[stddevimg_nonzero] / stddevimg[stddevimg_nonzero]
    )

    
    basefile=os.path.basename(in_file).split('.')[0]
    tsnr_file = os.path.join(os.getcwd(),basefile + '_tsnr.nii.gz') 
    tsnr_mean_file =  os.path.join(os.getcwd(),basefile + '_tsnr_mean.nii.gz') 
    tsnr_stddev_file =  os.path.join(os.getcwd(),basefile + '_tsnr_stddev.nii.gz') 


    img = nib.Nifti1Image(tsnr, img.affine, header)
    nib.save(img, os.path.abspath(tsnr_file))
    img = nib.Nifti1Image(meanimg, img.affine, header)
    nib.save(img, os.path.abspath(tsnr_mean_file))
    img = nib.Nifti1Image(stddevimg, img.affine, header)
    nib.save(img, os.path.abspath(tsnr_stddev_file))

    tsnr_data = {}
    if not ( in_signal_roifile is None or in_signal_roifile is Undefined):

        # if signal path doesn't exist then tack on to in_rodirfile location
        if not Path(in_signal_roifile).exists():
            in_signal_roifile=os.path.join(in_roidir,in_signal_roifile)

        signalimg = nib.load(in_signal_roifile)
        signaldata_mask = signalimg.get_fdata().astype(np.int16)
        signalmask = signaldata_mask[:,:,:] > 0 

        signal=tsnr.copy()
        signal[~signalmask] = 0
        tsnr_signal_valuesfile=os.path.join(os.getcwd(),basefile + '_tsnr_signal_values.nii.gz') 
        img = nib.Nifti1Image(signal, img.affine, header)
        nib.save(img, tsnr_signal_valuesfile)

        tsnr_in_roi=np.mean(signal[signalmask])

        tsnr_data['tsnr_signal_valuesfile'] = tsnr_signal_valuesfile
        tsnr_data['tsnr_signal_roi'] = in_signal_roifile
        tsnr_data['tsnr_in_roi'] = float(tsnr_in_roi)
    else:
        tsnr_signal_valuesfile = 'None'
        tsnr_data['tsnr_signal_valuesfile'] = 'None'
        tsnr_data['tsnr_signal_roi'] = 'None'
        tsnr_data['tsnr_in_roi'] = 'None'
    
    tsnr_data['in_file'] = in_file
    tsnr_data['tsnr_file'] = tsnr_file
    tsnr_data['tsnr_mean_file'] = tsnr_mean_file
    tsnr_data['tsnr_stddev_file'] = tsnr_stddev_file


    tsnr_json_file=os.path.join(os.getcwd(),basefile + '_tsnr.json')
    with open(tsnr_json_file, 'w') as outfile:
            json.dump(tsnr_data, outfile,indent=2)
            
    #populate file list
    out_file_list=[]
    out_file_list.insert(0,tsnr_file)
    out_file_list.insert(1,tsnr_mean_file)
    out_file_list.insert(2,tsnr_stddev_file)
    out_file_list.insert(3,tsnr_signal_valuesfile)
    out_file_list.insert(4,tsnr_json_file)
    
    return { "tsnr_signal_valuesfile":tsnr_signal_valuesfile,
             "tsnr_file":tsnr_file,
             "tsnr_mean_file":tsnr_mean_file,
             "tsnr_stddev_file":tsnr_stddev_file,
             "tsnr_json_file":tsnr_json_file,
             "out_files":out_file_list}    


class CalcTEESNRROIInputSpec(BaseInterfaceInputSpec):
    in_file = File( mandatory=True, desc='the input file')
    in_signal_roifile = File(mandatory=False, desc='signal roi')
    in_roidir = traits.String("", mandatory=False, desc='directory path of rois to allow iterables to be less wordy', usedefault=True)

class CalcTEESNRROIOutputSpec(TraitedSpec):
    tsnr_signal_valuesfile=File(desc='the signal values within roi')
    tsnr_file = File(desc='tsnr json file')
    tsnr_mean_file = File(desc='tsnr_mean_file')
    tsnr_stddev_file = File(desc='tsnr_stddev_file')
    tsnr_json_file = File(desc='tsnr_json_file ')
    out_files = traits.List(desc='list of files')
    
class CalcTEESNRROI(BaseInterface):
    input_spec = CalcTEESNRROIInputSpec
    output_spec = CalcTEESNRROIOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = calc_teesnr_inroi_proc(
            self.inputs.in_file,
            self.inputs.in_signal_roifile,
            self.inputs.in_roidir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results



# pass in an func and calculate snr as well - this is being done because the TSNR() default code from 
# nipype uses the input file header as basis but for int16 this is vausing low precision. Might be possible to 
# do this in anoher way by changing the data type.
def calc_teesnr_inroi_native_proc(in_file,in_signal_roifile,in_mat,in_roidir=""):
    import nibabel as nib
    import numpy as np
    import os
    import nipype.interfaces.fsl as fsl
    from nipype.interfaces.base import Undefined
    import json
    from pathlib import Path

    img = nib.load(in_file)
    header = img.header.copy()
    data=img.get_fdata()
    img_dtype=img.get_data_dtype()

    if img_dtype.kind == "i":
        header.set_data_dtype(np.float32)
        data = data.astype(np.float32)

    meanimg = np.mean(data, axis=3)
    stddevimg = np.std(data, axis=3)
    tsnr = np.zeros_like(meanimg)
    stddevimg_nonzero = stddevimg > 1.0e-3
    tsnr[stddevimg_nonzero] = (
            meanimg[stddevimg_nonzero] / stddevimg[stddevimg_nonzero]
    )

    
    basefile=os.path.basename(in_file).split('.')[0]
    tsnr_file_native = os.path.join(os.getcwd(),basefile + '_tsnr_native.nii.gz') 
    tsnr_mean_file_native =  os.path.join(os.getcwd(),basefile + '_tsnr_mean_native.nii.gz') 
    tsnr_stddev_file_native =  os.path.join(os.getcwd(),basefile + '_tsnr_stddev_native.nii.gz') 


    img = nib.Nifti1Image(tsnr, img.affine, header)
    nib.save(img, os.path.abspath(tsnr_file_native))
    img = nib.Nifti1Image(meanimg, img.affine, header)
    nib.save(img, os.path.abspath(tsnr_mean_file_native))
    img = nib.Nifti1Image(stddevimg, img.affine, header)
    nib.save(img, os.path.abspath(tsnr_stddev_file_native))

    tsnr_data = {}
    if not ( in_signal_roifile is None or in_signal_roifile is Undefined):

        # if signal path doesn't exist then tack on to in_rodirfile location
        if not Path(in_signal_roifile).exists():
            in_signal_roifile=os.path.join(in_roidir,in_signal_roifile)

        basefile_in_mat=os.path.basename(in_mat).split('.')[0]
        out_mat=os.path.join(os.getcwd(),basefile_in_mat + '_inverse.mat')
        # invert the input transform
        invt = fsl.ConvertXFM()
        invt.inputs.in_file = in_mat
        invt.inputs.invert_xfm = True
        invt.inputs.out_file = out_mat
        res1 = invt.run()

        # transform signal and noise rois to native space
        basefile_signal=os.path.basename(in_signal_roifile).split('.')[0]
        in_signal_roifile_native=os.path.join(os.getcwd(),basefile_signal + '_native.nii.gz')
        flt = fsl.FLIRT()
        flt.inputs.apply_xfm = True
        flt.inputs.interp = 'nearestneighbour'
        flt.inputs.in_matrix_file = out_mat
        flt.inputs.in_file=in_signal_roifile
        flt.inputs.reference = in_file
        flt.inputs.out_file = in_signal_roifile_native
        res2 = flt.run()

        signalimg = nib.load(in_signal_roifile_native)
        signaldata_mask = signalimg.get_fdata().astype(np.int16)
        signalmask = signaldata_mask[:,:,:] > 0 

        signal=tsnr.copy()
        signal[~signalmask] = 0
        tsnr_signal_valuesfile_native=os.path.join(os.getcwd(),basefile + '_tsnr_signal_values_native.nii.gz') 
        img = nib.Nifti1Image(signal, img.affine, header)
        nib.save(img, tsnr_signal_valuesfile_native)

        tsnr_in_roi_native=np.mean(signal[signalmask])

        tsnr_data['tsnr_signal_valuesfile_native'] = tsnr_signal_valuesfile_native
        tsnr_data['tsnr_signal_roi_native'] = in_signal_roifile_native
        tsnr_data['tsnr_in_roi_native'] = float(tsnr_in_roi_native)
        tsnr_data['out_mat_base2native'] = out_mat
    else:
        tsnr_signal_valuesfile_native = 'None'
        tsnr_data['tsnr_signal_valuesfile_native'] = 'None'
        tsnr_data['tsnr_signal_roi_native'] = 'None'
        tsnr_data['tsnr_in_roi_native'] = 'None'
        tsnr_data['out_mat_base2native'] = 'None'
    
    tsnr_data['in_file'] = in_file
    tsnr_data['tsnr_file_native'] = tsnr_file_native
    tsnr_data['tsnr_mean_file_native'] = tsnr_mean_file_native
    tsnr_data['tsnr_stddev_file_native'] = tsnr_stddev_file_native


    tsnr_json_file_native=os.path.join(os.getcwd(),basefile + '_tsnr_native.json')
    with open(tsnr_json_file_native, 'w') as outfile:
            json.dump(tsnr_data, outfile,indent=2)
            
    #populate file list
    out_file_list=[]
    out_file_list.insert(0,tsnr_file_native)
    out_file_list.insert(1,in_signal_roifile_native)
    out_file_list.insert(2,tsnr_mean_file_native)
    out_file_list.insert(3,tsnr_stddev_file_native)
    out_file_list.insert(4,tsnr_signal_valuesfile_native)
    out_file_list.insert(5,tsnr_json_file_native)
    out_file_list.insert(6,out_mat)
    
    return { "tsnr_signal_valuesfile_native":tsnr_signal_valuesfile_native,
             "in_signal_roifile_native":in_signal_roifile_native,
             "tsnr_file_native":tsnr_file_native,
             "tsnr_mean_file_native":tsnr_mean_file_native,
             "tsnr_stddev_file_native":tsnr_stddev_file_native,
             "tsnr_json_file_native":tsnr_json_file_native,
             "out_mat_base2native":out_mat,
             "out_files":out_file_list}    


class CalcTEESNRROINativeInputSpec(BaseInterfaceInputSpec):
    in_file = File( mandatory=True, desc='the input file')
    in_signal_roifile = File(mandatory=False, desc='signal roi')
    in_mat = File(mandatory=True, desc='Transformation matrix from native to roi space ')
    in_roidir = traits.String("", mandatory=False, desc='directory path of rois to allow iterables to be less wordy', usedefault=True)

class CalcTEESNRROINativeOutputSpec(TraitedSpec):
    tsnr_signal_valuesfile_native=File(desc='the signal values within roi')
    in_signal_roifile_native=File(desc='the signal roi')
    tsnr_file_native = File(desc='tsnr json file_native')
    tsnr_mean_file_native = File(desc='tsnr_mean_file_native')
    tsnr_stddev_file_native = File(desc='tsnr_stddev_file_native')
    tsnr_json_file_native = File(desc='tsnr_json_file_native')
    out_mat_base2native = File(desc='base 2 native transform matrix')
    out_files = traits.List(desc='list of files')
    
class CalcTEESNRROINative(BaseInterface):
    input_spec = CalcTEESNRROINativeInputSpec
    output_spec = CalcTEESNRROINativeOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = calc_teesnr_inroi_native_proc(
            self.inputs.in_file,
            self.inputs.in_signal_roifile,
            self.inputs.in_mat,
            self.inputs.in_roidir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results

def create_anat_wf(workflow,output_dir,session_file, base_anat, signal_roi_list, noise_roi_list,in_roidir, prefix):
    
    # Set up Workflow
    main_workflow=workflow
    acrmed_qc_wf = Workflow(name=main_workflow, base_dir=output_dir)

    # Reorient node
    reorient= fsl.utils.Reorient2Std()
    reorient.inputs.in_file=session_file
    reorient_image_node = Node(reorient,name='{}_reorient_image_node'.format(prefix))
   
    # datasink
    sink_output_basedir=os.path.join(output_dir,main_workflow)
    datasink_node=Node(nio.DataSink(),name="{}_datasink_node".format(prefix))
    datasink_node.inputs.base_directory = sink_output_basedir


    flt = fsl.FLIRT(cost_func='mutualinfo')
    flt.inputs.reference = base_anat
    flirt_image = Node(flt,name='flirt_image')
    
    acrmed_qc_wf.connect(reorient_image_node, 'out_file', flirt_image, 'in_file')

    # To prevent filename too long - see https://github.com/nipy/nipype/issues/2061 
    acrmed_qc_wf.config['execution']['parameterize_dirs'] = False
    calc_snr_reg=CalcSNR()
    calc_snr_reg_node=Node(calc_snr_reg,name="{}_calc_snr_reg_node".format(prefix))
    calc_snr_reg_node.inputs.in_roidir = in_roidir
    calc_snr_reg_node.iterables = [ ("in_signal_roifile",signal_roi_list), ("in_noise_roifile",noise_roi_list)]
    calc_snr_reg_node.synchronize = True
    acrmed_qc_wf.connect(flirt_image, 'out_file', calc_snr_reg_node, 'in_file')

    # calculate SNR in native space
    calc_snr_native=CalcSNRNative()
    calc_snr_native_node=Node(calc_snr_native,name="{}_calc_snr_native_node".format(prefix))
    calc_snr_native_node.inputs.in_roidir = in_roidir
    calc_snr_native_node.iterables = [ ("in_signal_roifile",signal_roi_list), ("in_noise_roifile",noise_roi_list)]
    calc_snr_native_node.synchronize = True
    acrmed_qc_wf.connect(reorient_image_node, 'out_file', calc_snr_native_node, 'in_file')
    acrmed_qc_wf.connect(flirt_image, 'out_matrix_file', calc_snr_native_node, 'in_mat')
    
    collate_avscale = CollateAvscale()
    collate_avscale_node=Node(collate_avscale,name="{}_collate_avscale_node".format(prefix))
    acrmed_qc_wf.connect(flirt_image, 'out_matrix_file', collate_avscale_node, 'in_mat')

    #acrmed_qc_wf.connect(collate_avscale_node, 'avscale_file', datasink_node, '{}_reports_registered.@avscale_file'.format(prefix))
    #acrmed_qc_wf.connect(flirt_image, 'out_matrix_file', datasink_node, '{}_reports_registered.@out_matrix_file'.format(prefix))

    #acrmed_qc_wf.connect(calc_snr_reg_node, 'signal_valuesfile', datasink_node, '{}_reports_snr_registered.@signal_valuesfile'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_reg_node, 'noise_valuesfile', datasink_node, '{}_reports_snr_registered.@noise_valuesfile'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_reg_node, 'snr_file', datasink_node, '{}_reports_snr_registered.@snr_file'.format(prefix))

    #acrmed_qc_wf.connect(calc_snr_native_node, 'signal_valuesfile_native', datasink_node, '{}_reports_snr_native.@signal_valuesfile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_node, 'noise_valuesfile_native', datasink_node, '{}_reports_snr_native.@noise_valuesfile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_node, 'in_signal_roifile_native', datasink_node, '{}_reports_snr_native.@in_signal_roifile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_node, 'in_noise_roifile_native', datasink_node, '{}_reports_snr_native.@in_noise_roifile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_node, 'out_mat_base2native', datasink_node, '{}_reports_snr_native.@out_mat_base2native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_node, 'snr_file_native', datasink_node, '{}_reports_snr_native.@snr_file'.format(prefix))

    return acrmed_qc_wf


def create_func_wf(workflow,output_dir,session_file, base_func, signal_roi_list, noise_roi_list,in_roidir, prefix):
    
    # Set up Workflow
    main_workflow=workflow
    acrmed_qc_wf = Workflow(name=main_workflow, base_dir=output_dir)

    # Reorient node
    reorient= fsl.utils.Reorient2Std()
    reorient.inputs.in_file=session_file
    reorient_image_node = Node(reorient,name='{}_reorient_image_node'.format(prefix))
   
    # datasink
    sink_output_basedir=os.path.join(output_dir,main_workflow)
    datasink_node=Node(nio.DataSink(),name="{}_datasink_node".format(prefix))
    datasink_node.inputs.base_directory = sink_output_basedir

    #motion correct
    motion_correct = Node(fsl.MCFLIRT(save_mats=True,
                       dof=12,
                       save_plots=True,
                       cost='mutualinfo',
                       ref_vol=0),
               name="{}_motion_correct".format(prefix))

    acrmed_qc_wf.connect(reorient_image_node, 'out_file', motion_correct, 'in_file')
   
    plot_motion = Node(
        interface=fsl.PlotMotionParams(in_source='fsl'),
        name='plot_motion',
        iterfield=['in_file'])
    plot_motion.iterables = ('plot_type', ['rotations', 'translations'])

    acrmed_qc_wf.connect(motion_correct, 'par_file', plot_motion, 'in_file')
    acrmed_qc_wf.connect(motion_correct, 'par_file', datasink_node, '{}_reports.@par_file'.format(prefix))
    acrmed_qc_wf.connect(plot_motion, 'out_file', datasink_node, '{}_reports.@out_file'.format(prefix))

    reg_funcfunc_mc = RegFuncFunc()
    reg_funcfunc_mc.inputs.ref_file=base_func
    reg_funcfunc_mc.inputs.ref_vol=0
    reg_funcfunc_mc_node = Node(reg_funcfunc_mc,name='{}_reg_funcfunc_mc_node'.format(prefix))
    acrmed_qc_wf.connect(motion_correct, 'out_file', reg_funcfunc_mc_node, 'in_source_func')

    # calculate SNR in native space
    calc_snr_native_mc=CalcSNRNative()
    calc_snr_native_mc_node=Node(calc_snr_native_mc,name="{}_calc_snr_native_mc_node".format(prefix))
    calc_snr_native_mc_node.inputs.in_roidir = in_roidir
    calc_snr_native_mc_node.iterables = [ ("in_signal_roifile",signal_roi_list), ("in_noise_roifile",noise_roi_list)]
    calc_snr_native_mc_node.synchronize = True
    acrmed_qc_wf.connect(motion_correct, 'out_file', calc_snr_native_mc_node, 'in_file')
    acrmed_qc_wf.connect(reg_funcfunc_mc_node, 'out_mat', calc_snr_native_mc_node, 'in_mat')
    
    # To prevent filename too long - see https://github.com/nipy/nipype/issues/2061 
    # use False
    acrmed_qc_wf.config['execution']['parameterize_dirs'] = False
    calc_snr_mc_reg=CalcSNR()
    calc_snr_mc_reg_node=Node(calc_snr_mc_reg,name="{}_calc_snr_reg_node".format(prefix))
    calc_snr_mc_reg_node.inputs.in_roidir = in_roidir
    calc_snr_mc_reg_node.iterables = [ ("in_signal_roifile",signal_roi_list), ("in_noise_roifile",noise_roi_list)]
    calc_snr_mc_reg_node.synchronize = True

    acrmed_qc_wf.connect(reg_funcfunc_mc_node, 'out_file', calc_snr_mc_reg_node, 'in_file')

    calc_tsnr_roi=CalcTEESNRROI()
    calc_tsnr_roi_node=Node(calc_tsnr_roi,name="{}_calc_tsnr_roi_node".format(prefix))
    calc_tsnr_roi_node.inputs.in_roidir = in_roidir
    calc_tsnr_roi_node.iterables = [ ("in_signal_roifile",signal_roi_list)]
    acrmed_qc_wf.connect(reg_funcfunc_mc_node, 'out_file', calc_tsnr_roi_node, 'in_file')

    calc_tsnr_roi_native=CalcTEESNRROINative()
    calc_tsnr_roi_native_node=Node(calc_tsnr_roi_native,name="{}_calc_tsnr_roi_native_node".format(prefix))
    calc_tsnr_roi_native_node.inputs.in_roidir = in_roidir
    calc_tsnr_roi_native_node.iterables = [ ("in_signal_roifile",signal_roi_list)]
    acrmed_qc_wf.connect(motion_correct, 'out_file', calc_tsnr_roi_native_node, 'in_file')
    acrmed_qc_wf.connect(reg_funcfunc_mc_node, 'out_mat', calc_tsnr_roi_native_node, 'in_mat')

    collate_avscale = CollateAvscale()
    collate_avscale_node=Node(collate_avscale,name="{}_collate_avscale_node".format(prefix))
    acrmed_qc_wf.connect(reg_funcfunc_mc_node, 'out_mat', collate_avscale_node, 'in_mat')

    #acrmed_qc_wf.connect(reg_funcfunc_mc_node, 'out_mat', datasink_node, '{}_reports_registered.@out_matrix_file'.format(prefix))
    #acrmed_qc_wf.connect(collate_avscale_node, 'avscale_file', datasink_node, '{}_reports_registered.@avscale_file'.format(prefix))

    #acrmed_qc_wf.connect(calc_snr_mc_reg_node, 'signal_valuesfile', datasink_node, '{}_reports_snr_registered.@signal_valuesfile'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_mc_reg_node, 'noise_valuesfile', datasink_node, '{}_reports_snr_registered.@noise_valuesfile'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_mc_reg_node, 'in_signal_roifile', datasink_node, '{}_reports_snr_registered.@in_signal_roifile'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_mc_reg_node, 'in_noise_roifile', datasink_node, '{}_reports_snr_registered.@in_noise_roifile'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_mc_reg_node, 'snr_file', datasink_node, '{}_reports_snr_registered.@snr_file'.format(prefix))

    #acrmed_qc_wf.connect(calc_snr_native_mc_node, 'signal_valuesfile_native', datasink_node, '{}_reports_snr_native.@signal_valuesfile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_mc_node, 'noise_valuesfile_native', datasink_node, '{}_reports_snr_native.@noise_valuesfile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_mc_node, 'in_signal_roifile_native', datasink_node, '{}_reports_snr_native.@in_signal_roifile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_mc_node, 'in_noise_roifile_native', datasink_node, '{}_reports_snr_native.@in_noise_roifile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_mc_node, 'out_mat_base2native', datasink_node, '{}_reports_snr_native.@out_mat_base2native'.format(prefix))
    #acrmed_qc_wf.connect(calc_snr_native_mc_node, 'snr_file_native', datasink_node, '{}_reports_snr_native.@snr_file'.format(prefix))

    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_signal_valuesfile', datasink_node, '{}_reports_tsnr_registered.@tsnr_signal_valuesfile'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_file', datasink_node, '{}_reports_tsnr_registered.@tsnr_file'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_mean_file', datasink_node, '{}_reports_tsnr_registered.@tsnr_mean_file'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_stddev_file', datasink_node, '{}_reports_tsnr_registered.@tsnr_stddev_file'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_json_file', datasink_node, '{}_reports_tsnr_registered.@tsnr_json_file'.format(prefix))

    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_signal_valuesfile_native', datasink_node, '{}_reports_tsnr_native.@tsnr_signal_valuesfile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_file_native', datasink_node, '{}_reports_tsnr_native.@tsnr_file_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_mean_file_native', datasink_node, '{}_reports_tsnr_native.@tsnr_mean_file_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_stddev_file_native', datasink_node, '{}_reports_tsnr_native.@tsnr_stddev_file_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'tsnr_json_file_native', datasink_node, '{}_reports_tsnr_native.@tsnr_json_file_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'in_signal_roifile_native', datasink_node, '{}_reports_tsnr_native.@in_signal_roifile_native'.format(prefix))
    #acrmed_qc_wf.connect(calc_tsnr_roi_node, 'out_mat_base2native', datasink_node, '{}_reports_tsnr_native.@out_mat_base2native'.format(prefix))

    return acrmed_qc_wf


def collateAnatJson(lines, outputdir, wf_name, anat_current_datetime):
    report_json={}
    anat_json={}
    snr_json={}
    index=0

    # collate data into one handy json!
    for roi in lines:
       entry_json={}
       space_json={}
       signal_roi = roi.split()[0]
       noise_roi = roi.split()[1]
       entry_json["signal_roi"]=signal_roi
       entry_json["noise_roi"]=noise_roi
       space_json["base_space"]=entry_json
       entry_json={}
       # placeholder for native rois
       entry_json["signal_roi_native"]=signal_roi.split(".nii")[0] + "_native.nii.gz"
       entry_json["noise_roi_native"]=noise_roi.split(".nii")[0] + "_native.nii.gz"
       space_json["native_space"]=entry_json
       snr_json[str(index)]=space_json
       index=index+1
    anat_json["snr"]=snr_json
    report_json["structural"]=anat_json
    report_json["structural"]["DateTime"]=anat_current_datetime

    # cycle through registration space snr folders
    rootdir=os.path.join(outputdir, wf_name)
    snrfiles=glob.glob("{}/*/anat_current_calc_snr_reg_node/*snr.json".format(rootdir))
    for snrfile in snrfiles:
        with open(snrfile,'r') as f:
            snr_roi_json = json.load(f)
        snr_mean = snr_roi_json["mean"]
        snr_stddev = snr_roi_json["stdev"]
        snr  =  snr_roi_json["snr"]
        snr_rcorr = snr_roi_json["snr_rcorr"]
        snr_noise_roi = snr_roi_json["noise_roi"]
        snr_signal_roi = snr_roi_json["signal_roi"]
        snr_in_file = snr_roi_json["in_file"]
        for key, value in report_json["structural"]["snr"].items():
            signal_roifile=value["base_space"]["signal_roi"]
            noise_roifile=value["base_space"]["noise_roi"]
            if (os.path.basename(snr_signal_roi) == os.path.basename(signal_roifile)) and \
               (os.path.basename(snr_noise_roi) == os.path.basename(noise_roifile)):
                report_json["structural"]["snr"][key]["base_space"]["snr"] = snr
                report_json["structural"]["snr"][key]["base_space"]["snr_rcorr"] = snr_rcorr
                report_json["structural"]["snr"][key]["base_space"]["snr_mean"] = snr_mean
                report_json["structural"]["snr"][key]["base_space"]["snr_stddev"] = snr_stddev
                report_json["structural"]["snr"][key]["base_space"]["signal_roi"] = snr_signal_roi
                report_json["structural"]["snr"][key]["base_space"]["noise_roi"] = snr_noise_roi 
                report_json["structural"]["snr"][key]["base_space"]["in_file"] = snr_in_file 
                report_json["structural"]["snr"][key]["base_space"]["json_source"] = snrfile
 
    # cycle through native space snr folders
    snrfiles=glob.glob("{}/*/anat_current_calc_snr_native_node/*snr_native.json".format(rootdir))
    for snrfile in snrfiles:
        with open(snrfile,'r') as f:
            snr_roi_json = json.load(f)
        snr_mean = snr_roi_json["mean_native"]
        snr_stddev = snr_roi_json["stdev_native"]
        snr  =  snr_roi_json["snr_native"]
        snr_rcorr = snr_roi_json["snr_rcorr_native"]
        snr_noise_roi = snr_roi_json["in_noise_roifile_native"]
        snr_signal_roi = snr_roi_json["in_signal_roifile_native"]
        snr_in_file = snr_roi_json["in_file_native"]
        for key, value in report_json["structural"]["snr"].items():
            signal_roifile=value["native_space"]["signal_roi_native"]
            noise_roifile=value["native_space"]["noise_roi_native"]
            if (os.path.basename(snr_signal_roi) == os.path.basename(signal_roifile)) and \
               (os.path.basename(snr_noise_roi) == os.path.basename(noise_roifile)):
                report_json["structural"]["snr"][key]["native_space"]["snr_native"] = snr
                report_json["structural"]["snr"][key]["native_space"]["snr_rcorr_native"] = snr_rcorr
                report_json["structural"]["snr"][key]["native_space"]["snr_mean_native"] = snr_mean
                report_json["structural"]["snr"][key]["native_space"]["snr_stddev_native"] = snr_stddev 
                report_json["structural"]["snr"][key]["native_space"]["signal_roi_native"] = snr_signal_roi
                report_json["structural"]["snr"][key]["native_space"]["noise_roi_native"] = snr_noise_roi
                report_json["structural"]["snr"][key]["native_space"]["in_file_native"] = snr_in_file 
                report_json["structural"]["snr"][key]["native_space"]["json_source_native"] = snrfile 

    avscalefile=glob.glob("{}/anat_current_collate_avscale_node/*avscale.json".format(rootdir))[0] 
    with open(avscalefile,'r') as f:
        avscale_json = json.load(f)
    avscale_json["json_source"] = avscalefile  
    report_json["structural"]["geometry"] = avscale_json

    return report_json


def collateFuncJson(lines, outputdir, wf_name, func_current_datetime):
    report_json={}
    func_json={}
    snr_json={}
    tsnr_json={}
    index=0

    # collate data into one handy json!
    for roi in lines:
       entry_json={}
       entry_tsnr_json={}
       space_json={}
       space_tsnr_json={}
       signal_roi = roi.split()[0]
       noise_roi = roi.split()[1]
       entry_json["signal_roi"]=signal_roi
       entry_tsnr_json["signal_roi"]=signal_roi
       entry_json["noise_roi"]=noise_roi
       space_json["base_space"]=entry_json
       space_tsnr_json["base_space"]=entry_tsnr_json

       entry_json={}
       entry_tsnr_json={}
       # placeholder for native rois
       entry_json["signal_roi_native"]=signal_roi.split(".nii")[0] + "_native.nii.gz"
       entry_tsnr_json["signal_roi_native"]=signal_roi.split(".nii")[0] + "_native.nii.gz"
       entry_json["noise_roi_native"]=noise_roi.split(".nii")[0] + "_native.nii.gz"
       space_json["native_space"]=entry_json
       space_tsnr_json["native_space"]=entry_tsnr_json

       snr_json[str(index)]=space_json
       tsnr_json[str(index)]=space_tsnr_json

       index=index+1
    func_json["snr"]=snr_json
    func_json["tsnr"]=tsnr_json
    report_json["functional"]=func_json
    report_json["functional"]["DateTime"]=func_current_datetime


    # cycle through registration space snr folders
    rootdir=os.path.join(outputdir, wf_name)
    snrfiles=glob.glob("{}/*/func_current_calc_snr_reg_node/*snr.json".format(rootdir))
    for snrfile in snrfiles:
        with open(snrfile,'r') as f:
            snr_roi_json = json.load(f)
        snr_mean = snr_roi_json["mean"]
        snr_stddev = snr_roi_json["stdev"]
        snr  =  snr_roi_json["snr"]
        snr_rcorr = snr_roi_json["snr_rcorr"]
        snr_noise_roi = snr_roi_json["noise_roi"]
        snr_signal_roi = snr_roi_json["signal_roi"]
        snr_in_file = snr_roi_json["in_file"]
        for key, value in report_json["functional"]["snr"].items():
            signal_roifile=value["base_space"]["signal_roi"]
            noise_roifile=value["base_space"]["noise_roi"]
            if (os.path.basename(snr_signal_roi) == os.path.basename(signal_roifile))  and \
               (os.path.basename(snr_noise_roi) == os.path.basename(noise_roifile)):
                report_json["functional"]["snr"][key]["base_space"]["snr"] = snr
                report_json["functional"]["snr"][key]["base_space"]["snr_rcorr"] = snr_rcorr
                report_json["functional"]["snr"][key]["base_space"]["snr_mean"] = snr_mean
                report_json["functional"]["snr"][key]["base_space"]["snr_stddev"] = snr_stddev
                report_json["functional"]["snr"][key]["base_space"]["signal_roi"] = snr_signal_roi
                report_json["functional"]["snr"][key]["base_space"]["noise_roi"] = snr_noise_roi
                report_json["functional"]["snr"][key]["base_space"]["in_file"] = snr_in_file 
                report_json["functional"]["snr"][key]["base_space"]["json_source"] = snrfile 
 
    # cycle through native space snr folders
    snrfiles=glob.glob("{}/*/func_current_calc_snr_native_mc_node/*snr_native.json".format(rootdir))
    for snrfile in snrfiles:
        with open(snrfile,'r') as f:
            snr_roi_json = json.load(f)
        snr_mean = snr_roi_json["mean_native"]
        snr_stddev = snr_roi_json["stdev_native"]
        snr  =  snr_roi_json["snr_native"]
        snr_rcorr = snr_roi_json["snr_rcorr_native"]
        snr_noise_roi = snr_roi_json["in_noise_roifile_native"]
        snr_signal_roi = snr_roi_json["in_signal_roifile_native"]
        snr_in_file = snr_roi_json["in_file_native"]
        for key, value in report_json["functional"]["snr"].items():
            signal_roifile=value["native_space"]["signal_roi_native"]
            noise_roifile=value["native_space"]["noise_roi_native"]
            if (os.path.basename(snr_signal_roi) == os.path.basename(signal_roifile))  and \
               (os.path.basename(snr_noise_roi) == os.path.basename(noise_roifile)):
                report_json["functional"]["snr"][key]["native_space"]["snr_native"] = snr
                report_json["functional"]["snr"][key]["native_space"]["snr_rcorr_native"] = snr_rcorr
                report_json["functional"]["snr"][key]["native_space"]["snr_mean_native"] = snr_mean
                report_json["functional"]["snr"][key]["native_space"]["snr_stddev_native"] = snr_stddev 
                report_json["functional"]["snr"][key]["native_space"]["signal_roi_native"] = snr_signal_roi
                report_json["functional"]["snr"][key]["native_space"]["noise_roi_native"] = snr_noise_roi
                report_json["functional"]["snr"][key]["native_space"]["in_file_native"] = snr_in_file 
                report_json["functional"]["snr"][key]["native_space"]["json_source_native"] = snrfile  

    avscalefile=glob.glob("{}/func_current_collate_avscale_node/*avscale.json".format(rootdir))[0] 
    with open(avscalefile,'r') as f:
        avscale_json = json.load(f)
    avscale_json["json_source"] = avscalefile  
    report_json["functional"]["geometry"] = avscale_json

    # cycle through registration space tsnr folders
    tsnrfiles=glob.glob("{}/*/func_current_calc_tsnr_roi_node/*tsnr.json".format(rootdir))
    for tsnrfile in tsnrfiles:
        with open(tsnrfile,'r') as f:
            tsnr_roi_json = json.load(f)
        tsnr_signal_roi = tsnr_roi_json["tsnr_signal_roi"]
        tsnr_in_roi  =  tsnr_roi_json["tsnr_in_roi"]
        tsnr_file  =  tsnr_roi_json["tsnr_file"]
        tsnr_mean_file  =  tsnr_roi_json["tsnr_mean_file"]
        tsnr_stddev_file  =  tsnr_roi_json["tsnr_stddev_file"]
        tsnr_in_file = tsnr_roi_json["in_file"]
       
        for key, value in report_json["functional"]["tsnr"].items():
            signal_roifile=value["base_space"]["signal_roi"]
            if os.path.basename(tsnr_signal_roi) == os.path.basename(signal_roifile):
                report_json["functional"]["tsnr"][key]["base_space"]["signal_roi"] = tsnr_signal_roi
                report_json["functional"]["tsnr"][key]["base_space"]["tsnr_in_roi"] = tsnr_in_roi
                report_json["functional"]["tsnr"][key]["base_space"]["tsnr_file"] = tsnr_file
                report_json["functional"]["tsnr"][key]["base_space"]["tsnr_mean_file"] = tsnr_mean_file
                report_json["functional"]["tsnr"][key]["base_space"]["tsnr_stddev_file"] = tsnr_stddev_file
                report_json["functional"]["tsnr"][key]["base_space"]["in_file"] = tsnr_in_file 
                report_json["functional"]["tsnr"][key]["base_space"]["json_source"] = tsnrfile  

    # cycle through native space snr folders
    tsnrfiles=glob.glob("{}/*/func_current_calc_tsnr_roi_native_node/*tsnr_native.json".format(rootdir))
    for tsnrfile in tsnrfiles:
        with open(tsnrfile,'r') as f:
            tsnr_roi_json = json.load(f)
        tsnr_signal_roi = tsnr_roi_json["tsnr_signal_roi_native"]
        tsnr_in_roi  =  tsnr_roi_json["tsnr_in_roi_native"]
        tsnr_file  =  tsnr_roi_json["tsnr_file_native"]
        tsnr_mean_file  =  tsnr_roi_json["tsnr_mean_file_native"]
        tsnr_stddev_file  =  tsnr_roi_json["tsnr_stddev_file_native"]
        tsnr_in_file = tsnr_roi_json["in_file"]
       
        for key, value in report_json["functional"]["tsnr"].items():
            signal_roifile=value["native_space"]["signal_roi_native"]
            if os.path.basename(tsnr_signal_roi) == os.path.basename(signal_roifile):
                report_json["functional"]["tsnr"][key]["native_space"]["signal_roi_native"] = tsnr_signal_roi
                report_json["functional"]["tsnr"][key]["native_space"]["tsnr_in_roi_native"] = tsnr_in_roi
                report_json["functional"]["tsnr"][key]["native_space"]["tsnr_file_native"] = tsnr_file
                report_json["functional"]["tsnr"][key]["native_space"]["tsnr_mean_file_native"] = tsnr_mean_file
                report_json["functional"]["tsnr"][key]["native_space"]["tsnr_stddev_file_native"] = tsnr_stddev_file
                report_json["functional"]["tsnr"][key]["native_space"]["in_file_native"] = tsnr_in_file 
                report_json["functional"]["tsnr"][key]["native_space"]["json_source_native"] = tsnrfile  

    return report_json



