'''
Created on 2012-05-10

@author: Andrew
'''
from collections import defaultdict

import os

import pyclone.zshelve as shelve

class TraceDB(object):
    def __init__(self, file_prefix, mode='r', max_cache_size=1000):
        if mode in ['a', 'r'] and not os.path.exists(file_prefix):
            raise Exception("{0} does not exists.".format(file_prefix))
        elif mode == 'w':
            if os.path.exists(file_prefix):
                raise Exception("{0} exists, cannot overwrite.".format(file_prefix))
            if not os.path.exists(os.path.dirname(os.path.abspath(file_prefix))):
                raise Exception("Folder {0} does not exist to create pyclone file in.".format(os.path.dirname(file_prefix)))
        
        self.mode = mode
        
        self._load_db(file_prefix)

        self._cache_size = 0
            
        self._max_cache_size = max_cache_size
    
    def _load_db(self, file_prefix):
        '''
        Load the shelve db object if it exists, otherwise initialise.
        '''
        self._db = shelve.open(file_prefix, writeback=True)
        
        # Check if file exists, if not initialise
        if 'trace' not in self._db:                
            self._db['trace'] = {'alpha' : [], 'labels' : [], 'phi' : []}
            
            self._db.sync()
                
    def __getitem__(self, key):
        return self._db[key]
    
    def __setitem__(self, key, value):
        if self.mode == 'r':
            raise Exception('AnalysisDB cannot be edited in read only mode.')
             
        self._db[key] = value 
        
    def update_trace(self, state):
        for parameter in self._db['trace']:
            self._db['trace'][parameter].append(state[parameter])
        
        self._cache_size += 1
        
        if self._cache_size >= self._max_cache_size:
            self._db.sync()
            self._cache_size = 0
    
    def close(self):
        self._db.close() 
    
    def sync(self):
        self._db.sync()

class TracePostProcessor(object):
    def __init__(self, trace_db):       
        self.genes = trace_db['genes']
        
        self._db = trace_db
        
        self._results = trace_db['trace']
        
    @property
    def alpha(self):
        '''
        Returns a list of alpha values of each iteration of the MCMC chain.
        '''
        return self._results['alpha']
    
    @property
    def cellular_frequencies(self):
        '''
        Returns a dictionary with keys genes, and values posterior samples of cellular frequencies.
        '''
        phi = defaultdict(list)
        
        labels = self.labels
        
        for gene in labels:
            for label, sample in zip(labels[gene], self._results['phi']):
                phi[gene].append(sample[label])
        
        return phi

    @property
    def labels(self):
        '''
        Returns a dict with keys genes, and values the class label of the genes for each MCMC sample.
        '''
        labels = defaultdict(list)
        
        for sample in self._results['labels']:
            for gene, label in zip(self.genes, sample):
                labels[gene].append(label)
        
        return labels

    @property
    def num_components(self):
        '''
        Returns a list of the number of components used in by each MCMC sample.
        '''
        labels = self._results['labels']
        
        num_components = []
        
        for sample in labels:
            num_components.append(len(set(sample)))
        
        return num_components
    
    @property
    def num_iterations(self):
        '''
        Returns the number of MCMC iterations.
        '''
        return self._db['sampler'].num_iters