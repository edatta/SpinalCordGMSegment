"""
This is an implementation of gray matter segmentation of the spinal cord with MGAC (Morphological Geodesic Active Contour) models in MRI images.

The accompanying paper is:
Datta, Esha, et al. "Gray matter segmentation of the spinal cord with active contours in mr images." NeuroImage 147 (2017): 788-799.

This implementation uses the morphsnakes code described in this paper:
Márquez-Neila, P., Baumela, L., Álvarez, L., "A morphological approach to curvature-based evolution of curves and surfaces". IEEE Transactions on Pattern Analysis and Machine Intelligence (PAMI), 2013.
"""


#!/usr/bin/env python
import crop_zoom_sc
import sys
import glob
import os
import morphsnakes
import nibabel as nib
import numpy as np
import argparse

#User Defined
template_image = 'Templates/control_template.nii.gz'
gm_template_image = 'Templates/gm_mask_template.nii.gz'
resolution_x = .078125
resolution_y = .078125

# obtain_prior registers the gray matter template to the image to use as a prior
def obtain_prior(folder, template_image, gm_template_image):
    cord_image = glob.glob(folder+'/*cord_mask.nii.gz')[0]
    subject = os.path.basename(folder)
    output_name = folder+'/'+subject+'_'
    command1 = 'ANTS 2 -m CC['+cord_image+', '+template_image+', 1, 2] -i 100x100x10 -o '+output_name+'.nii.gz -t SyN[0.25] -r Gauss[3,0]'
    command2 = 'WarpImageMultiTransform 2 '+template_image+' '+output_name+'template_reg_to_subject.nii.gz -R '+cord_image+' '+output_name+'Warp.nii.gz '+output_name+'Affine.txt'
    command3 = 'WarpImageMultiTransform 2 '+gm_template_image+' '+output_name+'prior.nii.gz -R '+cord_image+' '+output_name+'Warp.nii.gz '+output_name+'Affine.txt'
    os.system(command1)
    os.system(command2)
    os.system(command3)
    return

# segment_cord outputs an automatically segmented gray matter mask and prints the total cord and gray matter area
def segment_cord(folder, resolution_x, resolution_y):
    subject = os.path.basename(folder)
    prior = glob.glob(folder+'/*prior.nii.gz')[0]
    image = glob.glob(folder+'/*zoomed.nii.gz')[0]
    cord_mask_file = glob.glob(folder+'/*cord_mask.nii.gz')[0]     

    prior_img = nib.load(prior)
    prior_img_data, prior_img_aff = prior_img.get_data(), prior_img.get_affine()
    img = nib.load(image)
    data, aff = img.get_data(), img.get_affine()
    data = data.astype("float")
    cord_mask = nib.load(cord_mask_file)
    cord_mask_data, cord_mask_aff = cord_mask.get_data(), cord_mask.get_affine()
    cord_data = np.multiply(data,cord_mask_data)
    cord_min = np.amin(cord_data[np.nonzero(cord_data)])
    cord_max = np.amax(cord_data[np.nonzero(cord_data)])
    segmented_mask = test_cord_GAC(data, prior_img_data, cord_min, cord_max)
    segmented_mask_img = nib.save(nib.Nifti1Image(segmented_mask.astype("uint8"), aff), folder+'/'+subject+'_autoseg_gm.nii.gz')
    
    cord_area = np.sum(cord_mask_data)*.resolution_x*resolution_y
    GM_area = np.sum(segmented_mask)*resolution_x*resolution_y
    print('CORD AREA = ')
    print(cord_area)
    print('GM AREA = ')
    print(GM_area)
    return

def test_cord_GAC(img, prior, data_min, data_max):
    alpha = 1000
    sigma = 3
    smoothing = 5
    threshold = 1
    balloon = 1
    alpha = int(alpha)
    sigma = float(sigma)
    gI = morphsnakes.gborders(img, alpha, sigma)
    
    smoothing = int(smoothing)
    threshold = float(threshold)
    balloon = int(balloon)
    mgac = morphsnakes.MorphGAC(gI, int(smoothing), float(threshold), int(balloon))
    mgac.levelset = prior
    morphsnakes.evolve_visual(mgac, data_min, data_max, num_iters=45, background=img)
    return mgac.levelset

parser = argparse.ArgumentParser(description="creates nifti of segmented gray matter")
parser.add_argument("<subject folder>", help="folder containing roi file and psir nifti") 

folders = sys.argv[1:]
                
for folder in folders:
    print(folder)
    roi_files = sorted(glob.glob(folder+'/*.roi'))
    nii_files = sorted(glob.glob(folder+'/*.nii.gz'))
    if(len(roi_files) == len(nii_files)):
        print(folder)
        for i, roi_file in enumerate(roi_files):
            nii_file = nii_files[i]
            crop_zoom_sc.create_zoomed_files(nii_file, roi_file)
            obtain_prior(folder, template_image, gm_template_image)
            segment_cord(folder, resolution_x, resolution_y)

