# crop_zoom_sc.py crops and zooms spinal cord images after they have been segmented with JIM so that the spinal cord is centered in the new image.  The scale factor, crop distance, resolution, and number of voxels must be set by the user.

#!/usr/bin/env python
from matplotlib.path import Path
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from scipy import interpolate
import scipy.ndimage.interpolation as wezoom
import glob
import os
import sys
import argparse

def create_zoomed_files(psir, roi):

    #User defined settings
    cropdist = 15
    scalefac = 10
    numvox = cropdist*2*scalefac
    bsp_order=2
    resolution = .78125
    x_shift = 128
    y_shift = 128

    k1 = getpts(roi)
    psir_affine, psir_data = load(psir)

    a1=np.ones([k1.shape[0],k1.shape[1]])
    a1[:,1]=-1
    k1flip = k1*a1
    
    # TRANSFORM FROM JIM COORDINATES (0,0 at center of PSIR image) TO PSIR SPACE
    k1_new = jim2psir(k1flip, scalefac, x_shift, y_shift)

    # FIND CENTER OF MASS OF SPINAL CORD WM, THEN SET BORDERS
    xminv, xmaxv, yminv, ymaxv, xmin, xmax, ymin, ymax = find_com(k1_new, cropdist, scalefac, x_shift, y_shift)

    # MAKE PSIR CROP IMAGE
    psir_crop = psir_data[xminv:xmaxv, yminv:ymaxv]
    crop_aff = np.diag([-resolution*psir_crop.shape[0]/numvox,resolution*psir_crop.shape[1]/numvox,1,1])
    z = psir_crop[:,:,0]

    # MAKE PSIR CROP INTERP IMAGE
    zoomed = wezoom.zoom(z, numvox/(xmaxv-xminv), order=bsp_order)
    zoomed_file = psir[:-7]+'_zoomed.nii.gz'
    nib.save(nib.Nifti1Image(zoomed,crop_aff), zoomed_file)

    # MAKE CORD MASK IMAGE
    cord_mask = make_nifti(zoomed, xmin, xmax, ymin, ymax, k1flip)
    cord_mask_file = psir[:-7]+'_zoomed_cord_mask.nii.gz'
    cord_mask_img = nib.save(nib.Nifti1Image(cord_mask.astype("uint8"), crop_aff), cord_mask_file)

    # MAKE CORD IMAGE
    cord = np.multiply(cord_mask, zoomed)

    return zoomed_file, cord_mask_file

def getpts(filepath):
    rois = 0
    cordlist=[]
    cordxylist = []
    roifile = open(filepath, 'r')
    lines = roifile.readlines()
    roifile.close()
    for line in lines:
        if "X=" in line:
            cordlist.append(line.strip())
    for pt in cordlist:
        parts = pt.split('=')
        x = parts[1][:-3]
        y = parts[-1]
        cordxylist += [[x, y]]
        cord = np.array(cordxylist, dtype='float64')
    return cord

def load(image):
    img = nib.load(image)
    img_affine = img.get_affine()
    img_data = np.array(img.get_data())
    return img_affine, img_data

def jim2psir(k1flip, scale_factor, x_shift, y_shift): 
    k1_new = (k1flip*scale_factor) + [x_shift, y_shift]
    return k1_new

def find_com(k1_new, cropdist, scale_factor, x_shift, y_shift):
    k1_new_mean = np.floor(k1_new.mean(0))
    print 'new means: ', k1_new_mean
    k1_centerj = (k1_new_mean-[x_shift, y_shift])/scale_factor
    print 'new center: ', k1_centerj
    xminv = k1_new_mean[0]-cropdist
    xmaxv = k1_new_mean[0]+cropdist
    yminv = k1_new_mean[1]-cropdist
    ymaxv = k1_new_mean[1]+cropdist
    xmin = (xminv-x_shift)/scale_factor
    xmax = (xmaxv-x_shift)/scale_factor
    ymin = (yminv-y_shift)/scale_factor
    ymax = (ymaxv-y_shift)/scale_factor
    print 'xmin = %s; xmax = %s; ymin = %s; ymax = %s' % (xmin, xmax, ymin, ymax)
    return xminv, xmaxv, yminv, ymaxv, xmin, xmax, ymin, ymax

def make_nifti(zoomed, xmin, xmax, ymin, ymax, k1flip):
    k1flip_path = Path(k1flip)
    X = np.linspace(xmin,xmax,zoomed.shape[0])
    Y = np.linspace(ymin,ymax,zoomed.shape[0])
    cord = np.zeros([len(X),len(Y)])
    for i,x in enumerate(X):
        for j,y in enumerate(Y):
            cord[i,j]=k1flip_path.contains_point([x,y])
    print X, Y
    return cord




