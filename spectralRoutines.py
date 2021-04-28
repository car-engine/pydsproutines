# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 16:26:26 2021

@author: Lken
"""

import numpy as np
import sympy
from numba import jit

#%%
def czt(x, f1, f2, binWidth, fs):
    '''
    n = (f2-f1)/binWidth + 1
    w = - i 2 pi (f2-f1+binWidth)/(n fs)
    a = i 2 pi (f1/fs)
    
    cztoptprep(len(x), n, w, a, nfft) # nfft custom to >len(x)+n-1
    '''
    
    k = int((f2-f1)/binWidth + 1)
    m = len(x)
    nfft = m + k
    foundGoodPrimes = False
    while not foundGoodPrimes:
        nfft = nfft + 1
        if np.max(sympy.primefactors(nfft)) <= 7: # change depending on highest tolerable radix
            foundGoodPrimes = True
    
    kk = np.arange(-m+1,np.max([k-1,m-1])+1)
    kk2 = kk**2.0 / 2.0
    ww = np.exp(-1j * 2 * np.pi * (f2-f1+binWidth)/(k*fs) * kk2)
    chirpfilter = 1 / ww[:k-1+m]
    fv = np.fft.fft( chirpfilter, nfft )
    
    nn = np.arange(m)
    # print(ww[m+nn-1].shape)
    aa = np.exp(1j * 2 * np.pi * f1/fs * -nn) * ww[m+nn-1]
    
    y = x * aa
    fy = np.fft.fft(y, nfft)
    fy = fy * fv
    g = np.fft.ifft(fy)
    
    g = g[m-1:m+k-1] * ww[m-1:m+k-1]
    
    return g

def dft(x, freqs, fs):
    '''

    Parameters
    ----------
    x : array
        Input data.
    freqs : array
        Array of bin frequency values to evaluate at.

    Returns
    -------
    Array of DFT bin values for input frequencies.

    '''
    
    output = np.zeros(len(freqs),dtype=np.complex128)
    for i in np.arange(len(freqs)):
        freq = freqs[i]
        tone = np.exp(-1j*2*np.pi*freq*np.arange(len(x))/fs)
        output[i] = np.dot(tone, x)
    
    return output

@jit(nopython=True)
def toneSpectrum(f0, freqs, fs, N, phi=0, A=1.0):
    '''
    Returns a spectrum corresponding to applying DFT to a tone with frequency f0 and phase phi,
    at values specified by the 'freqs' array.
    
    See the tone reproduction notebook for details.
    '''
    
    vals = -1j * A * (1 - np.exp(-1j*2*np.pi*(freqs-f0)*N/fs))/(2*np.pi*(freqs-f0)/fs) * np.exp(1j*phi)
    
    return vals
