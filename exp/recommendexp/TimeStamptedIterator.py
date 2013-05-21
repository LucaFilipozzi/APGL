import numpy 
import gc 
import logging 
import scipy.sparse 
from datetime import datetime  
from exp.util.SparseUtils import SparseUtils 

class TimeStamptedIterator(object): 
    def __init__(self, ratingDataset, isTraining, centreRows=True): 
        """
        Initialise this iterator with a ratingDataset object and indicate whether 
        we want the training or test set. 
        """
        self.currentTimeStamp = ratingDataset.iterStartTimeStamp
        self.timeDelta = ratingDataset.timeStep 
        self.ratingDataset = ratingDataset
        
        self.i = 0
        self.maxIter = ratingDataset.maxIter 
        self.isTraining = isTraining 
        self.centreRows = centreRows 
        
    def next(self):
        if self.currentTimeStamp >= self.ratingDataset.endTimeStamp + self.timeDelta or self.i==self.maxIter: 
            logging.debug("Final iteration: " + str(self.i))
            raise StopIteration
            
        logging.debug("Current : " + str(datetime.utcfromtimestamp(self.currentTimeStamp))) 
        
        #Find all ratings before and including current date 
        ind = numpy.searchsorted(self.ratingDataset.sortedDates, self.currentTimeStamp, side="right")
        
        currentIsTrainRatings = self.ratingDataset.isTrainRating[self.ratingDataset.dateInds[0:ind]] 
        currentRatings = self.ratingDataset.ratings[self.ratingDataset.dateInds[0:ind]]
        currentInds = self.ratingDataset.trainInds[:, self.ratingDataset.dateInds[0:ind]]
        
        if self.isTraining: 
            currentRatings[numpy.logical_not(currentIsTrainRatings)] = 0 
        else: 
            currentRatings[currentIsTrainRatings] = 0 
        
        X = scipy.sparse.csc_matrix((currentRatings, currentInds), dtype=self.ratingDataset.ratings.dtype)      
        X.eliminate_zeros()
        X.prune()
        
        del currentRatings
        del currentInds
        gc.collect()
        
        if self.centreRows: 
            logging.debug("Centering rows of X with shape " + str(X.shape))
            X, mu = SparseUtils.centreRows(X)   
        
        X.eliminate_zeros()
        X.prune()
        
        if self.isTraining: 
            assert X.nnz  == currentIsTrainRatings.sum() 
        else: 
            assert X.nnz  == numpy.logical_not(currentIsTrainRatings).sum() 
         
        self.currentTimeStamp += self.timeDelta
        self.i += 1

        return X

    def __iter__(self):
        return self  