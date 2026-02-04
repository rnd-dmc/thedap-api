import pandas as pd
import numpy as np
import json
from collections import OrderedDict
from THEDAP_SIMULATION.DapPhase2_v4 import DapPhase2_v4

class DapPhase3_v4(DapPhase2_v4):
    
    def __init__(self):
        super().__init__()


    ## 전체 기준 결과
    def phase3(self, input_mix, input_age, input_gender, input_weight):
        df = self.phase2(input_mix, input_age, input_gender)

        ovr = df.groupby(['gender', 'age_min', 'age_max']). \
            agg({'e_imp': 'sum', 'eimp_weighted': 'sum', 'target_impression': 'sum', 'target_impression_weighted': 'sum',
                'population': 'mean',
                'ratio2_a': 'min', 'ratio2_af': 'max', 'ratio2_grps': 'max', 'ratio3_a': 'min', 'ratio3_af': 'max',
                'ratio3_grps': 'max', 'ratio4_a': 'min', 'ratio4_af': 'max', 'ratio4_grps': 'max',
                'ratio5_a': 'min', 'ratio5_af': 'max', 'ratio5_grps': 'max', 'ratio6_a': 'min', 'ratio6_af': 'max',
                'ratio6_grps': 'max', 'ratio7_a': 'min', 'ratio7_af': 'max', 'ratio7_grps': 'max',
                'ratio8_a': 'min', 'ratio8_af': 'max', 'ratio8_grps': 'max', 'ratio9_a': 'max', 'ratio9_af': 'max',
                'ratio9_grps': 'max', 'ratio10_a': 'max', 'ratio10_af': 'max', 'ratio10_grps': 'max'}).reset_index()

        trans_list = [[]]
        for i in range(ovr.shape[0]):
            filt = df.loc[
                df['gender'].isin([ovr['gender'][i]]) & (df['age_min']).isin([ovr['age_min'][i]]) & (df['age_max']).isin(
                    [ovr['age_max'][i]])]
            weight = self.get_weight(input_weight,
                                grps=np.sum(filt['eimp_weighted'] / np.mean(filt['population'])),
                                reach=np.sum(filt['e_reach_n']) / np.mean(filt['population']),
                                channel=filt.query('eimp_weighted > .0').shape[0])
            trans_list[0].append(self.trans_duplicate(filt['e_reach_p'].to_list(), weight))

        ovr['e_reach_p'] = trans_list[0]
        ovr['isTarget'] = np.where(ovr['target_impression'] > 0, 1, 0)

        ovr['e_reach_n'] = ovr['e_reach_p'] * ovr['population'] 
        ovr['target_reach_n'] = ovr['e_reach_n'] * ovr['isTarget']
        ovr['target_reach_p'] = ovr['target_reach_n'] / ovr['population']
        
        ovr['e_grps'] = ovr['e_imp'] / ovr['population'] * 100
        ovr['e_grps_weighted'] = ovr['eimp_weighted'] / ovr['population'] * 100
        ovr['target_grps'] = ovr['target_impression'] / ovr['population'] * 100
        ovr['target_grps_weighted'] = ovr['target_impression_weighted'] / ovr['population'] * 100
        
        ovr['af'] = ovr['e_imp'] / ovr['e_reach_n']
        ovr['af_weighted'] = ovr['eimp_weighted'] / ovr['e_reach_n']
        ovr['target_af'] = ovr['target_impression'] / ovr['target_reach_n']
        ovr['target_af_weighted'] = ovr['target_impression_weighted'] / ovr['target_reach_n']

        for r in range(2, 11):
            e_ratio = 'e_ratio' + str(r)
            e_reach_p = 'e_reach' + str(r) + '_p'
            e_reach_n = 'e_reach' + str(r) + '_n'

            target_ratio = 'target_ratio' + str(r)
            target_reach_p = 'target_reach' + str(r) + '_p'
            target_reach_n = 'target_reach' + str(r) + '_n'

            ratio_a = 'ratio' + str(r) + '_a'
            ratio_af = 'ratio' + str(r) + '_af'
            ratio_grps = 'ratio' + str(r) + '_grps'

            ###
            ovr[e_ratio] = (1 / (1 + np.exp(-(
                        ovr[ratio_a] + ovr[ratio_af] * np.log(ovr['af_weighted']) + ovr[ratio_grps] * np.log(
                    ovr['e_grps_weighted'])))))
            ovr[target_ratio] = (1 / (1 + np.exp(-(
                        ovr[ratio_a] + ovr[ratio_af] * np.log(ovr['target_af_weighted']) + ovr[ratio_grps] * np.log(
                    ovr['target_grps_weighted'])))))

            ###
            if r == 2:
                _e_reach_p = 'e_reach_p'
                _target_reach_p = 'target_reach_p'
            else:
                _e_reach_p = 'e_reach' + str(r - 1) + '_p'
                _target_reach_p = 'target_reach' + str(r - 1) + '_p'

            ovr[e_reach_p] = ovr[_e_reach_p] * ovr[e_ratio]
            ovr[target_reach_p] = ovr[_target_reach_p] * ovr[target_ratio]
            ovr[e_reach_n] = ovr[e_reach_p] * ovr['population']
            ovr[target_reach_n] = ovr[target_reach_p] * ovr['population']

        ovr.fillna(0, inplace=True)
        ovr = self.round_float(ovr)

        return (ovr)


    def summary_overall(self, input_mix, input_age, input_gender, input_weight):
        ph3 = self.phase3(input_mix, input_age, input_gender, input_weight)
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True)
        trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][0]

        df = ph3.copy()
        df['isDemo'] = np.where(df['e_imp'] == 0, 0, 1)
        demo_pop = int(sum(df['isDemo'] * df['population']))

        ovr = pd.DataFrame({'budget': [sum(mix_cleaned['budget'])],
                            'e_imp': [sum(df['e_imp'])], 'eimp_weighted': [sum(df['eimp_weighted'])],
                            'target_impression': [sum(df['target_impression'])],
                            'target_impression_weighted': [sum(df['target_impression_weighted'])],
                            'e_reach_n': [sum(df['e_reach_n'])], 'target_reach_n': [sum(df['target_reach_n'])],
                            'e_reach2_n': [sum(df['e_reach2_n'])], 'target_reach2_n': [sum(df['target_reach2_n'])],
                            'e_reach3_n': [sum(df['e_reach3_n'])], 'target_reach3_n': [sum(df['target_reach3_n'])],
                            'e_reach4_n': [sum(df['e_reach4_n'])], 'target_reach4_n': [sum(df['target_reach4_n'])],
                            'e_reach5_n': [sum(df['e_reach5_n'])], 'target_reach5_n': [sum(df['target_reach5_n'])],
                            'e_reach6_n': [sum(df['e_reach6_n'])], 'target_reach6_n': [sum(df['target_reach6_n'])],
                            'e_reach7_n': [sum(df['e_reach7_n'])], 'target_reach7_n': [sum(df['target_reach7_n'])],
                            'e_reach8_n': [sum(df['e_reach8_n'])], 'target_reach8_n': [sum(df['target_reach8_n'])],
                            'e_reach9_n': [sum(df['e_reach9_n'])], 'target_reach9_n': [sum(df['target_reach9_n'])],
                            'e_reach10_n': [sum(df['e_reach10_n'])], 'target_reach10_n': [sum(df['target_reach10_n'])],
                            'trans_pop': [trans_pop], 'demo_pop': [demo_pop]})

        ovr['e_grps'] = ovr['e_imp'] / ovr['demo_pop'] * 100
        ovr['e_grps_weighted'] = ovr['eimp_weighted'] / ovr['demo_pop'] * 100
        ovr['af'] = ovr['e_imp'] / ovr['e_reach_n']
        ovr['af_weighted'] = ovr['eimp_weighted'] / ovr['e_reach_n']
        
        ovr['target_grps'] = ovr['target_impression'] / ovr['trans_pop'] * 100
        ovr['target_grps_weighted'] = ovr['target_impression_weighted'] / ovr['trans_pop'] * 100
        ovr['target_af'] = ovr['target_impression'] / ovr['target_reach_n']
        ovr['target_af_weighted'] = ovr['target_impression_weighted'] / ovr['target_reach_n']

        for r in range(1, 11):
            if r == 1:
                reach = 'reach'
            else:
                reach = 'reach' + str(r)

            e_reach_p = 'e_' + reach + '_p'
            e_reach_n = 'e_' + reach + '_n'
            target_reach_p = 'target_' + reach + '_p'
            target_reach_n = 'target_' + reach + '_n'

            ovr[e_reach_p] = ovr[e_reach_n] / ovr['demo_pop']
            ovr[target_reach_p] = ovr[target_reach_n] / ovr['trans_pop']

        ovr = ovr[['budget', 'target_impression', 'target_impression_weighted','target_grps', 'target_grps_weighted',
                'target_reach_n', 'target_reach_p', 'target_reach2_p', 'target_reach3_p', 'target_reach4_p',
                'target_reach5_p',
                'target_reach6_p', 'target_reach7_p', 'target_reach8_p', 'target_reach9_p', 'target_reach10_p',
                'target_af', 'target_af_weighted']]. \
            fillna(0).assign(line="Grand Total")
        ovr = self.round_float(ovr)

        return (ph3, ovr)