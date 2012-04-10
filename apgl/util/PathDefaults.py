import os
import tempfile

#TODO: Read from a configuration file
class PathDefaults(object):
    """
    This class stores some useful global default paths. 
    """
    def __init__(self):
        pass

    @staticmethod
    def getProjectDir():
        import apgl
        dir =  apgl.__path__[0].split("/")

        try:
            ind = dir.index('APGL')+1

            projectDir = ""
            for i in range(0, ind):
                projectDir +=  dir[i] + "/"
        except ValueError:
            projectDir = os.path.abspath( __file__ )
            projectDir, head = os.path.split(projectDir)
            projectDir, head = os.path.split(projectDir)
            projectDir, head = os.path.split(projectDir)
            projectDir, head = os.path.split(projectDir)
            projectDir += "/"
        return projectDir 

    @staticmethod
    def getSourceDir():
        dir = os.path.abspath( __file__ )
        dir, head = os.path.split(dir)
        dir, head = os.path.split(dir)
        return dir 
        
    @staticmethod
    def getDataDir():
        return os.path.join(PathDefaults.getProjectDir(), "data") + os.sep

    @staticmethod
    def getTempDir():
        return tempfile.gettempdir() + "/"

    @staticmethod
    def getOutputDir():
        return os.path.join(PathDefaults.getProjectDir(), "output") + os.sep
