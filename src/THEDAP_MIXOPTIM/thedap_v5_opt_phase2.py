import warnings
import pandas as pd 
import numpy as np

warnings.filterwarnings(action='ignore')
from THEDAP_MIXOPTIM.thedap_v5_opt_phase1 import getOPTPhase1

class getOPTPhase2(getOPTPhase1):
    
    def __init__(self):
        super().__init__()

    def opt_phase2(self, opt_mix, input_age, input_gender, input_weight, opt_seq, opt_maxbudget, ftol=1e-04):
        opt_mix_cleaned = self.opt_tidy(opt_mix, input_age, input_gender)
        seq = self.get_seq(opt_seq)
        maxbudget = self.get_maxbudget(opt_maxbudget)
        
        optimal_range = np.linspace(0, maxbudget, seq+1)
        freq = []
        result = []
        
        for o in optimal_range:
            if o > 0:
                budget_val = np.round(o * 1e+06)
                opt_x = self.get_reach_max(opt_mix_cleaned, input_age, input_gender, input_weight, o, ftol=ftol)
                
                opt_mix_temp = opt_mix_cleaned.copy()
                opt_mix_temp['budget'] = opt_x * budget_val
                opt_mix_temp['epoch_budget'] = budget_val
                
                input_mix_json = opt_mix_temp.assign(imp="", reach="").to_json(orient='records', force_ascii=False)
                
                _, freq_ = self.summary_total(
                    input_mix=input_mix_json,
                    input_age=input_age,
                    input_gender=input_gender,
                    input_weight=input_weight
                )
                
                freq__ = freq_.assign(
                    alloc_rat = np.round(np.sum(opt_x)),
                    platform = 'Total',
                    product = '',
                    budget = budget_val
                ).\
                filter([
                    'platform', 'product', 'alloc_rat', 'budget', 'target_grps',
                    'target_grps_weighted', 'target_reach_p', 'target_reach2_p',
                    'target_reach3_p', 'target_reach4_p', 'target_reach5_p',
                    'target_reach6_p', 'target_reach7_p', 'target_reach8_p',
                    'target_reach9_p', 'target_reach10_p'
                ])
                
                freq.append(freq__)

                # 
                _, result_ = self.summary_each_line(
                    input_mix=input_mix_json,
                    input_age=input_age,
                    input_gender=input_gender
                )
                
                result_['budget'] = np.round(result_['budget'].astype(float))
                result.append(
                    pd.concat([
                        result_.assign(alloc_rat=np.round(opt_x, 6)), freq__
                    ], ignore_index=True).\
                    filter([
                        'platform', 'product', 'alloc_rat', 'budget', 'target_grps',
                        'target_reach_p', 'target_reach2_p', 'target_reach3_p',
                        'target_reach4_p', 'target_reach5_p', 'target_reach6_p',
                        'target_reach7_p', 'target_reach8_p', 'target_reach9_p',
                        'target_reach10_p'
                    ]),
                )

        return [result, freq]