# This class contains the attributes and methodss allowing to define the SDDP algorithm.
class SDDPStage:


    def __init__(self, instance):
        self.Instance = instance
        self.Stage = [ SDDPStage() for t in self.Instance.TimeBucketSet ]