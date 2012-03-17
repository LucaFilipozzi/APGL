
import numpy
import logging
import sys
from apgl.util.ProfileUtils import ProfileUtils 
from exp.sandbox.predictors.DecisionTreeLearner import DecisionTreeLearner
from apgl.data.ExamplesGenerator import ExamplesGenerator  
from sklearn.tree import DecisionTreeRegressor 

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
numpy.random.seed(22)

class DecisionTreeLearnerProfile(object):
    def profileLearnModel(self):
        numExamples = 200
        numFeatures = 20
        minSplit = 10
        maxDepth = 20
        
        generator = ExamplesGenerator()
        X, y = generator.generateBinaryExamples(numExamples, numFeatures)   
            
        learner = DecisionTreeLearner(minSplit=minSplit, maxDepth=maxDepth) 
        #learner.learnModel(X, y)
        #print("Done")
        ProfileUtils.profile('learner.learnModel(X, y) ', globals(), locals())

    def profileDecisionTreeRegressor(self): 
        numExamples = 200
        numFeatures = 20
        minSplit = 10
        maxDepth = 20
        
        generator = ExamplesGenerator()
        X, y = generator.generateBinaryExamples(numExamples, numFeatures)   
            
        regressor = DecisionTreeRegressor(min_split=minSplit, max_depth=maxDepth, min_density=0.0)
        
        ProfileUtils.profile('regressor.fit(X, y)', globals(), locals())

profiler = DecisionTreeLearnerProfile()
profiler.profileLearnModel()
#profiler.profileDecisionTreeRegressor()

#Takes 0.925 s