import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from THEDAP_SIMULATION.DapPhase3_v4 import DapPhase3_v4
# from THEDAP_SIMULATION.thedap_v4_output import THEDAP_OUTPUT
# from THEDAP_UTILS.thedap_v4_mixclean import *

class DapCurve_v4(DapPhase3_v4):
    
    def __init__(self):
        super().__init__()
        
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

        pbar = enumerate(curve_range[1:])
        # rc_df = pd.DataFrame()
        rc_df_list = []
        for _, budget in pbar:
            mix_cleaned['budget_r'] = mix_cleaned['budget'] / np.sum(mix_cleaned['budget'])
            mix_cleaned['budget_origin'] = mix_cleaned['budget']
            mix_cleaned['budget'] = mix_cleaned['budget_r'] * budget
            mix_cleaned['e_grp'] = np.where(mix_cleaned['bid_type'] == "E.GRP 직접입력",
                                            mix_cleaned['e_grp'] * (mix_cleaned['budget'] / mix_cleaned['budget_origin']),
                                            mix_cleaned['e_grp'])
            mix_cleaned['e_imp'] = np.where(mix_cleaned['bid_type'] == "E.IMP 직접입력",
                                            mix_cleaned['e_imp'] * (mix_cleaned['budget'] / mix_cleaned['budget_origin']),
                                            mix_cleaned['e_imp'])

            mix_cleaned.reset_index(drop=True, inplace=True)

            data_list = []
            for rownum in range(0, mix_cleaned.shape[0]):
                data = OrderedDict()
                row_values = mix_cleaned.loc[rownum,]
                data['platform'] = row_values['platform']
                data['product'] = row_values['product']
                data['gender'] = row_values['gender']
                data['min'] = float(row_values['min'])
                data['max'] = float(row_values['max'])
                data['impact'] = row_values['impact']
                data['budget'] = float(row_values['budget'])
                data['bid_type'] = row_values['bid_type']
                data['bid_cost'] = row_values['bid_cost']
                data['bid_rate'] = row_values['bid_rate']
                data['e_imp'] = row_values['e_imp']
                data['e_grp'] = row_values['e_grp']
                data_list.append(data)

            input_mix2 = json.dumps(data_list, ensure_ascii=False)
            _, summary_ovr = self.summary_overall(input_mix2, input_age, input_gender, input_weight)
            # rc_df = pd.concat([rc_df, summary_ovr])
            rc_df_list.append(summary_ovr)

        rc_df = pd.concat(rc_df_list, ignore_index=True)
        rc_df = pd.concat([pd.DataFrame(np.zeros(rc_df.shape[1]).reshape(1, rc_df.shape[1]), columns=rc_df.columns.tolist()), rc_df]).reset_index(
            drop=True). \
            rename_axis('idx').reset_index()
        # rc_df['budget'] = rc_df['budget'].apply(lambda x: np.round(x))
        rc_df['budget'] = curve_range

        rc_data_list = []
        for rownum in range(0, rc_df.shape[0]):
            data2 = OrderedDict()
            row_values2 = rc_df.loc[rownum,]
            data2['idx'] = float(row_values2['idx'])
            data2['budget'] = float(row_values2['budget'])
            data2['target_grps'] = float(row_values2['target_grps'])
            # data2['target_grps_weighted'] = float(row_values2['target_grps_weighted'])
            data2['target_reach_p'] = float(row_values2['target_reach_p'])
            # data2['target_reach2_p'] = float(row_values2['target_reach2_p'])
            # data2['target_reach3_p'] = float(row_values2['target_reach3_p'])
            # data2['target_reach4_p'] = float(row_values2['target_reach4_p'])
            # data2['target_reach5_p'] = float(row_values2['target_reach5_p'])
            # data2['target_reach6_p'] = float(row_values2['target_reach6_p'])
            # data2['target_reach7_p'] = float(row_values2['target_reach7_p'])
            # data2['target_reach8_p'] = float(row_values2['target_reach8_p'])
            # data2['target_reach9_p'] = float(row_values2['target_reach9_p'])
            # data2['target_reach10_p'] = float(row_values2['target_reach10_p'])
            data2['target_af'] = float(row_values2['target_af'])
            # data2['target_af_weigthed'] = float(row_values2['target_af_weighted'])
            rc_data_list.append(data2)
        j = json.loads(json.dumps(rc_data_list, ensure_ascii=False))

        return j