import warnings
import pandas as pd
import numpy as np
from datetime import datetime, date

warnings.filterwarnings(action='ignore')
from THEDAP_MIXOPTIM.DapSpecPhase1 import DapSpecPhase1
from THEDAP_MIXOPTIM.DapOptPhase3 import DapOptPhase3


class DapMixOptimizer():

    def __init__(self, 
            opt_type, opt_mix, input_age, input_gender, input_weight, 
            inputModelDate = datetime.strftime(date.today(), "%Y-%m-%d"), userName = '', platform_list= [],
            **kwargs
        ):
        self.opt_type = pd.read_json(opt_type).iloc[0, 0]
        self.input_age = input_age
        self.input_gender = input_gender
        self.input_weight = input_weight
        self.opt_mix = opt_mix
        
        self.modelDate = inputModelDate
        self.userName = userName
        self.platform_list = platform_list

        self.opt_maxbudget = kwargs.get('opt_maxbudget', "[{\"opt_maxbudget\": \"1000\"}]")
        self.opt_seq = kwargs.get('opt_seq', "[{\"opt_seq\": \"1\"}]")
        self.opt_target = kwargs.get('opt_target', "[{\"opt_target\": \"0.1\"}]")

        if self.opt_type == 'reach_max':
            optimizer_ = DapOptPhase3(inputModelDate=self.modelDate, userName=self.userName, platform_list=self.platform_list)
            self.op, self.fr = optimizer_.opt_phase2(self.opt_mix, self.input_age, self.input_gender, self.input_weight,
                                          self.opt_seq, self.opt_maxbudget)
            self.spec, self.viz = None, None

        elif self.opt_type == 'reach_target':
            optimizer_ = DapOptPhase3(inputModelDate=self.modelDate, userName=self.userName, platform_list=self.platform_list)
            self.op, self.fr = optimizer_.opt_phase3(self.opt_mix, self.input_age, self.input_gender, self.input_weight,
                                          self.opt_target)
            self.spec, self.viz = None, None

        elif self.opt_type == 'reach_spectrum':
            optimizer_ = DapSpecPhase1(inputModelDate=self.modelDate, userName=self.userName, platform_list=self.platform_list)
            self.plot, self.spec = optimizer_.spec_phase1(self.opt_mix,  self.input_age, self.input_gender, self.input_weight, self.opt_seq,  self.opt_maxbudget)
            self.viz, self.op, self.fr = None, None, None

    ### JSON 형태 변환
    def opt_result(self, op):
        op = sorted(op, key=lambda x: np.sum(x['budget']), reverse=True)
        opt_result = {}
        for i in range(len(op)):
            key_ = str('{:,.0f}'.format(np.max(op[i]['budget'])))
            val_ = op[i].to_dict(orient='records')
            opt_result[key_] = val_

        return [opt_result]

    ### 썬버스트 변환
    def get_suburst(self, op):
        op = sorted(op, key=lambda x: np.sum(x['budget']), reverse=True)
        sunburst_dict = {}
        for i in range(len(op)):
            key_ = str('{:,.0f}'.format(np.max(op[i]['budget'])))
            op_ = op[i].query('platform != "Total"')[['platform', 'product', 'budget']]

            platform_ = {}
            for p in op_['platform']:
                op__ = op_.query('platform == "{}"'.format(p))
                platform_[p] = op__[['product', 'budget']].to_dict(orient='records')

            sunburst_dict[key_] = platform_
        return [sunburst_dict]

    ### JSON 형태 변환
    def freq_result(self, fr):
        freq_result = pd.DataFrame()
        for f in fr:
            freq_result = pd.concat([freq_result, f], axis=0)

        freq_result = freq_result.reset_index(drop=True). \
            sort_values('budget', ascending=True).to_dict(orient='records')

        return freq_result

    def get_result(self):
        if self.opt_type in ['reach_max', 'reach_target']:
            return {'table_viz': self.get_suburst(self.op), 'table_opt': self.opt_result(self.op),
                    'table_freq': self.freq_result(self.fr)}

        else:
            return {'table_plot': self.plot, 'table_spec': self.spec}
