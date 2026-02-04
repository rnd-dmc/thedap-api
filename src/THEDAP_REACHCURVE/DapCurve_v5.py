import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from datetime import datetime, date
from THEDAP_SIMULATION.DapOutput_v5 import DapPhase5_v5

class DapCurve_v5(DapPhase5_v5):
    
    def __init__(self, inputModelDate = datetime.strftime(date.today(), "%Y-%m-%d"), userName = ''):
        super().__init__(inputModelDate=inputModelDate, userName=userName)
            
    def reach_curve(self, input_mix_selected, input_age, input_gender, input_weight, input_seq, input_maxbudget):
        seq = self.get_seq(input_seq)
        maxbudget = self.get_maxbudget(input_maxbudget)
        mix_cleaned = self.mix_clean(input_mix_selected)
        
        # REACH CURVE 영역에서는 IMPACT가 0 ~ 1 사이로 들어옴 
        # mix_cleaned['impact'] = mix_cleaned['impact'].apply(lambda x: x*100 if isinstance(x, float) else x)
        
        step = int(np.round(maxbudget * 1_000_000 / seq))
        end = int(np.round(maxbudget * 1_000_000))

        curve_range = list(range(0, end + step, step))
        curve_range = [c for c in curve_range if c <= end]

        # 마지막 값 보정
        if curve_range[-1] < end:
            curve_range.append(end)
        elif curve_range[-1] > end:
            curve_range[-1] = end
        
        ###
        mix_cleaned_rc = pd.DataFrame()
        mix_cleaned_rc_list = []
        for _, budget in enumerate(curve_range[1:]):
            mix_cleaned['budget_r'] = mix_cleaned['budget'] / np.sum(mix_cleaned['budget'])
            mix_cleaned['budget_origin'] = mix_cleaned['budget']
            mix_cleaned['budget'] = mix_cleaned['budget_r'] * budget
            mix_cleaned['Eimp'] = np.where(mix_cleaned['bid_type'].str.contains('직접입력'),
                                        mix_cleaned['Eimp'] * (mix_cleaned['budget'] / mix_cleaned['budget_origin']),
                                        mix_cleaned['Eimp'])
            mix_cleaned['campaign'] = str(budget)
            mix_cleaned_rc_list.append(mix_cleaned.copy())
            # mix_cleaned_rc = pd.concat([mix_cleaned_rc, mix_cleaned]).reset_index(drop=True)
        
        mix_cleaned_rc = pd.concat(mix_cleaned_rc_list, ignore_index=True)
        
        input_mix2 = mix_cleaned_rc.\
            rename(columns={'Eimp':'imp', 'Areach':'reach'}).\
            astype({'min':'float32', 'max':'float32', 'budget':'float32'}).\
            drop(['budget_r', 'budget_origin', 'Aimp'], axis=1).\
            to_json(orient='records', force_ascii=False)
            
        _, summary_campaign = self.summary_each_campaign(input_mix2, input_age, input_gender, input_weight)
        rc_df = pd.concat([pd.DataFrame(np.zeros(summary_campaign.shape[1]).reshape(1, summary_campaign.shape[1]),
                                        columns=summary_campaign.columns.tolist()), summary_campaign]). \
            sort_values('budget', ascending=True).reset_index(drop=True).rename_axis('idx').reset_index()
        # rc_df['budget'] = rc_df['budget'].apply(lambda x: np.round(x))
        rc_df['budget'] = curve_range

        rc_data_list = []
        for rownum in range(0, rc_df.shape[0]):
            data2 = OrderedDict()
            row_values2 = rc_df.loc[rownum,]
            data2['idx'] = float(row_values2['idx'])
            data2['budget'] = float(row_values2['budget'])
            data2['target_grps'] = float(row_values2['target_grps'])
            data2['target_grps_weighted'] = float(row_values2['target_grps_weighted'])
            data2['target_reach_p'] = float(row_values2['target_reach_p'])
            data2['target_reach2_p'] = float(row_values2['target_reach2_p'])
            data2['target_reach3_p'] = float(row_values2['target_reach3_p'])
            data2['target_reach4_p'] = float(row_values2['target_reach4_p'])
            data2['target_reach5_p'] = float(row_values2['target_reach5_p'])
            data2['target_reach6_p'] = float(row_values2['target_reach6_p'])
            data2['target_reach7_p'] = float(row_values2['target_reach7_p'])
            data2['target_reach8_p'] = float(row_values2['target_reach8_p'])
            data2['target_reach9_p'] = float(row_values2['target_reach9_p'])
            data2['target_reach10_p'] = float(row_values2['target_reach10_p'])
            data2['target_af'] = float(row_values2['target_af'])
            # data2['target_af_weighted'] = float(row_values2['target_af_weighted'])
            # data2['target_af_day'] = float(row_values2['target_af_day'])
            # data2['target_af_week'] = float(row_values2['target_af_week'])
            # data2['target_af_30'] = float(row_values2['target_af_30'])
            # data2['imp_interval'] = row_values2['imp_interval']
            rc_data_list.append(data2)

        j = json.loads(json.dumps(rc_data_list, ensure_ascii=False))

        return j