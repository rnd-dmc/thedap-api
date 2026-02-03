import pandas as pd
import numpy as np
from datetime import datetime
import json
from collections import OrderedDict
from THEDAP_SIMULATION.thedap_v5_phase4 import getPhase4_v5

class getPhase5_v5(getPhase4_v5):
    
    def __init__(self):
        super().__init__()

    # 전체 결과
    def phase5(self, input_mix, input_age, input_gender, input_weight):
        df = self.phase4(input_mix, input_age, input_gender)

        max_reach = df.groupby(['gender', 'age_min', 'age_max']).\
            agg(
                max_reach_n=('e_reach_n', 'max'), max_reach2_n=('e_reach2_n', 'max'),
                max_reach3_n=('e_reach3_n', 'max'), max_reach4_n=('e_reach4_n', 'max'),
                max_reach5_n=('e_reach5_n', 'max'), max_reach6_n=('e_reach6_n', 'max'),
                max_reach7_n=('e_reach7_n', 'max'), max_reach8_n=('e_reach8_n', 'max'),
                max_reach9_n=('e_reach9_n', 'max'), max_reach10_n=('e_reach10_n', 'max'),
                retargeting = ('retargeting', 'max'), retargeting_cnt=('retargeting_cnt', 'sum'), line_cnt = ('line_cnt', 'sum')
            ).reset_index()
            
        ovr = df.groupby(['gender', 'age_min', 'age_max']). \
            agg({'e_imp': 'sum', 'eimp_weighted': 'sum', 'e_imp_a': 'sum', 'eimp_a_weighted': 'sum',
                'target_impression': 'sum', 'target_impression_weighted': 'sum', 'target_impression_a': 'sum',
                'target_impression_a_weighted': 'sum',
                'population': 'mean', 'agrps': 'sum', 'a_ovr': 'min', 'b_ovr': 'max', 'c_ovr': 'max',
                'e_reach_n': 'sum', 'e_reach2_n': 'sum', 'e_reach3_n': 'sum', 'e_reach4_n': 'sum', 'e_reach5_n': 'sum',
                'e_reach6_n': 'sum', 'e_reach7_n': 'sum', 'e_reach8_n': 'sum', 'e_reach9_n': 'sum', 'e_reach10_n': 'sum',
                'ratio2_a': 'min', 'ratio2_af': 'max', 'ratio2_grps': 'max', 'ratio3_a': 'min', 'ratio3_af': 'max',
                'ratio3_grps': 'max', 'ratio4_a': 'min', 'ratio4_af': 'max', 'ratio4_grps': 'max',
                'ratio5_a': 'min', 'ratio5_af': 'max', 'ratio5_grps': 'max', 'ratio6_a': 'min', 'ratio6_af': 'max',
                'ratio6_grps': 'max', 'ratio7_a': 'min', 'ratio7_af': 'max', 'ratio7_grps': 'max',
                'ratio8_a': 'min', 'ratio8_af': 'max', 'ratio8_grps': 'max', 'ratio9_a': 'max', 'ratio9_af': 'max',
                'ratio9_grps': 'max', 'ratio10_a': 'max', 'ratio10_af': 'max', 'ratio10_grps': 'max'}).reset_index(). \
            rename(columns={'e_reach_n': 'reach_sum', 'e_reach2_n': 'reach2_sum', 'e_reach3_n': 'reach3_sum',
                            'e_reach4_n': 'reach4_sum', 'e_reach5_n': 'reach5_sum',
                            'e_reach6_n': 'reach6_sum', 'e_reach7_n': 'reach7_sum', 'e_reach8_n': 'reach8_sum',
                            'e_reach9_n': 'reach9_sum', 'e_reach10_n': 'reach10_sum'})
        ovr = ovr.merge(max_reach, how='left')

        grouped = df.groupby(['gender', 'age_min', 'age_max'])
        trans_list = [[]]

        for i in range(ovr.shape[0]):
            key = (ovr['gender'][i], ovr['age_min'][i], ovr['age_max'][i])
            try:
                filt = grouped.get_group(key)
            except KeyError:
                trans_list[0].append(0)
                continue

            pop_mean = filt['population'].mean()
            grps = filt['eimp_a_weighted'].sum() / pop_mean
            reach = filt['reach_sum'].sum() / pop_mean
            channel = (filt['eimp_a_weighted'] > 0).sum()

            weight = self.get_weight(input_weight, grps=grps, reach=reach, channel=channel)

            reach_p = filt['e_reach_p'].values 
            trans_list[0].append(self.trans_duplicate(reach_p, weight))
            
        ovr['e_reach_p'] = trans_list[0]
        ovr['e_reach_p'] = np.where(ovr['retargeting_cnt'] == ovr['line_cnt'], ovr['retargeting'] / ovr['population'] * .9999, ovr['e_reach_p'])
        ovr['isTarget'] = np.where(ovr['target_impression'] > 0, 1, 0)
        ovr['e_reach_n'] = ovr['e_reach_p'] * ovr['population']
        ovr['e_reach_n'] = np.where(ovr['e_reach_n'] > ovr['reach_sum'], ovr['reach_sum'], ovr['e_reach_n'])
        ovr['e_reach_p'] = np.where(ovr['agrps'] > 0, ovr['e_reach_n'] / ovr['population'], 0)
        ovr['e_reach_n'] = np.where(ovr['e_reach_n'] < ovr['max_reach_n'], ovr['max_reach_n'], ovr['e_reach_n'])
        ovr['e_reach_p'] = np.where(ovr['agrps'] > 0, ovr['e_reach_n'] / ovr['population'], 0)

        ovr['e_grps'] = ovr['eimp_weighted'] / ovr['population'] * 100
        ovr['e_grps_a'] = ovr['e_imp_a'] / ovr['population'] * 100
        ovr['target_grps'] = ovr['e_grps'] * ovr['isTarget']
        ovr['target_grps_a'] = ovr['e_grps_a'] * ovr['isTarget']
        ovr['target_reach_n'] = ovr['e_reach_n'] * ovr['isTarget']
        ovr['target_reach_p'] = ovr['target_reach_n'] / ovr['population']
        
        ovr['af'] = ovr['e_imp_a'] / ovr['e_reach_n']
        ovr['af_a'] = ovr['eimp_weighted'] / ovr['e_reach_n']
        ovr['target_af'] = ovr['target_impression_weighted'] / ovr['target_reach_n']
        ovr['target_af_a'] = ovr['target_impression_a'] / ovr['target_reach_n']

        for r in range(2, 11):
            max_reach_n = 'max_reach' + str(r) + '_n'
            e_ratio = 'e_ratio' + str(r)
            e_reach_p = 'e_reach' + str(r) + '_p'
            e_reach_n = 'e_reach' + str(r) + '_n'
            reach_sum = 'reach' + str(r) + '_sum'

            target_ratio = 'target_ratio' + str(r)
            target_reach_p = 'target_reach' + str(r) + '_p'
            target_reach_n = 'target_reach' + str(r) + '_n'

            ratio_a = 'ratio' + str(r) + '_a'
            ratio_af = 'ratio' + str(r) + '_af'
            ratio_grps = 'ratio' + str(r) + '_grps'

            ###
            ovr[e_ratio] = (1 / (1 + np.exp(
                -(ovr[ratio_a] + ovr[ratio_af] * np.log(ovr['af']) + ovr[ratio_grps] * np.log(ovr['e_grps'])))))
            ovr[target_ratio] = (1 / (1 + np.exp(
                -(ovr[ratio_a] + ovr[ratio_af] * np.log(ovr['target_af']) + ovr[ratio_grps] * np.log(ovr['target_grps'])))))

            ###
            if r == 2:
                _e_reach_p = 'e_reach_p'
                _target_reach_p = 'target_reach_p'
            else:
                _e_reach_p = 'e_reach' + str(r - 1) + '_p'
                _target_reach_p = 'target_reach' + str(r - 1) + '_p'

            ovr[e_reach_p] = ovr[_e_reach_p] * ovr[e_ratio]
            ovr[e_reach_n] = ovr[e_reach_p] * ovr['population']
            ovr[e_reach_n] = np.where(ovr[e_reach_n] < ovr[max_reach_n], ovr[max_reach_n], ovr[e_reach_n])
            ovr[e_reach_p] = ovr[e_reach_n] / ovr['population']
            
            ovr[target_reach_p] = ovr[_target_reach_p] * ovr[target_ratio]
            ovr[target_reach_n] = ovr[target_reach_p] * ovr['population']
            ovr[target_reach_n] = np.where(ovr[target_reach_n] < (ovr[max_reach_n] * ovr['isTarget']), (ovr[max_reach_n] * ovr['isTarget']), ovr[target_reach_n])
            ovr[target_reach_p] = ovr[target_reach_n] / ovr['population']

        ovr = self.round_float(ovr.fillna(0.))

        return (ovr)


    def summary_total(self, input_mix, input_age, input_gender, input_weight):
        ph5 = self.phase5(input_mix, input_age, input_gender, input_weight)
        mix_cleaned = self.get_eimp(self.mix_clean(input_mix)).reset_index(drop=True).assign(total='total')
        trans_pop = pd.read_json(self.get_population(pd.read_json(self.get_gender(input_gender))['gender'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_min'][0],
                                                pd.read_json(self.trans_age(input_age))['trans_max'][0]))['trans_pop'][0]

        df = ph5.query('e_grps_a != 0').assign(total='total')
        df = df.groupby('total'). \
            agg({'e_imp': 'sum', 'eimp_weighted': 'sum', 'e_imp_a': 'sum', 'eimp_a_weighted': 'sum',
                'target_impression': 'sum', 'target_impression_weighted': 'sum', 'target_impression_a': 'sum',
                'target_impression_a_weighted': 'sum',
                'e_reach_n': 'sum', 'e_reach2_n': 'sum', 'e_reach3_n': 'sum', 'e_reach4_n': 'sum', 'e_reach5_n': 'sum',
                'e_reach6_n': 'sum', 'e_reach7_n': 'sum', 'e_reach8_n': 'sum', 'e_reach9_n': 'sum', 'e_reach10_n': 'sum',
                'target_reach_n': 'sum', 'target_reach2_n': 'sum', 'target_reach3_n': 'sum', 'target_reach4_n': 'sum',
                'target_reach5_n': 'sum',
                'target_reach6_n': 'sum', 'target_reach7_n': 'sum', 'target_reach8_n': 'sum', 'target_reach9_n': 'sum',
                'target_reach10_n': 'sum',
                'population': 'sum'}).reset_index()

        df = pd.merge(df, mix_cleaned.groupby('total'). \
                    agg({'budget': 'sum', 'date_start': 'min', 'date_end': 'max'}).reset_index(), left_index=True,
                    right_index=True)
        
        df['e_grps_a'] = df['e_imp_a'] / df['population'] * 100
        df['e_grps'] = df['eimp_weighted'] / df['population'] * 100
        df['af_a'] = df['e_imp_a'] / df['e_reach_n']
        df['af'] = df['eimp_weighted'] / df['e_reach_n']
        df['target_grps_a'] = df['target_impression_a'] / trans_pop * 100
        df['target_grps'] = df['target_impression_weighted'] / trans_pop * 100
        df['target_af_a'] = df['target_impression_a'] / df['target_reach_n']
        df['target_af'] = df['target_impression_weighted'] / df['target_reach_n']

        for r in range(1, 11):
            if r == 1:
                reach = 'reach'
            else:
                reach = 'reach' + str(r)

            e_reach_p = 'e_' + reach + '_p'
            e_reach_n = 'e_' + reach + '_n'
            target_reach_p = 'target_' + reach + '_p'
            target_reach_n = 'target_' + reach + '_n'

            df[e_reach_p] = np.where(df[e_reach_n] < 1.0, 0.0, df[e_reach_n] / df['population'])
            df[target_reach_p] = np.where(df[target_reach_n] < 1.0, 0.0, df[target_reach_n] / trans_pop)

        select_columns = ['campaign', 'line', 'platform', 'product', 'date_start', 'date_end', 'gender', 'age_min',
                        'age_max', 'budget', 'target_impression_a', 'target_impression_weighted'] + \
                        [x for x in df.columns if 'target_reach' in x] + \
                        ['target_grps_a', 'target_grps', 'target_af_a', 'target_af']

        df = df.filter(select_columns). \
            rename(columns={'target_impression_a': 'target_impression',
                            'target_grps':'target_grps_weighted', 'target_grps_a': 'target_grps',
                            'target_af':'target_af_weighted', 'target_af_a': 'target_af'}). \
            fillna(0)

        # df['period'] = [((datetime.strptime(x, '%Y-%m-%d') - datetime.strptime(y, '%Y-%m-%d')).days + 1)
        #                 for x, y in zip(df['date_end'], df['date_start'])]
        df['period'] = [self.calc_period(x, y) for x, y in zip(df['date_end'], df['date_start'])]
        df['target_af_day'] = df['target_af'] / df['period']
        df['target_af_week'] = df['target_af'] / df['period'] * 7
        df['target_af_30'] = df['target_af'] / df['period'] * 30
        df['imp_interval'] = df['period'] / df['target_af']
        
        df['target_af_day_weighted'] = df['target_af_weighted'] / df['period']
        df['target_af_week_weighted'] = df['target_af_weighted'] / df['period'] * 7
        df['target_af_30_weighted'] = df['target_af_weighted'] / df['period'] * 30
        df['imp_interval_weighted'] = df['period'] / df['target_af_weighted']
        
        df['imp_interval'] = df['imp_interval'].apply(lambda x: str(np.round(x, 2)) + '일당 1회 노출')
        df['imp_interval_weighted'] = df['imp_interval_weighted'].apply(lambda x: str(np.round(x, 2)) + '일당 1회 노출')
        df = df.drop('period', axis=1).assign(line="Total", campaign=None, platform=None, product=None, gender=None,
                                            age_min=None, age_max=None)

        df = self.round_float(df)
        
        return (ph5, df)