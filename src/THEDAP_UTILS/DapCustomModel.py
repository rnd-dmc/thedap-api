import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

class DapCustomModel():
    
    def __init__(self, uploadData):
        self.uploadData = self.cleanData(uploadData)        
    
    def roundFloat(self, x):
        
        try:
            if isinstance(x, float) or isinstance(x, int):
                return np.round(x, 6)
            
            return .0 
        except:
            return .0
        
    def cleanData(self, uploadData):
        cleanedData = pd.DataFrame(uploadData).dropna(subset=['grps', 'reach_p'])
        cleanedData = cleanedData.\
            replace([np.inf, -np.inf], np.nan).\
            dropna(subset=['grps', 'reach_p']).\
            map(lambda x: self.roundFloat(x)).\
            query('grps > .0 & reach_p > .0 & reach_p < 99.').\
            to_dict(orient='records')
        
        return cleanedData

    def getDataParameter(self):
        data = pd.DataFrame(self.uploadData)
        rowN = data.shape[0]
        
        maxGrps = np.max(data['grps'])
        data['reach_p'] = (data['reach_p'] / 100).apply(lambda x: self.roundFloat(x))
        paramC = self.roundFloat(np.max(data['reach_p']) * 1.25) if self.roundFloat(np.max(data['reach_p'] * 1.25)) <= .9999 else .9999
        
        if rowN >= 20:
            
            try:
                data['paramC'] = paramC
                data['logGrps'] = np.log(data['grps'])
                data['logit'] = np.log(data['reach_p'] / (data['paramC'] - data['reach_p']))

                model = smf.ols('logit ~ logGrps', data=data).fit()
                paramA = self.roundFloat(model.params.iloc[0])
                paramB = self.roundFloat(model.params.iloc[1])
                
                return maxGrps, paramA, paramB, paramC
                
            except:
                
                return maxGrps, -4.5, 0.9, paramC
        
        return maxGrps, -4.5, 0.9, paramC
    
    def getResult(self):
        
        maxGrps, paramA, paramB, paramC = self.getDataParameter()
        
        return {
            "dataScatter":self.uploadData,
            "maxGrps":maxGrps,
            "paramA":paramA,
            "paramB":paramB,
            "paramC":paramC
        }