# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 11:59:47 2020

@author: Seo
"""

import time
import numpy as np
import cupy as cp

def createLinearTrajectory(pos1, pos2, stepArray, pos_start=None, randomWalk=None):
    '''
    Parameters
    ----------
    pos1 : Numpy array, 1-D.
        Anchor position 1. Starting position defaults to this.
    pos2 : Numpy array, 1-D.
        Anchor position 2.
    stepArray : Numpy array, 1-D.
        Array of steps. Each point will move by step * directionVectorNormed. Does not need to be equally spaced.
    pos_start : Scalar between [0,1], optional
        The default is None.
        The output will use this as the coefficient along the connecting vector between
        the 2 anchor points, as the position to start iterating at.
    randomWalk : Scalar, optional
        The default is None.
        Adds random noise around the trajectory using a normal distribution.

    Returns
    -------
    Matrix of column vectors of positions along the trajectory.
    For steps which exceed the 2nd anchor point, the direction reverses i.e.
    the trajectory is constructed as a bounce between the two anchor points.
    '''
    
    if pos_start is None:
        pos0 = pos1
    else:
        raise NotImplementedError
        
    result = np.zeros((len(pos1), len(stepArray)))
    finalStepArray = np.zeros(stepArray.shape)
    
    dirVec = pos2 - pos1
    anchorDist = np.linalg.norm(dirVec)
    dirVecNormed = dirVec / np.linalg.norm(dirVec)
    # revDirVecNormed = -dirVecNormed
    
    lengthsCovered = np.floor(stepArray / anchorDist)
    idxReverse = np.argwhere(lengthsCovered%2==1).flatten()
    
    # in these indices, calculate the remaining length
    remainderLen = np.remainder(stepArray[idxReverse], anchorDist)
    
    # these are removed from the full length to induce the backward motion from the 2nd anchor point
    finalStepArray[idxReverse] = anchorDist - remainderLen 
    
    # for forward we do the same
    idxForward = np.argwhere(lengthsCovered%2==0).flatten()
    
    remainderForwardLen = np.remainder(stepArray[idxForward], anchorDist)
    
    finalStepArray[idxForward] = remainderForwardLen
    
    # now calculate the values
    displacements = dirVecNormed.reshape((-1,1))  * finalStepArray.reshape((1,-1))
    
    result = pos0.reshape((-1,1)) + displacements
    
    return result

def createCircularTrajectory(totalSamples, r_a=100000.0, desiredSpeed=100.0, r_h=300.0, sampleTime=3.90625e-6, phi=0):    
    # initialize a bunch of rx points in a circle in 3d
    dtheta_per_s = desiredSpeed/r_a # rad/s
    arcangle = totalSamples * sampleTime * dtheta_per_s # rad
    r_theta = np.arange(phi,phi+arcangle,dtheta_per_s * sampleTime)[:totalSamples]
    
    r_x_x = r_a * np.cos(r_theta)
    r_x_y = r_a * np.sin(r_theta)
    r_x_z = np.zeros(len(r_theta)) + r_h
    r_x = np.vstack((r_x_x,r_x_y,r_x_z)).transpose()
    
    r_xdot_x = r_a * -np.sin(r_theta) * dtheta_per_s
    r_xdot_y = r_a * np.cos(r_theta) * dtheta_per_s
    r_xdot_z = np.zeros(len(r_theta))
    r_xdot = np.vstack((r_xdot_x,r_xdot_y,r_xdot_z)).transpose()
    
    return r_x, r_xdot, arcangle, dtheta_per_s


def calcFOA(r_x, r_xdot, t_x, t_xdot, freq=30e6):
    '''
    Expects individual row vectors.
    All numpy array shapes expected to match.
    
    Assumed that arrays are either all cupy arrays or all numpy arrays,
    operates agnostically using cupy/numpy.
    '''
    xp = cp.get_array_module(r_x)
    
    lightspd = 299792458.0
    
    radial = t_x - r_x # convention pointing towards transmitter
    radial_n = radial / xp.linalg.norm(radial,axis=1).reshape((-1,1)) # don't remove this reshape, nor the axis arg
    
    if radial_n.ndim == 1:
        vradial = xp.dot(radial_n, r_xdot) - xp.dot(radial_n, t_xdot) # minus or plus?
    else:
        # vradial = np.zeros(len(radial_n))
        # for i in range(len(radial_n)):
        #     vradial[i] = np.dot(radial_n[i,:],r_xdot[i,:]) - np.dot(radial_n[i,:], t_xdot[i,:])
        
        # make distinct numpy calls instead of the loop
        dot_radial_r = xp.sum(radial_n * r_xdot, axis=1)
        dot_radial_t = xp.sum(radial_n * t_xdot, axis=1)
        vradial = dot_radial_r - dot_radial_t

    foa = vradial/lightspd * freq

    return foa

def createTriangularSpacedPoints(numPts: int, dist: float=1.0,  startPt: np.ndarray=np.array([0,0])):
    '''
    Spawns locations in a set, beginning with startPt. Each location is spaced 
    'dist' apart from any other location, e.g.
    
       2      1
    
    3     O      0
    
       4      5
       
    The alignment is in the shape of triangles. The order of generation is anticlockwise as shown.
    
    '''
    
    if numPts < 2:
        raise Exception("Please specify at least 2 points.")
        
    origin = np.array([0.0,0.0])
    
    ptList = [origin]
    
    dirVecs = np.array([[1.0,0.0],
                     [0.5,np.sqrt(3)/2],
                     [-0.5,np.sqrt(3)/2],
                     [-1.0,0.0],
                     [-0.5,-np.sqrt(3)/2],
                     [0.5,-np.sqrt(3)/2],
                     [1.0,0.0]]) * dist # cyclical to ensure indexing later on
    
    layer1ptr = 0
    turnLayer = 0
    i = 1
    while i < numPts:
        idx = i - 1 # we go back to 0-indexing
        
        # test for layer
        layer = 1
        while idx >= (layer+1)*(layer/2)*6:
            layer += 1
            
        # print("i: %d, idx: %d, layer: %d"% (i,idx,layer)) # verbose index printing
        
        if layer == 1: # then it's simple, just take the genVec and propagate
            newPt = origin + dirVecs[idx]
            ptList.append(newPt)
            i += 1
        else:
            # use the pointer at layer 1
            layerptr = origin + dirVecs[layer1ptr]
            
            if turnLayer == 0: # go straight all the way
                for d in range(layer-1):
                    layerptr = layerptr + dirVecs[layer1ptr]
                ptList.append(np.copy(layerptr))
                turnLayer = layer - 1 # now set it to turn
            else:
                for d in range(turnLayer-1): # go straight for some layers
                    layerptr = layerptr + dirVecs[layer1ptr]
                for d in range(layer - turnLayer):
                    layerptr = layerptr + dirVecs[layer1ptr+1]
                ptList.append(np.copy(layerptr))
                turnLayer = turnLayer - 1 # decrement
                if turnLayer == 0: # if we have hit turnLayer 0, time to move the layer1ptr
                    layer1ptr = (layer1ptr + 1) % 6
                    
            
            i+=1
            
    # swap to array for cleanliness
    ptList = np.array(ptList)
    ptList = ptList + startPt # move the origin

    return ptList
            
        