# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 15:08:45 2021

@author: Seo
"""

import numpy as np
import matplotlib.pyplot as plt
from signalCreationRoutines import *
from spectralRoutines import *

#%%
def musicAlg(x, freqlist, rows, plist, snapshotJump=None, fwdBwd=False, useSignalAsNumerator=False):
    '''
    p (i.e. plist) is the dimensionality of the signal subspace. The function will return an array based on freqlist
    for every value of p in plist.
    
    x is expected as a 1-dim array (flattened).
    
    snapshotJump is the index jump per column vector. By default this jump is equal to rows,
    i.e. each column vector is unique (matrix constructed via reshape), but may not resolve frequencies well.
    
    fwdBwd is a boolean which toggles the use of the Forward-Backward correction of the covariance matrix (default False).
    
    '''
    
    if not np.all(np.abs(freqlist) <= 1.0):
        raise ValueError("Frequency list input must be normalized.")

    if snapshotJump is None: # then we snapshot via slices
        # 1 2 3 4 5 6 ->
        # 1 3 5
        # 2 4 6  for example
        x = x.reshape((-1,1)) # vectorize
        cols = int(np.floor(len(x)/rows))
        xslen = rows * cols
        xs = x[:xslen] # we cut off the ending bits
        xs = xs.reshape((cols, rows)).T
    else: # we use the rate to populate our columns
        # e.g. for snapshot jump = 1,
        # 1 2 3 4 5 6 ->
        # 1 2 3 4 5
        # 2 3 4 5 6
        if snapshotJump <= 0:
            raise ValueError("snapshotJump must be at least 1.")
            
        x = x.flatten() # in case it's not flat
        cols = (x.size - rows) / snapshotJump # calculate thee required columns
        xs = np.zeros((rows, int(cols+1)), x.dtype)
        print("Matrix dim is %d, %d" % (xs.shape[0], xs.shape[1]))
        for i in range(xs.shape[1]): # fill the columns
            xs[:,i] = x[i * snapshotJump : i * snapshotJump + rows]
            
    Rx = (1/cols) * xs @ xs.conj().T
    if fwdBwd:
        J = np.eye(Rx.shape[0])
        # Reverse row-wise to form the antidiagonal exchange matrix
        J = J[:,::-1]
        Rx = 0.5 * (Rx + J @ Rx.T @ J)
        print("Using forward-backward covariance.")
    
    u, s, vh = np.linalg.svd(Rx)
    
    f = np.zeros(len(freqlist))
    
    # # DEPRECATED
    # for i in range(len(freqlist)):
    #     freq = freqlist[i]
        
    #     e = np.exp(1j*2*np.pi*freq*np.arange(rows)).reshape((1,-1)) # row, 2-d vector directly
    #     eh = e.conj()
        
    #     d = eh @ u[:,p:]
    #     breakpoint()
    #     denom = np.sum(np.abs(d)**2)
        
    #     f[i] = 1/denom
   
    # Instead of iterations, generate a one-time Vandermonde matrix of eh
    ehlist = np.exp(-1j*2*np.pi*freqlist.reshape((-1,1))*np.arange(rows)) # generate the e vector for every frequency i.e. Vandermonde
    
    # Generate output
    numerator = 1.0 # default numerator
    if not hasattr(plist, '__len__'): # if only one value of p
        d = ehlist @ u[:,plist:]
        denom = np.sum(np.abs(d)**2, axis=1)
        
        if useSignalAsNumerator: # Construct the generalised inverse (we have the SVD results already)
            sp = s[:plist]**-0.5 # Take the p eigenvalues and reciprocal + root them -> generalised inverse root eigenvalues
            siginv = u[:,:plist] * sp # assume u = v, i.e. u^H = v^H, scale by the inverse eigenvalues
            n = ehlist @ siginv
            numerator = np.sum(np.abs(n)**2, axis=1)
            
        f = numerator / denom
        
    else: # for multiple values of p
        f = np.zeros((len(plist), len(freqlist)))
        for i in range(len(plist)):
            p = plist[i]
            d = ehlist @ u[:,p:]
            denom = np.sum(np.abs(d)**2, axis=1)
            
            if useSignalAsNumerator:
                sp = s[:p]**-0.5 # Take the p eigenvalues and reciprocal + root them -> generalised inverse root eigenvalues
                siginv = u[:,:p] * sp # assume u = v, i.e. u^H = v^H, scale by the inverse eigenvalues
                n = ehlist @ siginv
                numerator = np.sum(np.abs(n)**2, axis=1)
                
            f[i,:] = numerator / denom
        
    return f, u, s, vh

#%%
if __name__ == '__main__':
    #%%
    plt.close("all")
    fs = 1e4
    length = 1*fs
    fdiff = 0.5
    f0 = 1000
    padding = 0
    # x = np.exp(1j*2*np.pi*f0*np.arange(length)/fs) + np.exp(1j*2*np.pi*(f0+fdiff)*np.arange(length)/fs)
    x = np.pad(np.exp(1j*2*np.pi*f0*np.arange(length)/fs), (padding,0))
    
    # noisyAmp = (np.random.randn(int(length+100))*0.000001+1.0)
    # noisyAmp = np.abs(noisyAmp)
    noisyAmp = 1.0
    
    # How does it react to a non-constant amplitude tone?
    plt.figure("Amplitude for second tone")
    plt.plot(noisyAmp)
    
    x = x + noisyAmp * np.pad(np.exp(1j*2*np.pi*(f0+fdiff)*np.arange(length)/fs), (0,padding))
    x = x + (np.random.randn(x.size) + np.random.randn(x.size)*1j) * np.sqrt(1e-1)
    # xfft = np.fft.fft(x)    
    
    fineFreqStep = 0.01
    fineFreqRange = 3 # peg to the freqoffset
    fineFreqVec = np.arange((f0+fdiff/2)-fineFreqRange,(f0+fdiff/2)+fineFreqRange + 0.1*fineFreqStep, fineFreqStep)
    xczt = czt(x, (f0+fdiff/2)-fineFreqRange,(f0+fdiff/2)+fineFreqRange, fineFreqStep, fs)
    
    freqlist = np.arange(f0-fdiff,f0+fdiff*2,0.01)
    
    # One-shot evaluation for all desired p values
    plist = np.arange(1,5)
    rows = 1000
    t1 = time.time()
    f, u, s, vh = musicAlg(x, freqlist/fs, rows, plist, snapshotJump=1)
    f_fb, u_fb, s_fb, vh_fb = musicAlg(x, freqlist/fs, rows, plist, snapshotJump=1, fwdBwd=True)
    f_fb_ns, u_fb_ns, s_fb_ns, vh_fb_ns = musicAlg(x, freqlist/fs, rows, plist, snapshotJump=1, fwdBwd=True, useSignalAsNumerator=True)
    t2 = time.time()
    print("Took %f s." % (t2-t1))
    
    fig,ax = plt.subplots(3,1,num="Comparison")
    ax[0].set_title("Standard MUSIC, %d rows" % (rows))
    ax[1].set_title("Forward-Backward MUSIC, %d rows" % (rows))
    ax[2].set_title("Forward-Backward MUSIC + Signal Subspace, %d rows" % (rows))
    for i in range(len(ax)):
        # plt.plot(makeFreq(len(x),fs), np.abs(xfft)/np.max(np.abs(xfft)))
        ax[i].plot(fineFreqVec, np.abs(xczt)/ np.max(np.abs(xczt)), label='CZT')
        ax[i].vlines([f0,f0+fdiff],0,1,colors='r', linestyles='dashed',label='Actual')
   
    for i in range(f.shape[0]):
        ax[0].plot(freqlist, f[i]/np.max(f[i]), label='MUSIC, p='+str(plist[i]))
        ax[0].legend()
        ax[0].set_xlim([fineFreqVec[0],fineFreqVec[-1]])
        
        ax[1].plot(freqlist, f_fb[i]/np.max(f_fb[i]), label='MUSIC, p='+str(plist[i]))
        ax[1].legend()
        ax[1].set_xlim([fineFreqVec[0],fineFreqVec[-1]])
        
        ax[2].plot(freqlist, f_fb_ns[i]/np.max(f_fb_ns[i]), label='MUSIC, p='+str(plist[i]))
        ax[2].legend()
        ax[2].set_xlim([fineFreqVec[0],fineFreqVec[-1]])
        
        
    plt.figure("Eigenvalues")
    plt.plot(np.log10(s),'x-')
    
    ## At 1e-4 noise:
    # Note that at rows=100, unable to resolve. But at rows = 1000, able to resolve (dependency on 'block size' despite total length being equal)
    # p=3 is now required, instead of p=2
    ## At 1e-3 noise:
    # Similarly, at rows = 1000, able to resolve, but clarity is diminished.
    # Still p=3
    ## At 1e-2 noise:
    # No longer able to resolve with rows=1000.
    
    ## Now with snapshotJump = 1 (sliding window for every possible snapshot rather than unique snapshot)
    # 1e-2 noise:
    # Now possible to resolve with rows = 1000 !!!
    # Even at 1e-1 noise!!
